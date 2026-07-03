"""Uncertainty assessment node - evaluates confidence and adds disclaimers."""
from agent.state import AgentState


def uncertainty_node(state: AgentState) -> AgentState:
    retrieved_docs = state.get("retrieved_docs", [])
    tool_results = state.get("tool_results", [])
    has_data = bool(retrieved_docs) or bool(tool_results)

    if not has_data and state["confidence"] > 0.3:
        state["response"] = (state.get("response", "") +
            "\n\n[Note: I do not have specific data on this topic in my knowledge base. "
            "This response is based on general understanding and may not reflect current "
            "NovaCart operations. Please verify with a human analyst.]")
        state["confidence"] = 0.3

    if state["confidence"] < 0.3:
        state["response"] = state.get("response", "") + (
            "\n\nI recommend escalating this question to a human analyst who can "
            "access the specific data needed. You can escalate by asking me to "
            "'escalate to a human'."
        )
        state["requires_escalation"] = True

    state["next_step"] = "feedback"
    return state
