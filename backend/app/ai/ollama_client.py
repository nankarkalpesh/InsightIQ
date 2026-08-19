import os
import json
import logging
from typing import Dict, List, Any, Optional, Generator
import httpx

logger = logging.getLogger(__name__)

try:
    import ollama
    OllamaResponseError = getattr(ollama, "ResponseError", Exception)
    OllamaRequestError = getattr(ollama, "RequestError", Exception)
except ImportError:
    ollama = None
    OllamaResponseError = Exception
    OllamaRequestError = Exception

DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "IDENTITY & TONE:\n"
    "You are InsightIQ's Senior Data Chat Assistant, an AI data expert like ChatGPT or Claude. "
    "Your goal is to provide clear, simple, human-friendly explanations with 100% mathematical and factual accuracy.\n\n"
    "CRITICAL RULES — ZERO HALLUCINATION & PROPER DATA ACCURACY:\n"
    "1. Never state specific numbers, percentages, or statistics unless they come directly from a tool result in this conversation.\n"
    "2. Always translate raw data into simple, easy-to-understand terms. Use clean bullet points, bold key metrics, and explain what the numbers mean in plain language.\n"
    "3. Whenever asked ANY analytical question about the dataset, you MUST call one of these tools first:\n"
    "   - get_dataset_summary: for dataset overview, row/column counts, column names, missing/null values, duplicate rows, or health score.\n"
    "   - find_top_categories: for most common values, top categories, distributions, value frequencies, or percentages.\n"
    "   - calculate_statistic: for single column statistics (mean, median, sum, min, max, std, total count, unique values).\n"
    "   - aggregate_data: for grouping data by categories and computing totals/averages (e.g., loss by city, victim age by crime type).\n"
    "   - recommend_chart: for recommending visualizations or charts.\n"
    "4. Do NOT call tools for simple greetings (e.g. 'hi', 'hello', 'hey') or identity questions ('who are you?'). Respond directly with a warm, friendly text message.\n"
    "5. Keep responses concise, clear, visually well-structured, and easy to read (2-4 sentences max plus bullet points)."
)


class OllamaUnavailableError(Exception):
    """Raised when Ollama server is unreachable or fails to respond."""
    pass


def get_available_providers(groq_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return list of LLM providers and their server-side/user configuration status.
    """
    effective_groq_key = (groq_api_key or os.getenv("GROQ_API_KEY", "")).strip()
    groq_configured = bool(effective_groq_key)

    active_groq_name = _cached_working_groq_model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    return [
        {
            "id": "ollama",
            "name": "Local Ollama",
            "configured": True,
            "status": "ready",
            "details": f"Local Ollama LLM ({DEFAULT_OLLAMA_MODEL} @ {DEFAULT_OLLAMA_HOST})"
        },
        {
            "id": "groq",
            "name": "Groq (Cloud)",
            "configured": groq_configured,
            "status": "ready" if groq_configured else "not_configured",
            "details": f"Groq Cloud API ({active_groq_name})" if groq_configured else "GROQ_API_KEY environment variable is not set on the server"
        }
    ]


def get_ollama_client(host: Optional[str] = None) -> Any:
    """Get Ollama client instance pointing to specified or default host."""
    if ollama is None:
        raise OllamaUnavailableError("Ollama library is not installed.")
    target_host = host or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    return ollama.Client(host=target_host)


def _ensure_system_prompt(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure system prompt is present at the beginning of the messages list."""
    if not messages:
        return [{"role": "system", "content": SYSTEM_PROMPT}]
    if messages[0].get("role") != "system":
        return [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    return messages


def _prepare_messages_for_groq(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format messages for OpenAI/Groq REST API specification (tool call arguments as string)."""
    base = _ensure_system_prompt(messages)
    out = []
    for m in base:
        item = dict(m)
        if "tool_calls" in item and item["tool_calls"]:
            tcs = []
            for tc in item["tool_calls"]:
                tc_item = dict(tc)
                fn = dict(tc_item.get("function", {}))
                args = fn.get("arguments", {})
                if isinstance(args, dict):
                    args = json.dumps(args)
                fn["arguments"] = args
                tc_item["function"] = fn
                tcs.append(tc_item)
            item["tool_calls"] = tcs
        out.append(item)
    return out


def _prepare_messages_for_ollama(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format messages for Ollama Python SDK specification (tool call arguments as dict)."""
    base = _ensure_system_prompt(messages)
    out = []
    for m in base:
        item = dict(m)
        if "tool_calls" in item and item["tool_calls"]:
            tcs = []
            for tc in item["tool_calls"]:
                tc_item = dict(tc)
                fn = dict(tc_item.get("function", {}))
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                fn["arguments"] = args
                tc_item["function"] = fn
                tcs.append(tc_item)
            item["tool_calls"] = tcs
        out.append(item)
    return out


GROQ_MODEL_FALLBACKS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]

_cached_working_groq_model: Optional[str] = None


def get_groq_model_candidates(model_arg: Optional[str] = None) -> List[str]:
    """Get list of Groq models to attempt in order of preference."""
    env_default = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
    candidates = []
    if model_arg and model_arg.strip():
        candidates.append(model_arg.strip())
    if env_default and env_default not in candidates:
        candidates.append(env_default)
    if _cached_working_groq_model and _cached_working_groq_model not in candidates:
        candidates.append(_cached_working_groq_model)
    for m in GROQ_MODEL_FALLBACKS:
        if m and m not in candidates:
            candidates.append(m)
    return candidates


def chat_groq(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    groq_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """Execute chat request against Groq Cloud API with automatic model fallback."""
    global _cached_working_groq_model
    groq_key = (groq_api_key or os.getenv("GROQ_API_KEY", "")).strip()
    if not groq_key:
        return {
            "error": "groq_unavailable",
            "message": "GROQ_API_KEY environment variable or user API key is not set."
        }

    prepared_messages = _prepare_messages_for_groq(messages)
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    candidates = get_groq_model_candidates(model)
    last_error_msg = "Unknown error"

    for candidate_model in candidates:
        payload: Dict[str, Any] = {
            "model": candidate_model,
            "messages": prepared_messages,
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code != 200:
                    resp_lower = resp.text.lower()
                    last_error_msg = f"Groq API returned HTTP {resp.status_code}: {resp.text}"

                    # HTTP 401 Invalid API key -> Immediate auth error, DO NOT fallback across models
                    if resp.status_code == 401 or "invalid_api_key" in resp_lower or "invalid api key" in resp_lower:
                        return {
                            "error": "groq_unavailable",
                            "message": "Invalid Groq API key provided. Please verify your GROQ_API_KEY environment variable."
                        }

                    # Model-specific errors (HTTP 400 decommissioned, 404 not found, 429 rate limit) -> fallback to next candidate
                    if (
                        resp.status_code in (400, 404, 429) or
                        "model_not_found" in resp_lower or
                        "does not exist" in resp_lower or
                        "decommissioned" in resp_lower
                    ):
                        logger.warning(f"[GROQ FALLBACK] Model '{candidate_model}' returned {resp.status_code}. Trying fallback model...")
                        continue

                    return {
                        "error": "groq_unavailable",
                        "message": last_error_msg
                    }

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return {
                        "error": "groq_unavailable",
                        "message": "Groq returned empty response choices."
                    }

                _cached_working_groq_model = candidate_model
                choice_msg = choices[0].get("message", {})
                raw_tool_calls = choice_msg.get("tool_calls", [])
                parsed_tool_calls = []

                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        parsed_tool_calls.append({
                            "id": tc.get("id") or f"call_{len(parsed_tool_calls)+1}",
                            "type": tc.get("type", "function"),
                            "function": {
                                "name": fn.get("name"),
                                "arguments": args
                            }
                        })

                return {
                    "content": choice_msg.get("content") or "",
                    "tool_calls": parsed_tool_calls,
                    "raw_response": data,
                    "active_model": candidate_model
                }

        except Exception as err:
            last_error_msg = f"Groq connection error: {str(err)}"
            logger.warning(f"[GROQ FALLBACK] Error connecting with model '{candidate_model}': {err}")

    return {
        "error": "groq_unavailable",
        "message": last_error_msg
    }


def chat_stream_groq(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    groq_api_key: Optional[str] = None
) -> Generator[str, None, None]:
    """Execute streaming chat request against Groq Cloud API with automatic model fallback."""
    global _cached_working_groq_model
    groq_key = (groq_api_key or os.getenv("GROQ_API_KEY", "")).strip()
    if not groq_key:
        yield " [Error streaming from Groq: GROQ_API_KEY is not configured]"
        return

    prepared_messages = _prepare_messages_for_groq(messages)
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    candidates = get_groq_model_candidates(model)
    stream_started = False

    for candidate_model in candidates:
        payload: Dict[str, Any] = {
            "model": candidate_model,
            "messages": prepared_messages,
            "stream": True
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        resp_lower = response.text.lower() if hasattr(response, "text") and response.text else ""
                        if response.status_code == 401 or "invalid_api_key" in resp_lower:
                            yield " [Error streaming from Groq: Invalid API key provided. Please verify your GROQ_API_KEY environment variable]"
                            return
                        if (
                            response.status_code in (400, 404, 429) or
                            "model_not_found" in resp_lower or
                            "does not exist" in resp_lower or
                            "decommissioned" in resp_lower
                        ):
                            logger.warning(f"[GROQ STREAM FALLBACK] Model '{candidate_model}' returned {response.status_code}. Trying fallback model...")
                            continue
                        yield f" [Error streaming from Groq: HTTP {response.status_code}]"
                        return

                    _cached_working_groq_model = candidate_model
                    stream_started = True
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data_str)
                                content = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                continue
                    if stream_started:
                        return
        except Exception as err:
            logger.warning(f"[GROQ STREAM FALLBACK] Error with model '{candidate_model}': {err}")

    yield " [Error streaming from Groq: All configured model fallbacks failed]"


def chat_ollama(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    host: Optional[str] = None
) -> Dict[str, Any]:
    """Execute chat request against local Ollama with maximum speed & accuracy optimizations."""
    target_model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    prepared_messages = _prepare_messages_for_ollama(messages)
    client = get_ollama_client(host=host)

    # Speed & accuracy optimization options
    options: Dict[str, Any] = {
        "temperature": 0.0,    # Deterministic, faster sampling, higher tool precision
        "num_predict": 384,    # Limits token generation length for fast response
        "top_k": 20,           # Compact sampling pool
        "top_p": 0.8,          # Nucleus sampling bound
    }
    cpu_cores = os.cpu_count()
    if cpu_cores:
        options["num_thread"] = min(cpu_cores, 8)

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": prepared_messages,
        "keep_alive": "30m",   # Keep model loaded in memory to eliminate cold-start latency
        "options": options
    }
    if tools:
        kwargs["tools"] = tools

    try:
        response = client.chat(**kwargs)
        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls", [])

        parsed_tool_calls = []
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function", {})
                parsed_tool_calls.append({
                    "id": tc.get("id") or f"call_{len(parsed_tool_calls)+1}",
                    "type": tc.get("type", "function"),
                    "function": {
                        "name": fn.get("name"),
                        "arguments": fn.get("arguments", {})
                    }
                })

        return {
            "content": msg.get("content", ""),
            "tool_calls": parsed_tool_calls,
            "raw_response": response
        }

    except (OllamaResponseError, OllamaRequestError, httpx.HTTPError, ConnectionError, Exception) as err:
        return {
            "error": "ollama_unavailable",
            "message": f"Ollama connection error: {str(err)}"
        }


def chat_stream_ollama(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    host: Optional[str] = None
) -> Generator[str, None, None]:
    """Execute streaming chat request against Ollama with maximum speed & accuracy optimizations."""
    target_model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    prepared_messages = _prepare_messages_for_ollama(messages)
    client = get_ollama_client(host=host)

    options: Dict[str, Any] = {
        "temperature": 0.0,
        "num_predict": 384,
        "top_k": 20,
        "top_p": 0.8,
    }
    cpu_cores = os.cpu_count()
    if cpu_cores:
        options["num_thread"] = min(cpu_cores, 8)

    try:
        stream = client.chat(
            model=target_model,
            messages=prepared_messages,
            keep_alive="30m",
            options=options,
            stream=True
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
    except Exception as err:
        yield f" [Error streaming from Ollama: {str(err)}]"


def chat(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    host: Optional[str] = None,
    provider: Optional[str] = None,
    groq_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute chat request using specified or active provider ('ollama' or 'groq').
    """
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower().strip()
    logger.info(f"[LLM ROUTER] Dispatching chat request using provider: '{selected_provider}'")

    if selected_provider == "groq":
        return chat_groq(messages=messages, model=model, tools=tools, groq_api_key=groq_api_key)
    else:
        return chat_ollama(messages=messages, model=model, tools=tools, host=host)


def chat_stream(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    host: Optional[str] = None,
    provider: Optional[str] = None,
    groq_api_key: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Execute streaming chat request using specified or active provider ('ollama' or 'groq').
    """
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower().strip()
    logger.info(f"[LLM ROUTER] Dispatching chat_stream request using provider: '{selected_provider}'")

    if selected_provider == "groq":
        yield from chat_stream_groq(messages=messages, model=model, groq_api_key=groq_api_key)
    else:
        yield from chat_stream_ollama(messages=messages, model=model, host=host)
