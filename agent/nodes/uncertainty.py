"""
Uncertainty assessment node — evaluates response confidence and adds disclaimers.

Purpose:
    After the LLM node produces a response (or after a direct tool
    response), this node reviews the available evidence and the
    assigned confidence score. If confidence is low, it appends
    disclaimers or prompts the user to escalate.

    Two thresholds drive behaviour:
      - confidence > 0.3 but no data → reduce to 0.3, add disclaimer.
      - confidence < 0.3             → suggest human escalation.

State modifications:
    - Appends disclaimers to state["response"].
    - May reduce state["confidence"].
    - Sets state["requires_escalation"] = True when confidence is very low.
    - Sets state["next_step"] = "feedback".
"""

from agent.state import AgentState


def uncertainty_node(state: AgentState) -> AgentState:
    """
    LangGraph node — assess and adjust confidence, append disclaimers.

    Logic:
      1. If the LLM generated a response with moderate confidence (>0.3)
         but had **no** retrieved documents and **no** tool results, the
         response is based purely on parametric (training) knowledge.
         A disclaimer is appended and confidence is capped at 0.3.
      2. If confidence is already below 0.3, the response is considered
         unreliable. A stronger escalation prompt is appended and the
         ``requires_escalation`` flag is set so downstream nodes or the
         front-end can offer a hand-off.

    Args:
        state: The shared AgentState dictionary. Reads ``retrieved_docs``,
            ``tool_results``, and ``confidence``. May append to
            ``response``, adjust ``confidence``, and set
            ``requires_escalation``.

    Returns:
        The mutated *state* dictionary.
    """
    retrieved_docs = state.get("retrieved_docs", [])
    tool_results = state.get("tool_results", [])
    has_data = bool(retrieved_docs) or bool(tool_results)

    # Case: moderate confidence but no factual backing.
    # The threshold 0.3 is chosen to catch responses that are neither
    # clearly confident nor clearly uncertain — the "grey zone" where
    # a disclaimer is most valuable.
    if not has_data and state["confidence"] > 0.3:
        state["response"] = (
            state.get("response", "") +
            "\n\n[Note: I do not have specific data on this topic in my knowledge base. "
            "This response is based on general understanding and may not reflect current "
            "NovaCart operations. Please verify with a human analyst.]"
        )
        state["confidence"] = 0.3

    # Case: very low confidence — the LLM itself is unsure.
    # Escalation is the safest action.
    if state["confidence"] < 0.3:
        state["response"] = state.get("response", "") + (
            "\n\nI recommend escalating this question to a human analyst who can "
            "access the specific data needed. You can escalate by asking me to "
            "'escalate to a human'."
        )
        state["requires_escalation"] = True

    state["next_step"] = "feedback"
    return state
