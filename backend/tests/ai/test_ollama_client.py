from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.core.session import store_dataset, clear_all_sessions
from app.ai.conversation import (
    create_conversation,
    append_message,
    get_history,
    clear_conversations,
    get_or_create_conversation
)
from app.ai.ollama_client import chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_all_sessions()
    clear_conversations()
    yield
    clear_all_sessions()
    clear_conversations()


# --- Conversation Store Tests ---

def test_conversation_store_persistence():
    cid = create_conversation()
    history = get_history(cid)
    assert len(history) == 0

    append_message(cid, {"role": "user", "content": "First message"})
    append_message(cid, {"role": "assistant", "content": "Second message"})

    retrieved_history = get_history(cid)
    assert len(retrieved_history) == 2
    assert retrieved_history[0]["role"] == "user"
    assert retrieved_history[0]["content"] == "First message"
    assert retrieved_history[1]["role"] == "assistant"
    assert retrieved_history[1]["content"] == "Second message"


def test_conversation_store_isolation():
    cid1, _ = get_or_create_conversation("session_1")
    cid2, _ = get_or_create_conversation("session_2")

    append_message(cid1, {"role": "user", "content": "Session 1 msg"})
    append_message(cid2, {"role": "user", "content": "Session 2 msg"})

    h1 = get_history("session_1")
    h2 = get_history("session_2")

    assert len(h1) == 1 and h1[0]["content"] == "Session 1 msg"
    assert len(h2) == 1 and h2[0]["content"] == "Session 2 msg"


# --- Ollama Client Unit Tests ---

@patch("ollama.Client")
def test_ollama_unreachable_error_handling(mock_ollama_client):
    mock_inst = MagicMock()
    mock_inst.chat.side_effect = httpx.ConnectError("Failed to connect to host")
    mock_ollama_client.return_value = mock_inst

    result = chat(messages=[{"role": "user", "content": "Test"}])

    assert isinstance(result, dict)
    assert result.get("error") == "ollama_unavailable"
    assert "Ollama connection error" in result.get("message", "")


# --- API Endpoint Tests ---

def test_chat_endpoint_missing_dataset():
    response = client.post(
        "/api/dataset/non_existent_file/chat",
        json={"message": "Summarize this dataset"}
    )
    assert response.status_code == 404


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_ollama_unreachable(mock_chat):
    df = pd.DataFrame({"a": [1, 2, 3]})
    file_id = "test_file_unreachable"
    store_dataset(file_id, df)

    mock_chat.return_value = {
        "error": "ollama_unavailable",
        "message": "AI assistant is currently unavailable. Please ensure Ollama is running locally."
    }

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Hello"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ollama_unavailable"
    assert "AI assistant is currently unavailable" in data["response_text"]


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_normal_conversation(mock_chat):
    df = pd.DataFrame({"a": [1, 2, 3]})
    file_id = "test_file_chat"
    store_dataset(file_id, df)

    mock_chat.return_value = {
        "content": "This is a dataset with 3 rows.",
        "tool_calls": []
    }

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Tell me about this dataset"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["status"] == "ok"
    assert data["response_text"] == "This is a dataset with 3 rows."
    assert data["tool_calls_made"] == []


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_tool_calling_with_route_file_id_override(mock_chat):
    """
    Test that even if the LLM passes a wrong or missing file_id in tool call arguments,
    the route's file_id from the URL path is authoritatively used.
    """
    df = pd.DataFrame({"name": ["Alice", "Bob"], "score": [90, 85]})
    real_file_id = "test_file_authoritative_123"
    store_dataset(real_file_id, df)

    # Mock Ollama: 1st call returns tool call with WRONG file_id in arguments,
    # 2nd call returns final natural language response.
    mock_chat.side_effect = [
        {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_dataset_summary",
                        "arguments": {"file_id": "WRONG_FILE_ID_FROM_LLM"}
                    }
                }
            ]
        },
        {
            "content": "The dataset has 2 rows and columns name, score with 100% health score.",
            "tool_calls": []
        }
    ]

    response = client.post(
        f"/api/dataset/{real_file_id}/chat",
        json={"message": "Summarize dataset"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["response_text"] == "The dataset has 2 rows and columns name, score with 100% health score."
    assert data["tool_calls_made"] == ["get_dataset_summary"]


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_multi_turn_history_threading(mock_chat):
    """
    Test sending two chat messages with the same conversation_id where the second message
    asks the model to recall exact wording from the first. Assert that the actual messages array
    passed to chat() on turn 2 contains both turn 1 user message and turn 1 assistant response.
    """
    df = pd.DataFrame({"x": [1, 2]})
    file_id = "test_file_history_threading"
    store_dataset(file_id, df)

    mock_chat.side_effect = [
        {"content": "I stored your initial prompt.", "tool_calls": []},
        {"content": "Your initial prompt was 'Secret prompt phrase 123'", "tool_calls": []}
    ]

    # Turn 1
    res1 = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "Secret prompt phrase 123"}
    )
    assert res1.status_code == 200
    cid = res1.json()["conversation_id"]

    # Turn 2
    res2 = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"conversation_id": cid, "message": "What was the exact wording of my first question?"}
    )
    assert res2.status_code == 200

    # Verify call_args_list for mock_chat on turn 2
    assert mock_chat.call_count == 2
    turn2_kwargs = mock_chat.call_args_list[1].kwargs
    turn2_messages = turn2_kwargs.get("messages", [])

    # Turn 2 messages should include:
    # 0: Turn 1 user message
    # 1: Turn 1 assistant message
    # 2: Turn 2 user message
    assert len(turn2_messages) == 3
    assert turn2_messages[0]["role"] == "user"
    assert turn2_messages[0]["content"] == "Secret prompt phrase 123"
    assert turn2_messages[1]["role"] == "assistant"
    assert turn2_messages[1]["content"] == "I stored your initial prompt."
    assert turn2_messages[2]["role"] == "user"
    assert turn2_messages[2]["content"] == "What was the exact wording of my first question?"


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_calculate_statistic_tool_call(mock_chat):
    """
    Test chat route when Ollama requests calculate_statistic tool call on a real column.
    Verify tool execution and tool_calls_made in final output.
    """
    df = pd.DataFrame({"salary": [50000, 60000, 70000]})
    file_id = "test_file_calc_stat_route"
    store_dataset(file_id, df)

    mock_chat.side_effect = [
        {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate_statistic",
                        "arguments": {
                            "file_id": file_id,
                            "column_name": "salary",
                            "statistic": "mean"
                        }
                    }
                }
            ]
        },
        {
            "content": "The average salary is $60,000.00.",
            "tool_calls": []
        }
    ]

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "What is the average salary?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["response_text"] == "The average salary is $60,000.00."
    assert data["tool_calls_made"] == ["calculate_statistic"]


@patch("app.api.routes.chat.chat")
def test_greeting_message_returns_no_tool_calls(mock_chat):
    """
    Test simulating a greeting message (e.g. 'hi')
    and confirming tool_calls_made is empty.
    """
    df = pd.DataFrame({"a": [1, 2]})
    file_id = "test_file_greeting"
    store_dataset(file_id, df)

    mock_chat.return_value = {
        "content": "Hello! I am InsightIQ's AI Data Analyst Assistant. How can I help you analyze your dataset today?",
        "tool_calls": []
    }

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "hi"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tool_calls_made"] == []
    assert "Hello" in data["response_text"]


@patch("app.api.routes.chat.logger")
@patch("app.api.routes.chat.chat")
def test_audit_response_claims_logs_warning_on_unverified_numbers(mock_chat, mock_logger):
    """
    Test guardrail check: given a response containing percentage claims with zero preceding tool calls,
    the system audits the response and logs a server-side warning.
    """
    df = pd.DataFrame({"weapon_used": ["Hands", "Knives"]})
    file_id = "test_file_guardrail_warning"
    store_dataset(file_id, df)

    mock_chat.return_value = {
        "content": "The top weapons by percentage are Hands 34.5% and Knives 23.2%.",
        "tool_calls": []
    }

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "list top weapons used by percentage"}
    )

    assert response.status_code == 200
    assert mock_logger.warning.called
    warning_args = str(mock_logger.warning.call_args[0][0])
    assert "GUARDRAIL WARNING" in warning_args


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_suggested_action_create_chart(mock_chat):
    """
    Test that when recommend_chart or find_top_categories tool is invoked,
    the chat route populates suggested_action with type 'create_chart' and valid payload.
    """
    df = pd.DataFrame({"weapon_used": ["Knife", "Firearm", "Knife"]})
    file_id = "test_file_suggested_action_chart"
    store_dataset(file_id, df)

    mock_chat.side_effect = [
        {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "recommend_chart",
                        "arguments": {"file_id": file_id, "columns_of_interest": ["weapon_used"]}
                    }
                }
            ]
        },
        {
            "content": "A bar chart showing weapon_used by count works best.",
            "tool_calls": []
        }
    ]

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "create a chart showing weapon_used counts"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tool_calls_made"] == ["recommend_chart"]
    assert data["suggested_action"] is not None
    assert data["suggested_action"]["type"] == "create_chart"
    assert "payload" in data["suggested_action"]
    assert data["suggested_action"]["payload"]["chart_type"] != ""


@patch("app.api.routes.chat.chat")
def test_chat_endpoint_suggested_action_create_kpi(mock_chat):
    """
    Test that when calculate_statistic tool is invoked,
    the chat route populates suggested_action with type 'create_kpi' and valid payload.
    """
    df = pd.DataFrame({"suspect_age": [25, 30, 35]})
    file_id = "test_file_suggested_action_kpi"
    store_dataset(file_id, df)

    mock_chat.side_effect = [
        {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate_statistic",
                        "arguments": {"file_id": file_id, "column_name": "suspect_age", "statistic": "mean"}
                    }
                }
            ]
        },
        {
            "content": "The average suspect_age is 30.",
            "tool_calls": []
        }
    ]

    response = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "What is the average suspect_age?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tool_calls_made"] == ["calculate_statistic"]
    assert data["suggested_action"] is not None
    assert data["suggested_action"]["type"] == "create_kpi"
    assert data["suggested_action"]["payload"]["value"] == 30.0


@patch("app.api.routes.chat.chat")
def test_suggested_action_not_carried_over_to_unrelated_next_turn(mock_chat):
    """
    Test that a suggested_action generated in Turn 1 is NOT carried over
    to an unrelated question in Turn 2. Turn 2 must return suggested_action = None.
    """
    from app.ai.conversation import get_history
    df = pd.DataFrame({"weapon_used": ["Knife", "Gun"]})
    file_id = "test_file_action_carryover"
    store_dataset(file_id, df)

    # Turn 1 mock: recommendation tool -> text response
    mock_chat.side_effect = [
        {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "recommend_chart",
                        "arguments": {"file_id": file_id, "columns_of_interest": ["weapon_used"]}
                    }
                }
            ]
        },
        {
            "content": "Here is a recommended chart for weapon_used.",
            "tool_calls": []
        },
        # Turn 2 mock: direct text response with no tool calls
        {
            "content": "I am InsightIQ AI Assistant.",
            "tool_calls": []
        }
    ]

    # Turn 1
    resp1 = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "create a chart showing weapon_used counts"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    cid = data1["conversation_id"]
    assert data1["suggested_action"] is not None
    assert data1["suggested_action"]["type"] == "create_chart"

    # Turn 2: Unrelated question
    resp2 = client.post(
        f"/api/dataset/{file_id}/chat",
        json={"message": "who made you?", "conversation_id": cid}
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["tool_calls_made"] == []
    # MUST be None on Turn 2
    assert data2["suggested_action"] is None

    # Verify long-term conversation memory contains ONLY clean text messages
    hist = get_history(cid)
    assert len(hist) == 4  # [user1, assistant1, user2, assistant2]
    roles = [m["role"] for m in hist]
    assert roles == ["user", "assistant", "user", "assistant"]
    # Ensure no raw tool call objects in long-term memory
    for m in hist:
        assert "tool_calls" not in m
        assert m["role"] != "tool"

