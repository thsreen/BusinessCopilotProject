"""Typed state schema for the LangGraph agent."""
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """State passed through the LangGraph nodes."""
    messages: List[Dict[str, str]]
    user_input: str
    response: str
    confidence: float
    requires_escalation: bool
    escalation_reason: str
    escalation_handled: bool
    retrieved_docs: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    next_step: str
    plan: List[str]
    feedback: Optional[str]
    session_id: str
    adaptation_data: Dict[str, Any]
    adaptation_applied: Optional[str]
    cached: bool
    error: Optional[str]
    latency_ms: float
