"""
Feedback node — persists user feedback and auto-generates prompt adaptations.

Purpose:
    This is the final node in the graph pipeline. It performs two
    independent functions:

    1. **Feedback storage** — when ``state["feedback"]`` is "positive"
       or "negative", the current interaction (input, response, confidence,
       topic, timestamp) is appended to ``feedback_store.json``.

    2. **Auto-tuning** — for each topic, the node tracks positive vs.
       negative counts. When the number of negatives for a topic crosses
       a topic-specific threshold (e.g. 2 for "fulfillment", 3 for "kpi")
       and the positive ratio is below 0.5, a pre-defined adaptation
       instruction is injected into the prompt on subsequent queries.
       This allows the system to self-correct without manual intervention.

    The module also exports ``get_adaptation_instructions()`` which is
    called by the LLM node to retrieve active instructions for the
    current query's topic.

State modifications:
    - Writes state["adaptation_applied"] when a new rule is generated.
    - Writes state["adaptation_data"] with the full adaptations dict.
    - Sets state["next_step"] = "end" unconditionally.
"""

import json
import os
import datetime
from agent.state import AgentState
from agent.filelock import locked_json_read_write
from agent.logging.logger import get_logger

logger = get_logger(__name__)

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "feedback_store.json",
)

# Topics the system can auto-tune. Drawn from NovaCart's primary
# operational domains. The "general" fallback is handled separately
# via get_adaptation_instructions combining topic + general adjustments.
TOPIC_KEYWORDS = ["fulfillment", "return", "csat", "kpi", "trend", "inventory", "revenue"]

# Each topic maps to:
#   - min_negatives:  how many negative feedback entries trigger tuning
#   - instruction:    the prompt instruction injected when tuning fires
#
# Thresholds are deliberately low (2–3 negatives) so the system adapts
# quickly without requiring a large feedback corpus.
ADAPTATION_RULES = {
    "fulfillment": {
        "min_negatives": 2,
        "instruction": (
            "When answering about fulfillment, always compare shipping times across "
            "all warehouses (A: Austin, B: Newark, C: Reno) and highlight any warehouse "
            "that exceeds the 24-hour SLA."
        ),
    },
    "return": {
        "min_negatives": 2,
        "instruction": (
            "When answering about returns, include the return rate percentage, the top "
            "categories by return volume, and any notable week-over-week changes."
        ),
    },
    "csat": {
        "min_negatives": 2,
        "instruction": (
            "When answering about CSAT, provide the current score, the trend direction, "
            "and compare against the 4.2 target. Include breakdown by channel if available."
        ),
    },
    "kpi": {
        "min_negatives": 3,
        "instruction": (
            "When answering KPI questions, present the data in a structured format with "
            "current value, target, variance, and trend direction. Prioritize the most "
            "recent 7 days of data."
        ),
    },
    "trend": {
        "min_negatives": 2,
        "instruction": (
            "When answering trend questions, include the direction (improving/declining), "
            "magnitude of change, and the date range analyzed. Highlight any anomalies."
        ),
    },
    "inventory": {
        "min_negatives": 2,
        "instruction": (
            "When answering about inventory, include current stock levels, any SKUs below "
            "threshold, and recent restock status."
        ),
    },
    "revenue": {
        "min_negatives": 2,
        "instruction": (
            "When answering about revenue, include the current period total, comparison "
            "to previous period, and breakdown by channel."
        ),
    },
}

# Simple in-memory cache keyed by file mtime to avoid re-reading
# feedback_store.json on every LLM call.
_adaptation_cache = None
_adaptation_cache_mtime = 0


def _detect_topic(text: str) -> str:
    """
    Identify the most relevant topic for *text* based on keyword matching.

    The first matching keyword in TOPIC_KEYWORDS wins. If none match,
    the topic defaults to "general". This is intentionally simple —
    a single keyword is sufficient for the auto-tuning use case.

    Args:
        text: The user's input string.

    Returns:
        A topic string from TOPIC_KEYWORDS, or "general".
    """
    text_lower = text.lower()
    for kw in TOPIC_KEYWORDS:
        if kw in text_lower:
            return kw
    return "general"


def _generate_adaptation(data: dict, topic: str) -> str | None:
    """
    Check feedback counts for *topic* and generate a new adaptation rule if needed.

    A rule is generated when:
      - Total feedback count >= 2 (minimum signal).
      - Negatives >= topic's ``min_negatives`` threshold.
      - Positive ratio < 0.5 (more negatives than positives or equal split).
      - The instruction has not already been applied.

    Args:
        data: The full feedback_store.json dict (must contain
            ``data["adaptations"][topic]`` with ``negatives``,
            ``positives``, and ``adjustments`` keys).
        topic: The detected topic string.

    Returns:
        The instruction string if a new adaptation was generated,
        or None if no action was taken.
    """
    adapt = data["adaptations"].get(topic)
    if not adapt:
        return None

    negatives = adapt.get("negatives", 0)
    positives = adapt.get("positives", 0)
    total = negatives + positives
    existing_adjustments = adapt.get("adjustments", [])

    # Need at least 2 feedback entries before we trust the signal.
    if total < 2:
        return None

    positive_ratio = positives / total if total > 0 else 0

    rule = ADAPTATION_RULES.get(topic)
    if not rule:
        return None

    if negatives >= rule["min_negatives"] and positive_ratio < 0.5:
        instruction = rule["instruction"]
        if instruction not in existing_adjustments:
            # Persist the new instruction so it survives restarts.
            existing_adjustments.append(instruction)
            data["adaptations"][topic]["adjustments"] = existing_adjustments
            logger.info(f"Auto-tuning applied for topic '{topic}': {instruction[:60]}...")
            return instruction
    return None


def get_adaptation_instructions(state: AgentState) -> str:
    """
    Retrieve active adaptation instructions for the current query's topic.

    Called by the LLM node. Uses a simple mtime-based cache to avoid
    re-reading the feedback file on every invocation. Returns a formatted
    string suitable for inclusion in the system prompt.

    The result includes both topic-specific and "general" adjustments,
    so that general-purpose corrections apply across all queries.

    Args:
        state: The AgentState dictionary (used to extract ``user_input``
            for topic detection).

    Returns:
        A markdown-formatted string of active instructions, or an empty
        string if none exist.
    """
    global _adaptation_cache, _adaptation_cache_mtime
    try:
        mtime = os.path.getmtime(FEEDBACK_FILE)
        # Invalidate the cache when the file has been modified externally
        # (e.g. by another process or by a previous feedback_node call).
        if mtime != _adaptation_cache_mtime:
            _adaptation_cache = None
    except OSError:
        # File may not exist yet — will be handled below.
        pass

    if _adaptation_cache is not None:
        adaptations = _adaptation_cache
    else:
        try:
            with open(FEEDBACK_FILE, "r") as f:
                adaptations = json.load(f).get("adaptations", {})
            _adaptation_cache = adaptations
            try:
                _adaptation_cache_mtime = os.path.getmtime(FEEDBACK_FILE)
            except OSError:
                pass
        except (FileNotFoundError, json.JSONDecodeError):
            adaptations = {}

    user_text = state.get("user_input", "")
    topic = _detect_topic(user_text)

    topic_adapt = adaptations.get(topic, {})
    adjustments = topic_adapt.get("adjustments", [])

    general_adjustments = adaptations.get("general", {}).get("adjustments", [])

    all_instructions = adjustments + general_adjustments
    if all_instructions:
        return (
            "## Auto-Tuning Instructions (from feedback)\n" +
            "\n".join(f"- {instr}" for instr in all_instructions)
        )
    return ""


VALID_FEEDBACK = {"positive", "negative"}


def feedback_node(state: AgentState) -> AgentState:
    """
    LangGraph node — persist user feedback and auto-generate adaptations.

    This is the terminal node and always sets ``state["next_step"] = "end"``.

    Workflow:
      1. Validate the feedback value (must be "positive" or "negative").
      2. Open ``feedback_store.json`` with a file lock for thread-safety.
      3. Detect the topic from user input.
      4. Append an interaction record to ``data["entries"]``.
      5. Increment the positive/negative counter for the detected topic.
      6. Call ``_generate_adaptation`` — if a new instruction is produced,
         store it in both the file and ``state["adaptation_applied"]``.
      7. Snapshot the full adaptations dict to ``state["adaptation_data"]``.
      8. Invalidate the adaptation cache so the LLM node picks up changes
         on the very next request.

    Args:
        state: The shared AgentState dictionary. Reads ``feedback``,
            ``user_input``, ``response``, ``confidence``, and ``session_id``.
            Writes ``adaptation_applied``, ``adaptation_data``, and
            ``next_step``.

    Returns:
        The mutated *state* dictionary.
    """
    feedback = state.get("feedback")
    if feedback and feedback not in VALID_FEEDBACK:
        logger.warning(f"Invalid feedback value: {feedback}")
        feedback = None

    if feedback:
        # locked_json_read_write provides a thread-/process-safe way
        # to read-modify-write the JSON file. The default structure
        # ensures the file is initialised on first access.
        with locked_json_read_write(FEEDBACK_FILE, default={"entries": [], "adaptations": {}}) as data:
            topic = _detect_topic(state.get("user_input", ""))

            entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "session_id": state.get("session_id", "unknown"),
                "user_input": state.get("user_input", ""),
                "response": state.get("response", ""),
                "feedback": feedback,
                "confidence": state.get("confidence", 0.0),
                "topic": topic,
            }
            data["entries"].append(entry)

            # Ensure the adaptation tracking structure exists for this topic.
            if topic not in data["adaptations"]:
                data["adaptations"][topic] = {"negatives": 0, "positives": 0, "adjustments": []}
            if feedback == "negative":
                data["adaptations"][topic]["negatives"] += 1
            elif feedback == "positive":
                data["adaptations"][topic]["positives"] += 1

            adapted = _generate_adaptation(data, topic)
            if adapted:
                state["adaptation_applied"] = adapted
                logger.info(f"Auto-tuned prompt for topic '{topic}'")

            state["adaptation_data"] = dict(data.get("adaptations", {}))

        # Force cache re-read on next LLM call by resetting the mtime.
        global _adaptation_cache_mtime
        _adaptation_cache_mtime = 0

    state["next_step"] = "end"
    return state
