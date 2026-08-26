import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.session import clear_all_sessions

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_get_llm_provider_default(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    response = client.get("/api/settings/llm-provider")
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "ollama"

    providers = {p["id"]: p for p in data["providers"]}
    assert "ollama" in providers
    assert providers["ollama"]["configured"] is True
    assert "groq" in providers
    assert providers["groq"]["configured"] is False


def test_post_llm_provider_unconfigured(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.post("/api/settings/llm-provider", json={"provider": "groq"})
    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


def test_post_llm_provider_configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy_test_key_12345")

    # Get settings with Groq configured
    get_res = client.get("/api/settings/llm-provider")
    assert get_res.status_code == 200
    providers = {p["id"]: p for p in get_res.json()["providers"]}
    assert providers["groq"]["configured"] is True

    # Update provider to groq
    post_res = client.post("/api/settings/llm-provider", json={"provider": "groq"})
    assert post_res.status_code == 200
    assert post_res.json()["active_provider"] == "groq"

    # Verify active provider is now groq
    get_after = client.get("/api/settings/llm-provider")
    assert get_after.json()["active_provider"] == "groq"


def test_post_invalid_provider():
    response = client.post("/api/settings/llm-provider", json={"provider": "invalid_backend"})
    assert response.status_code == 400
    assert "Invalid provider" in response.json()["detail"]


def test_groq_key_priority_and_secrecy(monkeypatch):
    """
    Test key resolution order (User Key > Default Env Key) and ensure secret key strings are NEVER returned.
    """
    env_secret = "gsk_env_secret_key_99999"
    user_secret = "gsk_user_custom_key_11111"

    monkeypatch.setenv("GROQ_API_KEY", env_secret)

    # 1. Without user key -> uses default env key
    get_res1 = client.get("/api/settings/llm-provider")
    assert get_res1.status_code == 200
    data1 = get_res1.json()
    assert data1["has_custom_groq_key"] is False
    assert data1["groq_key_source"] == "default"
    # Ensure secret env key string is nowhere in the API response JSON string
    assert env_secret not in str(data1)

    # 2. Save user custom key -> user key takes priority over default env key
    post_res = client.post(
        "/api/settings/llm-provider",
        json={"provider": "groq", "groq_api_key": user_secret},
        headers={"X-Session-ID": "test_session_secrecy_1"}
    )
    assert post_res.status_code == 200
    # Ensure secret user key string is not returned in post response
    assert user_secret not in str(post_res.json())

    # 3. GET settings with user key configured
    get_res2 = client.get(
        "/api/settings/llm-provider",
        headers={"X-Session-ID": "test_session_secrecy_1"}
    )
    assert get_res2.status_code == 200
    data2 = get_res2.json()
    assert data2["has_custom_groq_key"] is True
    assert data2["groq_key_source"] == "user"
    # Absolute security check: secrets must NEVER be present in client responses
    assert user_secret not in str(data2)
    assert env_secret not in str(data2)


def test_groq_quota_error_differentiation(monkeypatch):
    """
    Test that chat_groq distinguishes between default key quota limit vs user key quota limit.
    """
    from app.ai.ollama_client import chat_groq
    from unittest.mock import patch, MagicMock

    monkeypatch.setenv("GROQ_API_KEY", "gsk_default_quota_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit reached: quota_exceeded for candidate model"

    with patch("httpx.Client.post", return_value=mock_resp):
        # Case A: Default key quota limit
        res_default = chat_groq(messages=[{"role": "user", "content": "hello"}], groq_api_key=None)
        assert res_default["error"] == "groq_default_limit_reached"
        assert "InsightIQ's default Groq API access is currently unavailable" in res_default["message"]

        # Case B: User key quota limit
        res_user = chat_groq(
            messages=[{"role": "user", "content": "hello"}],
            groq_api_key="gsk_user_personal_key",
            is_user_key=True
        )
        assert res_user["error"] == "groq_user_key_limit_reached"
        assert "Your personal Groq API key has reached its usage limit" in res_user["message"]


def test_ollama_model_missing_prevents_activation():
    """
    Test that when Ollama is reachable but required model is missing, provider choice cannot be activated.
    """
    from unittest.mock import patch

    with patch("app.ai.ollama_client.check_ollama_status") as mock_status:
        mock_status.return_value = {
            "reachable": True,
            "model_available": False,
            "status": "model_missing",
            "model": "llama3.2:3b",
            "details": "Ollama is running, but required model 'llama3.2:3b' is not installed locally"
        }

        # GET should show configured: False and status: model_missing
        get_res = client.get("/api/settings/llm-provider")
        assert get_res.status_code == 200
        providers = {p["id"]: p for p in get_res.json()["providers"]}
        assert providers["ollama"]["configured"] is False
        assert providers["ollama"]["status"] == "model_missing"

        # POST should fail with 400
        post_res = client.post("/api/settings/llm-provider", json={"provider": "ollama"})
        assert post_res.status_code == 400
        assert "unavailable" in post_res.json()["detail"].lower() or "not configured" in post_res.json()["detail"].lower()


def test_guest_session_user_key_isolation():
    """
    Test that custom Groq key saved by Session A is not visible or accessible to Session B.
    """
    session_a = "session_user_alpha"
    session_b = "session_user_beta"

    # Session A saves a key
    res_a = client.post(
        "/api/settings/llm-provider",
        json={"provider": "groq", "groq_api_key": "gsk_session_a_secret_key"},
        headers={"X-Session-ID": session_a}
    )
    assert res_a.status_code == 200

    # Session A should show custom key
    get_a = client.get("/api/settings/llm-provider", headers={"X-Session-ID": session_a})
    assert get_a.json()["has_custom_groq_key"] is True

    # Session B should NOT have Session A's key
    get_b = client.get("/api/settings/llm-provider", headers={"X-Session-ID": session_b})
    assert get_b.json()["has_custom_groq_key"] is False
