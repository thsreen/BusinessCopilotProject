"""Feedback node - stores user feedback, adapts prompt strategies."""
import json
import os
import datetime
from agent.state import AgentState
from agent.filelock import locked_json_read_write
from agent.logging.logger import get_logger

logger = get_logger(__name__)

FEEDBACK_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "feedback_store.json"
)

TOPIC_KEYWORDS = ["fulfillment", "return", "csat", "kpi", "trend", "inventory", "revenue"]

ADAPTATION_RULES = {
    "fulfillment": {
        "min_negatives": 2,
        "instruction": "When answering about fulfillment, always compare shipping times across all warehouses (A: Austin, B: Newark, C: Reno) and highlight any warehouse that exceeds the 24-hour SLA.",
    },
    "return": {
        "min_negatives": 2,
        "instruction": "When answering about returns, include the return rate percentage, the top categories by return volume, and any notable week-over-week changes.",
    },
    "csat": {
        "min_negatives": 2,
        "instruction": "When answering about CSAT, provide the current score, the trend direction, and compare against the 4.2 target. Include breakdown by channel if available.",
    },
    "kpi": {
        "min_negatives": 3,
        "instruction": "When answering KPI questions, present the data in a structured format with current value, target, variance, and trend direction. Prioritize the most recent 7 days of data.",
    },
    "trend": {
        "min_negatives": 2,
        "instruction": "When answering trend questions, include the direction (improving/declining), magnitude of change, and the date range analyzed. Highlight any anomalies.",
    },
    "inventory": {
        "min_negatives": 2,
        "instruction": "When answering about inventory, include current stock levels, any SKUs below threshold, and recent restock status.",
    },
    "revenue": {
        "min_negatives": 2,
        "instruction": "When answering about revenue, include the current period total, comparison to previous period, and breakdown by channel.",
    },
}

_adaptation_cache = None
_adaptation_cache_mtime = 0


def _detect_topic(text: str) -> str:
    text_lower = text.lower()
    for kw in TOPIC_KEYWORDS:
        if kw in text_lower:
            return kw
    return "general"


def _generate_adaptation(data: dict, topic: str) -> str | None:
    """Generate auto-tuning instruction if feedback pattern warrants it."""
    adapt = data["adaptations"].get(topic)
    if not adapt:
        return None

    negatives = adapt.get("negatives", 0)
    positives = adapt.get("positives", 0)
    total = negatives + positives
    existing_adjustments = adapt.get("adjustments", [])

    if total < 2:
        return None

    positive_ratio = positives / total if total > 0 else 0

    rule = ADAPTATION_RULES.get(topic)
    if not rule:
        return None

    if negatives >= rule["min_negatives"] and positive_ratio < 0.5:
        instruction = rule["instruction"]
        if instruction not in existing_adjustments:
            existing_adjustments.append(instruction)
            data["adaptations"][topic]["adjustments"] = existing_adjustments
            logger.info(f"Auto-tuning applied for topic '{topic}': {instruction[:60]}...")
            return instruction
    return None


def get_adaptation_instructions(state: AgentState) -> str:
    """Retrieve active adaptation instructions for the current query topic."""
    global _adaptation_cache, _adaptation_cache_mtime
    try:
        mtime = os.path.getmtime(FEEDBACK_FILE)
        if mtime != _adaptation_cache_mtime:
            _adaptation_cache = None
    except OSError:
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
        return "## Auto-Tuning Instructions (from feedback)\n" + "\n".join(
            f"- {instr}" for instr in all_instructions
        )
    return ""


VALID_FEEDBACK = {"positive", "negative"}


def feedback_node(state: AgentState) -> AgentState:
    feedback = state.get("feedback")
    if feedback and feedback not in VALID_FEEDBACK:
        logger.warning(f"Invalid feedback value: {feedback}")
        feedback = None
    if feedback:
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

        global _adaptation_cache_mtime
        _adaptation_cache_mtime = 0

    state["next_step"] = "end"
    return state
