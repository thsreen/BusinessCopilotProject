
import datetime
import json
import os
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Literal

# All interactions are logged as JSON lines for audit / comparison.
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "v1b_langgraph_baseline.log")

# ── State ─────────────────────────────────────────────────────────────────

class AgentState(TypedDict):

    messages: List[Dict[str, str]]
    next_step: str
    response: str
    confidence: float
    requires_escalation: bool

# ── Mock LLM ──────────────────────────────────────────────────────────────

class MockLLM:

    def invoke(self, prompt: str, **kwargs) -> str:
        """Return a template response matching the *prompt*."""
        prompt_lower = prompt.lower()
        if "fulfillment" in prompt_lower:
            return "Based on available data, fulfillment times are within operational targets. For detailed metrics, please refer to the daily ops dashboard."
        elif "return" in prompt_lower:
            return "Return rates are monitored daily. Current metrics indicate rates are within the 8% threshold."
        elif "csat" in prompt_lower:
            return "Customer satisfaction scores are at 4.2 or above. Detailed breakdown by channel is available."
        elif "kpi" in prompt_lower or "metric" in prompt_lower:
            return "Key operational metrics include: Order Volume, Fulfillment Time (avg & p95), Return Rate, CSAT, Wait Time, Revenue, and Inventory Accuracy."
        elif "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I am the NovaCart Operations Copilot. I can help you understand operational metrics and identify trends. How can I assist you today?"
        elif "help" in prompt_lower:
            return "I can answer questions about fulfillment, return rates, customer satisfaction, KPIs, warehouses, and operational trends. Please ask a specific question."
        else:
            return "I am a decision-support agent and can only provide information about operational metrics. Please ask about fulfillment, returns, CSAT, or other KPIs."

# ── Graph Nodes ───────────────────────────────────────────────────────────

def input_node(state: AgentState) -> AgentState:
    """Initialise state for a new turn.

    Resets ``response``, ``confidence``, and ``requires_escalation`` to their
    defaults.  Sets ``next_step`` to ``"process"`` so the guardrails node
    runs next.
    """
    if not state.get("messages"):
        state["messages"] = []
    state["next_step"] = "process"
    state["response"] = ""
    state["confidence"] = 0.0
    state["requires_escalation"] = False
    return state

def guardrails_node(state: AgentState) -> AgentState:

    last_message = state["messages"][-1]["content"] if state["messages"] else ""
    content_lower = last_message.lower()

    # Check for data modification requests
    modification_keywords = ["update", "change", "modify", "delete", "remove", "set", "override"]
    safety_patterns = [
        ("change policy", "I am a decision-support only system and cannot modify policies."),
        ("update data", "This system is read-only. I cannot update data."),
        ("delete record", "I cannot delete records. Please contact an operations analyst."),
    ]

    for kw in modification_keywords:
        if kw in content_lower:
            state["response"] = f"I am a decision-support only system and cannot '{kw}' any data or settings. Please escalate to an operations analyst."
            state["next_step"] = "end"
            return state

    for pattern, refusal_msg in safety_patterns:
        if pattern in content_lower:
            state["response"] = refusal_msg
            state["next_step"] = "end"
            return state

    state["next_step"] = "llm"
    return state

def llm_node(state: AgentState) -> AgentState:
    """Call the (mock) LLM and store its answer in *state*.

    The confidence is hard-coded to 0.7 so that the uncertainty node has
    something to work with later when a real model is in place.
    """
    last_message = state["messages"][-1]["content"] if state["messages"] else ""
    llm = MockLLM()
    response = llm.invoke(last_message)
    state["response"] = response
    state["confidence"] = 0.7  # Mock confidence - always moderate
    state["next_step"] = "output"
    return state

def uncertainty_node(state: AgentState) -> AgentState:
    """Append a low-confidence disclaimer when ``confidence < 0.5``.

    With the mock LLM this never fires (confidence is always 0.7), but it
    demonstrates the pattern for when a real model produces uncertain
    answers.
    """
    if state["confidence"] < 0.5:
        state["response"] += "\n\n[Note: I have low confidence in this response. Please verify with a human analyst.]"
    return state

def output_node(state: AgentState) -> AgentState:
    """Persist the current turn to the JSON-lines log file.

    The log entry captures the full conversation so far, the final response,
    confidence, and escalation flag.
    """
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "messages": state["messages"],
        "response": state["response"],
        "confidence": state["confidence"],
        "requires_escalation": state["requires_escalation"],
    }
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    return state

def should_continue(state: AgentState) -> Literal["llm", "output", "end"]:

    return state["next_step"]

# ── Build Graph ───────────────────────────────────────────────────────────

def create_graph():

    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(AgentState)

        graph.add_node("input", input_node)
        graph.add_node("guardrails", guardrails_node)
        graph.add_node("llm", llm_node)
        graph.add_node("output", output_node)

        graph.set_entry_point("input")
        graph.add_edge("input", "guardrails")
        graph.add_conditional_edges(
            "guardrails",
            should_continue,
            {"llm": "llm", "end": "output", "output": "output"},
        )
        graph.add_edge("llm", "output")
        graph.add_edge("output", END)

        return graph.compile()
    except ImportError:
        print("WARNING: langgraph not installed. Running in mock mode without graph.")
        return None

def main():
    """REPL loop that feeds user input through the LangGraph (or manual fallback)."""
    print("=" * 60)
    print("  NovaCart Ops Copilot v1b (Minimal LangGraph Baseline)")
    print("  LangGraph framework + Mock LLM - No Real Intelligence")
    print("=" * 60)
    print("\nType 'quit' to exit.\n")

    app = create_graph()

    if app is None:
        # Fallback: run nodes manually
        print("[Running in fallback mode - no graph]\n")
        state = AgentState(messages=[], next_step="", response="", confidence=0.0, requires_escalation=False)
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if not user_input or user_input.lower() in ("quit", "exit", "bye"):
                print("Assistant: Goodbye!")
                break
            state["messages"] = [{"role": "user", "content": user_input}]
            state = input_node(state)
            state = guardrails_node(state)
            if state["next_step"] == "llm":
                state = llm_node(state)
            state = uncertainty_node(state)
            state = output_node(state)
            print(f"Assistant: {state['response']}\n")
    else:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            if not user_input or user_input.lower() in ("quit", "exit", "bye"):
                print("Assistant: Goodbye!")
                break
            state = AgentState(
                messages=[{"role": "user", "content": user_input}],
                next_step="", response="", confidence=0.0, requires_escalation=False,
            )
            result = app.invoke(state)
            print(f"Assistant: {result['response']}\n")

    print("Session ended.")

if __name__ == "__main__":
    main()
