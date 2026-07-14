"""
Main LangGraph StateGraph definition for the AI Operations Copilot.

This module wires together the 9 graph nodes into a directed cyclic graph
managed by LangGraph. The execution flow is:

  input -> guardrails -> router -> {retrieval, tools, llm} -> llm ->
  uncertainty -> feedback -> response -> END

Two conditional routing functions (`should_route`, `after_retrieval`) decide
which branch to follow based on the `next_step` field in AgentState and on
document-availability / query-keyword heuristics respectively.

The public entry point `run_agent()` builds the graph once (lazy singleton),
invokes it synchronously, and returns the final AgentState as a plain dict.

Global singletons:
  - _memory (MemoryManager): long-term and short-term conversation storage.
  - _compiled_graph (CompiledStateGraph): cached after the first build.
"""
import os
import time
import json
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from agent.state import AgentState
from agent.nodes.guardrails import guardrails_node
from agent.nodes.router import router_node
from agent.nodes.retrieval import retrieval_node
from agent.nodes.tools_node import tools_node
from agent.nodes.llm import llm_node
from agent.nodes.uncertainty import uncertainty_node
from agent.nodes.feedback import feedback_node
from agent.memory.manager import MemoryManager
from agent.cache import get_cache
from agent.logging.logger import get_logger

logger = get_logger("graph")

# Global memory manager
_memory = MemoryManager()
_compiled_graph = None


def input_node(state: AgentState) -> AgentState:
    """Process and validate incoming user input, initialise/reset state fields.

    This node runs first on every invocation. It:
      1. Extracts `user_input` from the state or the last message.
      2. Resets all volatile fields to safe defaults so that no stale data
         from a previous turn leaks through.
      3. Clears the response cache when the user provides feedback (forcing
         a fresh generation so the feedback is taken into account).
      4. Creates a new session via `MemoryManager.create_session()` if one
         does not already exist.
      5. Persists the user message into the memory store.

    Args:
        state: The incoming AgentState; may be partially populated from a
            previous turn (e.g. session_id, feedback).

    Returns:
        The mutated AgentState with fresh defaults and the user message
        appended to memory.
    """
    user_input = state.get("user_input", "")
    if not user_input and state.get("messages"):
        user_input = state["messages"][-1].get("content", "")

    state["user_input"] = user_input
    state["response"] = ""
    state["confidence"] = 0.0
    state["requires_escalation"] = False
    state["escalation_reason"] = ""
    state["escalation_handled"] = False
    state["retrieved_docs"] = []
    state["tool_calls"] = []
    state["tool_results"] = []
    state["next_step"] = "guardrails"
    state["error"] = None
    state["latency_ms"] = 0.0
    state["adaptation_applied"] = None
    state["cached"] = False
    state["classification"] = None

    # Invalidate cache if feedback is provided (force fresh response)
    feedback = state.get("feedback")
    if feedback:
        get_cache().clear()

    # Create session if not exists
    if not state.get("session_id"):
        state["session_id"] = _memory.create_session()

    # Add to memory
    if user_input:
        _memory.add_message(state["session_id"], "user", user_input)

    return state


def response_node(state: AgentState) -> AgentState:
    """Format the final response and persist it to memory.

    This node runs just before the END node. It:
      1. Attaches long-term memory context to the state (if available and
         not already present).
      2. Appends a low-confidence disclaimer when confidence < 0.4.
      3. Logs the assistant response into the memory store.

    Args:
        state: The incoming AgentState containing the LLM response and
            confidence score.

    Returns:
        The mutated AgentState, ready for END.
    """
    response = state.get("response", "")

    # Add memory context hint if available
    long_term = _memory.get_long_term_context(state.get("session_id", ""))
    if long_term and "long_term" not in state:
        state["long_term_context"] = long_term

    # Add confidence indicator
    confidence = state.get("confidence", 0.0)
    if confidence < 0.4 and response:
        state["response"] = response + (
            "\n\n*I have low confidence in this response. Please verify with a human analyst.*"
        )

    # Log to memory
    if response:
        _memory.add_message(state["session_id"], "assistant", response)

    return state


def should_route(state: AgentState) -> Literal["retrieval", "tools", "llm", "uncertainty", "end"]:
    """Route after guardrails.

    Reads the `next_step` field and maps it to the next graph node.
    This is the primary routing function used by both the "guardrails"
    and "router" conditional edges.

    Routing logic:
      - "end"            -> "end" (skip to response formatting)
      - "router"         -> checks step again (delegates to retrieval/tools/llm)
      - "retrieval"      -> "retrieval"
      - "tools"          -> "tools"
      - "uncertainty"    -> "uncertainty"
      - "feedback"       -> "uncertainty"  (feedback flows through uncertainty)
      - anything else    -> "llm" (safe fallback)

    Args:
        state: The current AgentState; only `next_step` is inspected.

    Returns:
        The literal name of the next graph node.
    """
    step = state.get("next_step", "end")

    if step == "end":
        return "end"
    elif step == "router":
        # After router, we determine the next step
        route = state.get("next_step", "llm")
        if route == "retrieval":
            return "retrieval"
        elif route == "tools":
            return "tools"
        else:
            return "llm"
    elif step == "retrieval":
        return "retrieval"
    elif step == "tools":
        return "tools"
    elif step == "uncertainty":
        return "uncertainty"
    elif step == "feedback":
        return "feedback"
    else:
        return "llm"


def after_retrieval(state: AgentState) -> Literal["tools", "llm", "uncertainty"]:
    """Route after retrieval to determine if tools are also needed.

    If retrieval found relevant documents, go to LLM for synthesis.
    Only go to tools if retrieval was empty AND the query clearly needs KPI data.
    On error, go to LLM for graceful error messaging.

    Heuristic for tool-forcing:
      - If `retrieved_docs` is non-empty → go directly to LLM.
      - If `retrieved_docs` is empty and the query contains KPI-related
        keywords such as "kpi", "metric", "how many" → route to tools
        so the agent can fetch live data.
      - Otherwise → route to uncertainty, since we have neither docs
        nor a clear data-fetching intent.

    Args:
        state: AgentState with `error`, `retrieved_docs`, and `user_input` set.

    Returns:
        One of "tools", "llm", or "uncertainty".
    """
    if state.get("error"):
        return "llm"

    docs_found = bool(state.get("retrieved_docs"))
    user_text = state.get("user_input", "").lower()

    if docs_found:
        return "llm"

    tool_indicators = ["kpi", "metric", "volume", "order volume",
                       "return rate", "units shipped", "fulfillment time",
                       "csat", "revenue", "average", "how many", "how much"]
    if any(kw in user_text for kw in tool_indicators):
        return "tools"

    # Fallback: if the LLM-based router classified this as a tools query
    # but no static keywords matched, still route to tools.
    if state.get("classification") == "tools":
        return "tools"

    return "uncertainty"


def build_graph():
    """Build and compile the LangGraph.

    Assembles the 9-node StateGraph with conditional edges and compiles it.
    The graph topology is:

        input ──▶ guardrails ──▶ (should_route)
                                   ├── router ──▶ (should_route)
                                   │                ├── retrieval ──▶ (after_retrieval)
                                   │                │                  ├── tools
                                   │                │                  ├── llm
                                   │                │                  └── uncertainty
                                   │                ├── tools
                                   │                ├── llm
                                   │                ├── uncertainty
                                   │                └── end ──▶ response ──▶ END
                                   ├── tools
                                   ├── llm
                                   ├── uncertainty
                                   └── end ──▶ response ──▶ END

        tools ──▶ (after_tools: if escalation_handled → uncertainty, else llm)
        llm   ──▶ uncertainty ──▶ feedback ──▶ response ──▶ END

    Returns:
        A compiled `langgraph.graph.graph.CompiledStateGraph` ready to invoke.
    """
    from langgraph.graph import StateGraph, END

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input", input_node)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("router", router_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("tools", tools_node)
    graph.add_node("llm", llm_node)
    graph.add_node("uncertainty", uncertainty_node)
    graph.add_node("feedback", feedback_node)
    graph.add_node("response", response_node)

    # Set entry point
    graph.set_entry_point("input")

    # Define edges
    graph.add_edge("input", "guardrails")

    # Conditional routing from guardrails
    graph.add_conditional_edges(
        "guardrails",
        should_route,
        {
            "retrieval": "router",
            "tools": "tools",
            "llm": "router",
            "uncertainty": "uncertainty",
            "end": "response",
        }
    )

    # Conditional routing from router
    graph.add_conditional_edges(
        "router",
        should_route,
        {
            "retrieval": "retrieval",
            "tools": "tools",
            "llm": "llm",
            "uncertainty": "uncertainty",
            "end": "response",
        }
    )

    # After retrieval, potentially run tools then continue
    graph.add_conditional_edges(
        "retrieval",
        after_retrieval,
        {"tools": "tools", "llm": "llm", "uncertainty": "uncertainty"},
    )

    # After tools: if escalation was handled, skip LLM; otherwise synthesize
    def after_tools(state: AgentState) -> Literal["llm", "uncertainty"]:
        if state.get("escalation_handled"):
            return "uncertainty"
        return "llm"

    graph.add_conditional_edges(
        "tools",
        after_tools,
        {"llm": "llm", "uncertainty": "uncertainty"},
    )

    # After LLM, proceed
    graph.add_edge("llm", "uncertainty")

    # After uncertainty, evaluate confidence
    graph.add_edge("uncertainty", "feedback")

    # After feedback, format response
    graph.add_edge("feedback", "response")

    # End
    graph.add_edge("response", END)

    return graph.compile()


def run_agent(user_input: str, session_id: str = None, feedback: str = None,
              prompt_variant: str = None) -> dict:
    """Run the agent with the given input and return the result.

    This is the public entry point used by the CLI (`deploy/cli.py`), the
    FastAPI server (`deploy/api.py`), and the evaluation harness.

    The function:
      1. Sets the `PROMPT_VARIANT` environment variable if provided.
      2. Builds the graph on first call (lazy singleton; subsequent calls
         reuse the compiled graph).
      3. Constructs a fresh `AgentState` with all fields initialised.
      4. Invokes the graph synchronously with `app.invoke(state)`.
      5. Measures wall-clock latency and attaches it as `total_latency_ms`.
      6. On any exception, logs the error and returns a safe fallback dict.

    Args:
        user_input: The raw question or command from the user.
        session_id: Optional session identifier for memory continuity.
            If None or empty, a new session is created inside the graph.
        feedback: Optional feedback signal ("positive" or "negative") to
            trigger the auto-tuning / adaptation loop. When provided the
            response cache is cleared for this session.
        prompt_variant: Optional name of the prompt strategy to use
            ("v1_minimal", "v2_safety_first", "v3_structured"). If None,
            the current value of the PROMPT_VARIANT env var is used.

    Returns:
        A dict containing the full result state with keys:
            "response" (str),
            "session_id" (str),
            "confidence" (float),
            "total_latency_ms" (float),
            "cached" (bool),
            "requires_escalation" (bool),
            "escalation_reason" (str),
            "adaptation_applied" (Optional[str]),
            "tool_calls" (list),
            "tool_results" (list),
            "error" (Optional[str]),
            and all other AgentState fields.

        On failure a minimal dict is returned with:
            "response": error message for the end-user,
            "error": raw exception string,
            "total_latency_ms": elapsed time,
            "session_id": the provided session_id,
            "confidence": 0.0.
    """
    if prompt_variant:
        os.environ["PROMPT_VARIANT"] = prompt_variant

    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    app = _compiled_graph
    state = AgentState(
        messages=[],
        user_input=user_input,
        response="",
        confidence=0.0,
        requires_escalation=False,
        escalation_reason="",
        escalation_handled=False,
        retrieved_docs=[],
        tool_calls=[],
        tool_results=[],
        next_step="",
        plan=[],
        feedback=feedback,
        session_id=session_id or "",
        adaptation_data={},
        adaptation_applied=None,
        cached=False,
        classification=None,
        error=None,
        latency_ms=0.0,
    )

    start = time.time()
    try:
        result = app.invoke(state)
        elapsed = round((time.time() - start) * 1000, 1)
        result["total_latency_ms"] = elapsed
        return result
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", error=str(e))
        return {
            "response": f"I encountered an error processing your request: {str(e)}. Please try again.",
            "error": str(e),
            "total_latency_ms": round((time.time() - start) * 1000, 1),
            "session_id": session_id or "",
            "confidence": 0.0,
        }
