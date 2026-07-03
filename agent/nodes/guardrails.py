"""Safety guardrails node - refuses data modification, checks PII, validates scope."""
import re
from agent.state import AgentState


MODIFICATION_PATTERNS = [
    (r"(update|change|modify|edit|set|override|adjust)\s+(the\s+)?(policy|rule|sla|target|threshold|kpi|data|record|order|inventory|price|return)", True),
    (r"(delete|remove|erase|clear|cancel|void)\s+(the\s+)?(order|record|customer|data|product|policy)", True),
    (r"write\s+(to|a|new)\s+(database|system|record)", True),
    (r"create\s+(a\s+)?(new\s+)?(order|record|policy|rule)", True),
]

PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    r"\b\d{16}\b",
    r"\b(ssn|social security)\s*:\s*\d{3}-\d{2}-\d{4}\b",
]

ESCALATION_PATTERNS = [
    r"(escalate|human|manager|supervisor|speak\s+to|talk\s+to|contact)",
    r"(urgent|emergency|critical|immediate|asap)",
    r"(complaint|unhappy|dissatisfied|escalation)",
    r"(not\s+helping|useless|wrong|incorrect)",
]


def check_modification(text: str) -> tuple[bool, str]:
    for pattern, _ in MODIFICATION_PATTERNS:
        if re.search(pattern, text.lower()):
            return True, f"I am a decision-support only system and cannot modify data, policies, or configurations. Please contact an operations analyst for assistance. If this is urgent, use the escalation tool to reach a human."
    return False, ""


def check_pii(text: str) -> bool:
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def check_escalation(text: str) -> bool:
    for pattern in ESCALATION_PATTERNS:
        if re.search(pattern, text.lower()):
            return True
    return False


def guardrails_node(state: AgentState) -> AgentState:
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        user_text = state["messages"][-1].get("content", "")

    # Check PII in input
    if check_pii(user_text):
        state["response"] = "I detected potentially sensitive information (PII) in your input. Please avoid sharing personal data. I cannot process requests containing personal identifiable information."
        state["confidence"] = 1.0
        state["next_step"] = "end"
        return state

    # Check modification requests
    is_mod, refusal_msg = check_modification(user_text)
    if is_mod:
        state["response"] = refusal_msg
        state["confidence"] = 1.0
        state["next_step"] = "end"
        return state

    # Check escalation - route to tools for escalation execution
    if check_escalation(user_text):
        state["requires_escalation"] = True
        state["escalation_reason"] = "User requested human escalation or used urgency keywords."
        state["next_step"] = "tools"
        return state

    state["next_step"] = "router"
    return state
