"""Shared intent classification constants for routing and tool selection."""

KNOWLEDGE_KEYWORDS = [
    "policy", "procedure", "sop", "handbook", "guideline",
    "what is", "how does", "explain", "define", "tell me about",
    "sla", "target", "threshold", "recall", "incident",
]

TOOL_KEYWORDS = [
    "what was", "what is the", "show me", "compare", "trend",
    "how many", "how much", "average", "kpi", "metric",
    "order volume", "return rate",
    "revenue", "units shipped",
]

QUERY_KPI_KEYWORDS = [
    "kpi", "metric", "order volume", "return rate",
    "csat", "revenue", "how many", "how much", "average",
    "wait time", "fulfillment time", "units shipped",
]

TREND_KEYWORDS = [
    "trend", "over time", "compare", "change", "pattern",
]

ESCALATION_KEYWORDS = [
    "escalate", "human", "manager", "speak to",
]
