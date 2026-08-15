import json
import logging
import re
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.session import get_dataset
from app.core.database import get_db
from app.auth.dependencies import get_optional_user
from app.models.db_models import User, ChatConversationModel
from app.schemas.chat import ChatRequest, ChatResponse
from app.ai.conversation import (
    create_conversation,
    get_history,
    append_message,
    get_or_create_conversation
)
from app.ai.ollama_client import chat, chat_stream
from app.ai.tool_router import TOOL_REGISTRY, dispatch_tool_call
from app.api.routes.settings import get_active_provider_for_request, get_effective_groq_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dataset", tags=["chat"])

GREETING_PATTERNS = {
    "hi", "hello", "hey", "hi!", "hello!", "hey!", "hello there", "hi there",
    "good morning", "good afternoon", "good evening", "who are you", "who are you?",
    "who made you", "who made you?", "who created you", "who created you?",
    "who built you", "who built you?", "what can you do", "what can you do?"
}

PERCENTAGE_OR_NUMBER_PATTERN = re.compile(r'\b\d+(\.\d+)?%\b|\b\d{2,}\b')


def is_simple_greeting(message: str) -> bool:
    """Detect if a user prompt is a simple greeting or meta question that should not trigger tools."""
    if not message or not isinstance(message, str):
        return False
    msg_clean = message.strip().lower()
    return msg_clean in GREETING_PATTERNS


def audit_response_claims(response_text: str, tool_calls_made: List[str]):
    """
    Audit generated natural language text for numeric/percentage claims when zero tool calls were made in this turn.
    Logs a warning server-side if suspicious claims are detected without preceding tool verification.
    """
    if not tool_calls_made and response_text:
        matches = PERCENTAGE_OR_NUMBER_PATTERN.findall(response_text)
        if matches:
            logger.warning(
                f"[GUARDRAIL WARNING] AI response contains numerical/percentage claims without preceding tool call! "
                f"Response text: '{response_text}'"
            )


def build_suggested_action(tool_name: str, tool_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Construct a structured suggested_action object based on executed tool results.
    Connects AI tool execution directly to Dashboard/Analytics UI actions.
    """
    if not tool_result or "error" in tool_result:
        return None

    if tool_name == "recommend_chart":
        return {
            "type": "create_chart",
            "payload": {
                "chart_type": tool_result.get("chart_type", "bar"),
                "title": f"{tool_result.get('y_axis', '')} by {tool_result.get('x_axis', '')}".strip() or "Recommended Chart",
                "x_axis": tool_result.get("x_axis", ""),
                "y_axis": tool_result.get("y_axis", ""),
                "aggregation": tool_result.get("aggregation", "count"),
                "reason": tool_result.get("reasoning") or tool_result.get("reason", "")
            }
        }
    elif tool_name == "calculate_statistic":
        col = tool_result.get("column", "")
        stat = tool_result.get("statistic", "")
        val = tool_result.get("value")
        return {
            "type": "create_kpi",
            "payload": {
                "kpi_name": f"{stat.title()} of {col}" if stat and col else "Calculated Metric",
                "value": val,
                "definition": f"Calculated {stat} for column '{col}'",
                "required_columns": [col] if col else [],
                "calculation_logic": f"{stat.upper()}({col})",
                "reason": f"Calculated statistic for {col}",
                "dax": f"{stat.upper()}([{col}])"
            }
        }
    elif tool_name == "aggregate_data":
        g_col = tool_result.get("group_by_column", "")
        v_col = tool_result.get("value_column", "")
        agg = tool_result.get("aggregation", "sum")
        return {
            "type": "create_chart",
            "payload": {
                "chart_type": "bar",
                "title": f"{v_col} by {g_col}".strip() or "Grouped Aggregation",
                "x_axis": g_col,
                "y_axis": v_col,
                "aggregation": agg,
                "reason": f"Grouped aggregation of {v_col} by {g_col}"
            }
        }
    elif tool_name == "find_top_categories":
        col = tool_result.get("column", "")
        return {
            "type": "create_chart",
            "payload": {
                "chart_type": "bar",
                "title": f"Top Categories of {col}".strip() or "Category Distribution",
                "x_axis": col,
                "y_axis": "count",
                "aggregation": "count",
                "reason": f"Top category distribution of {col}"
            }
        }

    return None


def parse_malformed_tool_call(content: str) -> Optional[Dict[str, Any]]:
    """
    Detect if Ollama emitted a tool call inside plain response_text JSON instead of structured tool_calls.
    """
    if not content or not isinstance(content, str):
        return None
    s = content.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 2:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            s = "\n".join(lines).strip()

    if "{" in s and "}" in s:
        start = s.find("{")
        end = s.rfind("}")
        json_str = s[start:end+1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                if "name" in data or "function" in data:
                    if any(k in data for k in ["parameters", "arguments", "user_input", "message_id", "conversation_id"]):
                        return data
                    if "function" in data and isinstance(data["function"], dict):
                        return data
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return None


def sync_chat_to_db(db: Session, file_id: str, cid: str, current_user: Optional[User]):
    if not db:
        return
    history = list(get_history(cid))
    rec = db.query(ChatConversationModel).filter(ChatConversationModel.id == cid).first()
    if not rec:
        rec = ChatConversationModel(
            id=cid,
            user_id=current_user.id if current_user else None,
            dataset_id=file_id,
            messages_json=json.dumps(history)
        )
        db.add(rec)
    else:
        rec.messages_json = json.dumps(history)
        if current_user and not rec.user_id:
            rec.user_id = current_user.id
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to sync chat conversation to DB: {e}")


def format_tool_result_summary(tool_name: str, tool_result: Dict[str, Any]) -> str:
    """Format executed tool result into natural language markdown if LLM text output is empty."""
    if not tool_result or "error" in tool_result:
        return tool_result.get("message") or tool_result.get("error", "Unable to compute results for this dataset.")

    if tool_name == "find_top_categories":
        col = tool_result.get("column", "category")
        cats = tool_result.get("categories", [])
        if not cats:
            return f"No categories found for column **{col}**."
        lines = [f"Here are the top categories for **{col}**:"]
        for c in cats:
            name = c.get("category", "")
            pct = c.get("percentage")
            cnt = c.get("count")
            if pct is not None:
                lines.append(f"- **{name}**: {pct}% ({cnt} occurrences)")
            else:
                lines.append(f"- **{name}**: {cnt}")
        return "\n".join(lines)

    elif tool_name == "calculate_statistic":
        col = tool_result.get("column", "")
        stat = tool_result.get("statistic", "")
        val = tool_result.get("value")
        return f"The calculated **{stat}** for column **{col}** is **{val}**."

    elif tool_name == "get_dataset_summary":
        rows = tool_result.get("total_rows", "N/A")
        cols = tool_result.get("total_columns", "N/A")
        health = tool_result.get("health_score", "N/A")
        return f"Dataset Summary:\n- **Total Rows**: {rows}\n- **Total Columns**: {cols}\n- **Quality Health Score**: {health}%"

    elif tool_name == "aggregate_data":
        g_col = tool_result.get("group_by_column", "")
        v_col = tool_result.get("value_column", "")
        results = tool_result.get("results", [])
        lines = [f"Aggregated **{v_col}** grouped by **{g_col}**:"]
        for r in results[:10]:
            lines.append(f"- **{r.get('group')}**: {r.get('value')}")
        return "\n".join(lines)

    return "Successfully calculated dataset analytics."


def infer_and_execute_tool_fallback(file_id: str, message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Intelligently infer and execute backend analytics tool if LLM failed to emit structured tool call on turn 1.
    """
    msg_clean = message.lower().strip()
    try:
        df = get_dataset(file_id)
        cols = [str(c) for c in df.columns]

        # 1. Overview / Metadata / Health / Column list
        summary_kw = {"row", "rows", "column", "columns", "summary", "overview", "health", "clean", "quality", "null", "nulls", "missing", "duplicate", "duplicates", "record", "records"}
        if any(k in msg_clean for k in summary_kw) and not any(k in msg_clean for k in ["average", "mean", "sum", "median"]):
            res = dispatch_tool_call("get_dataset_summary", {}, file_id)
            return ("get_dataset_summary", res)

        # 2. Recommendation / Chart
        if any(k in msg_clean for k in ["chart", "plot", "visualize", "graph", "recommendation", "recommend"]):
            res = dispatch_tool_call("recommend_chart", {"columns_of_interest": cols}, file_id)
            return ("recommend_chart", res)

        # 3. Fuzzy match column name in message
        matched_col = None
        for c in cols:
            norm_c = c.replace("_", " ").lower()
            if norm_c in msg_clean or c.lower() in msg_clean:
                matched_col = c
                break

        if not matched_col:
            words = [w.strip("?,.!") for w in msg_clean.split()]
            for w in words:
                if len(w) >= 3:
                    r_col = resolve_column_name(cols, w)
                    if r_col:
                        matched_col = r_col
                        break

        if matched_col:
            top_kw = {"top", "most", "frequent", "distribution", "percentage", "proportion", "common", "category", "categories", "least", "counts", "count"}
            if any(k in msg_clean for k in top_kw):
                res = dispatch_tool_call("find_top_categories", {"column_name": matched_col}, file_id)
                return ("find_top_categories", res)

            stat_map = {
                "average": "mean", "mean": "mean", "median": "median", "sum": "sum",
                "total": "sum", "min": "min", "minimum": "min", "lowest": "min",
                "max": "max", "maximum": "max", "highest": "max", "std": "std",
                "unique": "unique_count"
            }
            for kw, st in stat_map.items():
                if kw in msg_clean:
                    res = dispatch_tool_call("calculate_statistic", {"column_name": matched_col, "statistic": st}, file_id)
                    return ("calculate_statistic", res)

            is_num = pd.api.types.is_numeric_dtype(df[matched_col]) and not pd.api.types.is_bool_dtype(df[matched_col])
            if is_num:
                res = dispatch_tool_call("calculate_statistic", {"column_name": matched_col, "statistic": "mean"}, file_id)
                return ("calculate_statistic", res)
            else:
                res = dispatch_tool_call("find_top_categories", {"column_name": matched_col}, file_id)
                return ("find_top_categories", res)

        res = dispatch_tool_call("get_dataset_summary", {}, file_id)
        return ("get_dataset_summary", res)
    except Exception as err:
        logger.warning(f"Failed to auto-infer tool call for message '{message}': {err}")
        return None


@router.post("/{file_id}/chat", response_model=None)
async def chat_with_dataset(
    file_id: str,
    payload: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """
    Data Chat endpoint allowing multi-turn conversational analysis with tool-calling capabilities.
    Supports optional streaming for real-time incremental token rendering via SSE,
    and returns a suggested_action payload ONLY when actionable tools are invoked in the current turn.
    """
    # 1. Verify dataset exists (raises 404 if missing)
    get_dataset(file_id)

    # 2. Get active provider & effective Groq key for request
    active_provider = get_active_provider_for_request(current_user=current_user, session_id=x_session_id)
    effective_groq_key = get_effective_groq_key(current_user=current_user, session_id=x_session_id)

    # 3. Get or initialize conversation session
    cid, _ = get_or_create_conversation(payload.conversation_id)

    # 4. Retrieve clean long-term conversation history (only user text & assistant text)
    history = list(get_history(cid))
    turn_messages = list(history)
    turn_messages.append({"role": "user", "content": payload.message})

    tool_calls_made: List[str] = []
    last_tool_result: Optional[Dict[str, Any]] = None
    last_tool_name: Optional[str] = None
    turn_suggested_action: Optional[Dict[str, Any]] = None
    MAX_TOOL_LOOPS = 3
    is_greeting = is_simple_greeting(payload.message)

    for loop_idx in range(MAX_TOOL_LOOPS):
        # Pass tools on turns where tool calling is allowed and message is not a simple greeting
        allow_tools = (loop_idx < MAX_TOOL_LOOPS - 1) and not is_greeting
        res = chat(
            messages=turn_messages,
            tools=TOOL_REGISTRY if allow_tools else None,
            provider=active_provider,
            groq_api_key=effective_groq_key
        )

        err_type = res.get("error")
        if err_type in ["ollama_unavailable", "groq_unavailable"]:
            return ChatResponse(
                conversation_id=cid,
                response_text=res.get("message", f"AI assistant ({active_provider}) is currently unavailable."),
                tool_calls_made=tool_calls_made,
                suggested_action=None,
                status=err_type
            )

        tool_calls = res.get("tool_calls", [])

        # Auto-infer tool call on loop 0 if LLM returned zero tool calls for analytical message
        if not tool_calls and loop_idx == 0 and not is_greeting:
            inferred = infer_and_execute_tool_fallback(file_id, payload.message)
            if inferred:
                inf_name, inf_res = inferred
                tool_calls_made.append(inf_name)
                last_tool_name = inf_name
                last_tool_result = inf_res
                act = build_suggested_action(inf_name, inf_res)
                if act:
                    turn_suggested_action = act
                turn_messages.append({
                    "role": "tool",
                    "tool_call_id": "call_inferred_1",
                    "content": json.dumps(inf_res),
                    "name": inf_name
                })
                # Re-query model with inferred tool result
                continue

        if tool_calls and allow_tools:
            # Format tool_calls with valid IDs and JSON argument strings for OpenAI/Groq compatibility
            formatted_tc_openai = []
            for idx, tc in enumerate(tool_calls):
                call_id = tc.get("id") or f"call_{idx+1}"
                fn = tc.get("function", {})
                fn_name = fn.get("name", "")
                fn_args = fn.get("arguments", {})
                args_str = json.dumps(fn_args) if isinstance(fn_args, dict) else str(fn_args)
                formatted_tc_openai.append({
                    "id": call_id,
                    "type": tc.get("type", "function"),
                    "function": {
                        "name": fn_name,
                        "arguments": args_str
                    }
                })

            turn_messages.append({
                "role": "assistant",
                "content": res.get("content") or None,
                "tool_calls": formatted_tc_openai
            })

            for idx, tc in enumerate(tool_calls):
                call_id = tc.get("id") or f"call_{idx+1}"
                fn = tc.get("function", {})
                t_name = fn.get("name", "")
                t_args = fn.get("arguments", {}) or {}

                if t_name:
                    tool_calls_made.append(t_name)
                    last_tool_name = t_name
                    try:
                        tool_result = dispatch_tool_call(tool_name=t_name, arguments=t_args, file_id=file_id)
                        last_tool_result = tool_result
                        act = build_suggested_action(t_name, tool_result)
                        if act:
                            turn_suggested_action = act
                    except Exception as err:
                        tool_result = {"error": f"Failed to execute tool {t_name}: {str(err)}"}
                        last_tool_result = tool_result

                    turn_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(tool_result),
                        "name": t_name
                    })
            # Continue loop to allow model to consume tool result
            continue

        # No tool calls requested (or tool loop finished) -> process final natural language response
        final_text = (res.get("content") or "").strip()

        # Fallback if assistant text is empty but tool was executed
        if not final_text and last_tool_name and last_tool_result:
            final_text = format_tool_result_summary(last_tool_name, last_tool_result)

        if not final_text:
            if tool_calls_made:
                final_text = f"Executed analytics ({', '.join(tool_calls_made)}) on your dataset."
            else:
                final_text = "Hello! I am your InsightIQ Data Chat Assistant. How can I help you analyze your dataset today?"

        if payload.stream:
            async def sse_generator():
                full_text_list = [final_text] if final_text else []
                if not final_text:
                    for chunk_text in chat_stream(messages=turn_messages, provider=active_provider, groq_api_key=effective_groq_key):
                        full_text_list.append(chunk_text)
                        event_data = {
                            "conversation_id": cid,
                            "chunk": chunk_text,
                            "tool_calls_made": tool_calls_made,
                            "suggested_action": turn_suggested_action,
                            "status": "ok",
                            "done": False
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                else:
                    event_data = {
                        "conversation_id": cid,
                        "chunk": final_text,
                        "tool_calls_made": tool_calls_made,
                        "suggested_action": turn_suggested_action,
                        "status": "ok",
                        "done": False
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

                result_text = "".join(full_text_list) or (format_tool_result_summary(last_tool_name, last_tool_result) if last_tool_name else "Analytics executed.")
                audit_response_claims(result_text, tool_calls_made)

                # Persist ONLY clean user message and final assistant response to long-term history
                append_message(cid, {"role": "user", "content": payload.message})
                append_message(cid, {"role": "assistant", "content": result_text})

                end_event = {
                    "conversation_id": cid,
                    "chunk": "",
                    "tool_calls_made": tool_calls_made,
                    "suggested_action": turn_suggested_action,
                    "status": "ok",
                    "done": True
                }
                yield f"data: {json.dumps(end_event)}\n\n"

            return StreamingResponse(sse_generator(), media_type="text/event-stream")

        # Non-streaming response branch
        malformed = parse_malformed_tool_call(final_text)

        if malformed:
            t_name = malformed.get("name") or malformed.get("function", {}).get("name", "unknown_tool")
            logger.warning(f"Detected malformed tool call JSON in response_text for tool '{t_name}': {final_text}")

            turn_messages.append({
                "role": "user",
                "content": f"System Note: The tool '{t_name}' does not exist. Please answer the question directly from conversation history in plain natural language text without calling any tools."
            })
            retry_res = chat(messages=turn_messages, provider=active_provider, groq_api_key=effective_groq_key)
            if retry_res.get("error") not in ["ollama_unavailable", "groq_unavailable"]:
                final_text = (retry_res.get("content") or "").strip()
                if parse_malformed_tool_call(final_text) or not final_text:
                    if last_tool_name and last_tool_result:
                        final_text = format_tool_result_summary(last_tool_name, last_tool_result)
                    else:
                        final_text = "The assistant produced an unexpected response. Please try rephrasing your question."
            else:
                if last_tool_name and last_tool_result:
                    final_text = format_tool_result_summary(last_tool_name, last_tool_result)
                else:
                    final_text = "The assistant produced an unexpected response. Please try rephrasing your question."

        audit_response_claims(final_text, tool_calls_made)

        # Persist ONLY clean user message and final assistant response to long-term history
        append_message(cid, {"role": "user", "content": payload.message})
        append_message(cid, {"role": "assistant", "content": final_text})
        sync_chat_to_db(db, file_id, cid, current_user)

        return ChatResponse(
            conversation_id=cid,
            response_text=final_text,
            tool_calls_made=tool_calls_made,
            suggested_action=turn_suggested_action,
            status="ok"
        )

    # Fallback if loop finishes unexpectedly
    append_message(cid, {"role": "user", "content": payload.message})
    append_message(cid, {"role": "assistant", "content": "The assistant completed tool processing."})
    sync_chat_to_db(db, file_id, cid, current_user)
    return ChatResponse(
        conversation_id=cid,
        response_text="The assistant completed tool processing.",
        tool_calls_made=tool_calls_made,
        suggested_action=turn_suggested_action,
        status="ok"
    )
