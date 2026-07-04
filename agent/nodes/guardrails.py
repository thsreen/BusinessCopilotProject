"""
Safety guardrails node — runs first in the graph pipeline.

Purpose:
    Inspects user input for disallowed content before it reaches
    any other node. Three checks are performed in order:
      1. PII detection — refuses to process if sensitive data is found.
      2. Modification detection — refuses data/policy change requests.
      3. Escalation detection — routes to tools if a human is requested.

State modifications:
    - Sets state["response"] with a refusal or escalation message.
    - Sets state["confidence"] = 1.0 on refusal (deterministic block).
    - Sets state["next_step"] to "end", "tools", or "router".
    - Sets state["requires_escalation"] and state["escalation_reason"]
      when escalation keywords are detected.
"""

import re
from agent.state import AgentState


# Each tuple: (regex_pattern, is_blocking)
# is_blocking is reserved for future severity levels but kept for
# consistency across the pattern list. All matched patterns currently
# result in a hard refusal.
MODIFICATION_PATTERNS = [
    (r"(update|change|modify|edit|set|override|adjust)\s+(the\s+)?(policy|rule|sla|target|threshold|kpi|data|record|order|inventory|price|return)", True),
    (r"(delete|remove|erase|clear|cancel|void)\s+(the\s+)?(order|record|customer|data|product|policy)", True),
    (r"write\s+(to|a|new)\s+(database|system|record)", True),
    (r"create\s+(a\s+)?(new\s+)?(order|record|policy|rule)", True),
]

# Email, phone, credit-card-like digits, and SSN patterns.
# These are intentionally broad — better to over-match and refuse
# than to accidentally process PII.
PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    r"\b\d{16}\b",
    r"\b(ssn|social security)\s*:\s*\d{3}-\d{2}-\d{4}\b",
]

# Keywords and phrases that indicate a user wants human intervention.
# Also covers urgency markers (urgent, emergency, critical) and
# dissatisfaction signals that should not be handled by the bot alone.
ESCALATION_PATTERNS = [
    r"(escalate|human|manager|supervisor|speak\s+to|talk\s+to|contact)",
    r"(urgent|emergency|critical|immediate|asap)",
    r"(complaint|unhappy|dissatisfied|escalation)",
    r"(not\s+helping|useless|wrong|incorrect)",
]


def check_modification(text: str) -> tuple[bool, str]:
    """
    Scan *text* for modification/creation/deletion intents.

    Args:
        text: The raw user input string.

    Returns:
        A tuple of (is_modification_request, refusal_message).
        If no modification intent is found, refusal_message is empty.
    """
    for pattern, _ in MODIFICATION_PATTERNS:
        if re.search(pattern, text.lower()):
            # Return a clear, actionable refusal that points the user
            # to the escalation path as a fallback.
            return True, (
                "I am a decision-support only system and cannot modify data, "
                "policies, or configurations. Please contact an operations analyst "
                "for assistance. If this is urgent, use the escalation tool to "
                "reach a human."
            )
    return False, ""


def check_pii(text: str) -> bool:
    """
    Detect personally identifiable information in *text*.

    Args:
        text: The raw user input string.

    Returns:
        True if any PII pattern is matched, False otherwise.
    """
    for pattern in PII_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def check_escalation(text: str) -> bool:
    """
    Detect escalation or urgency signals in *text*.

    Args:
        text: The raw user input string.

    Returns:
        True if any escalation keyword is found, False otherwise.
    """
    for pattern in ESCALATION_PATTERNS:
        if re.search(pattern, text.lower()):
            return True
    return False


def guardrails_node(state: AgentState) -> AgentState:
    """
    LangGraph node — entry gate for all user input.

    Checks are applied in priority order:
      1. PII → hard block with response, end immediately.
      2. Modification → hard block with refusal message, end immediately.
      3. Escalation → set escalation flags, route to tools node.
      4. Clear → route to router node for normal processing.

    Args:
        state: The shared AgentState dictionary. Reads ``user_input``
            (or the last message content as fallback). Writes ``response``,
            ``confidence``, ``next_step``, and optionally escalation fields.

    Returns:
        The mutated *state* dictionary.
    """
    user_text = state.get("user_input", "")
    if not user_text and state.get("messages"):
        # Fallback: use the content of the most recent message when
        # user_input is not populated directly.
        user_text = state["messages"][-1].get("content", "")

    # --- PII check (highest priority) ---
    if check_pii(user_text):
        state["response"] = (
            "I detected potentially sensitive information (PII) in your input. "
            "Please avoid sharing personal data. I cannot process requests "
            "containing personal identifiable information."
        )
        state["confidence"] = 1.0
        state["next_step"] = "end"
        return state

    # --- Modification check ---
    is_mod, refusal_msg = check_modification(user_text)
    if is_mod:
        state["response"] = refusal_msg
        state["confidence"] = 1.0
        state["next_step"] = "end"
        return state

    # --- Escalation check ---
    if check_escalation(user_text):
        state["requires_escalation"] = True
        state["escalation_reason"] = "User requested human escalation or used urgency keywords."
        state["next_step"] = "tools"
        return state

    # --- Nothing triggered → normal routing ---
    state["next_step"] = "router"
    return state
