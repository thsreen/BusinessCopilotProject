"""Main LangGraph StateGraph definition for the AI Operations Copilot."""
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
    """Process and validate incoming user input."""
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
    """Format the final response and add memory context."""
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
    """Route after guardrails."""
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
    On error, go to LLM for graceful error messaging."""
    if state.get("error"):
        return "llm"

    docs_found = bool(state.get("retrieved_docs"))
    user_text = state.get("user_input", "").lower()

    if docs_found:
        return "llm"

    tool_indicators = ["kpi", "metric", "volume", "order volume",
                       "average", "how many", "how much"]
    if any(kw in user_text for kw in tool_indicators):
        return "tools"

    return "uncertainty"


def build_graph():
    """Build and compile the LangGraph."""
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
    """Run the agent with the given input and return the result."""
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
