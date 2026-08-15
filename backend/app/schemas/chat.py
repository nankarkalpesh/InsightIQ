from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SuggestedAction(BaseModel):
    type: str = Field(..., description="Action type: 'create_chart' or 'create_kpi'")
    payload: Dict[str, Any] = Field(..., description="Action payload (chart or KPI config)")


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Optional existing conversation session ID")
    message: str = Field(..., description="User chat message prompt", min_length=1)
    stream: Optional[bool] = Field(False, description="Whether to stream the final natural language response as Server-Sent Events (SSE)")


class ChatResponse(BaseModel):
    conversation_id: str = Field(..., description="Conversation session ID")
    response_text: str = Field(..., description="Assistant response text")
    tool_calls_made: List[str] = Field(default_factory=list, description="List of tool names invoked during response generation")
    suggested_action: Optional[Dict[str, Any]] = Field(None, description="Optional suggested action payload for UI integration")
    status: str = Field("ok", description="Response status: 'ok' or 'ollama_unavailable'")
