import uuid
from typing import Dict, List, Any, Optional, Tuple

_conversations: Dict[str, List[Dict[str, Any]]] = {}


def create_conversation() -> str:
    """Initialize a new conversation session and return its conversation_id."""
    cid = str(uuid.uuid4())
    _conversations[cid] = []
    return cid


def get_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Get message history for a conversation_id, returning empty list if not found."""
    return _conversations.get(conversation_id, [])


def append_message(conversation_id: str, message: Dict[str, Any]) -> None:
    """Append a message dict to conversation history."""
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    _conversations[conversation_id].append(message)


# Aliases for compatibility
add_message = append_message
get_conversation_history = get_history


def get_or_create_conversation(conversation_id: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Retrieve existing conversation history or initialize a new conversation session.
    Returns (conversation_id, message_list).
    """
    if not conversation_id or conversation_id not in _conversations:
        cid = conversation_id if (conversation_id and conversation_id.strip()) else create_conversation()
        if cid not in _conversations:
            _conversations[cid] = []
        return cid, _conversations[cid]

    return conversation_id, _conversations[conversation_id]


def clear_conversations() -> None:
    """Clear all stored conversation sessions (primarily for test cleanup)."""
    _conversations.clear()
