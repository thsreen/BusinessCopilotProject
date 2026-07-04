"""
Agent state schema for the LangGraph execution pipeline.

This module defines the central `AgentState` TypedDict that flows through
every node in the agent graph. Each field represents a piece of context
that one or more graph nodes produce or consume. The state acts as the
single source of truth across all stages — input processing, guardrails,
routing, retrieval, tool execution, LLM synthesis, uncertainty evaluation,
feedback, and response formatting.

Architecture notes:
  - All graph nodes receive and return AgentState; no node accesses shared
    mutable state apart from the global MemoryManager and ResponseCache.
  - Fields prefixed with `escalation_*` form a sub-protocol for deferring
    to human operators when the agent cannot safely proceed.
  - The `adaptation_*` fields support the auto-tuning loop: after feedback
    is received, the graph records what adaptation was applied so the CLI
    and API can surface that information.
"""
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """State passed through the LangGraph nodes.

    Every key in this TypedDict is expected to be present at all times;
    nodes initialise missing fields to safe defaults at the start of each
    invocation (see `input_node` in `graph.py`).

    Attributes:
        messages: Full conversation history as a list of {"role": ..., "content": ...} dicts.
        user_input: The raw, trimmed input from the current turn.
        response: The final textual response produced by the LLM synthesis.
        confidence: A float in [0.0, 1.0] representing the LLM's self-assessed certainty.
        requires_escalation: Flag set by guardrails or uncertainty node when human
            intervention is needed (e.g. write intent detected).
        escalation_reason: Human-readable explanation of why escalation was triggered.
        escalation_handled: Flag indicating that the escalation sub-flow completed
            (e.g. the tools node ran an `escalate` tool).
        retrieved_docs: Documents returned by the retrieval (RAG) step, each as a
            dict with keys like "content", "source", "relevance_score".
        tool_calls: List of tool invocations emitted by the LLM or router, each
            containing at least a "tool" key.
        tool_results: Results returned from executing the tools in `tool_calls`,
            stored in the same order.
        next_step: String routing hint consumed by the `should_route` conditional
            edge (values: "guardrails", "router", "retrieval", "tools", "llm",
            "uncertainty", "feedback", "end").
        plan: Ordered list of high-level steps the LLM generated, used for
            structured multi-step reasoning.
        feedback: Optional user feedback string ("positive" or "negative") that
            is injected on re-runs to trigger adaptation.
        session_id: Unique identifier for the conversation session, used to
            correlate messages in the memory store.
        adaptation_data: Bag of key/value pairs collected during execution that
            the auto-tuning logic uses to adjust prompts on subsequent turns.
        adaptation_applied: Short string describing which adaptation (if any)
            was triggered (e.g. "prompt_tuned_verbosity", "style_adjusted").
        cached: Boolean flag set by the cache layer; when True the response was
            served from the in-memory LRU cache rather than re-generated.
        error: Error message string if any node raised an exception during this
            invocation; None otherwise.
        latency_ms: Wall-clock time in milliseconds consumed by the full graph
            execution (measured externally in `run_agent`).
    """
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
