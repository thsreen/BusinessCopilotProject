
# Substrings indicating the user is asking about documented processes,
# policies, SLAs, or incident records. When matched, the agent prefers
# the RAG retrieval path over tool execution.
KNOWLEDGE_KEYWORDS = [
    "policy", "procedure", "sop", "handbook", "guideline",
    "how does", "explain", "define", "tell me about",
    "sla", "target", "threshold", "recall", "incident",
]

# Substrings that suggest a data-fetching KPI query (e.g. "show me
# return rates"). These route the agent toward tool execution rather
# than document retrieval.
TOOL_KEYWORDS = [
    "what was", "what is the", "show me", "compare", "trend",
    "how many", "how much", "average", "kpi", "metric",
    "order volume", "return rate",
    "revenue", "units shipped",
]

# A subset of TOOL_KEYWORDS that specifically targets quantitative
# KPI lookups. Used by ``after_retrieval`` as a heuristic to force
# tool execution when RAG returns no results.
QUERY_KPI_KEYWORDS = [
    "kpi", "metric", "order volume", "return rate",
    "csat", "revenue", "how many", "how much", "average",
    "wait time", "fulfillment time", "units shipped",
]

# Substrings that indicate a comparison or time-series request,
# typically routed to a trend_analysis tool.
TREND_KEYWORDS = [
    "trend", "over time", "compare", "change", "pattern",
]

# Substrings that trigger immediate escalation to a human operator.
# Checked early in the routing pipeline so that sensitive requests
# bypass the normal LLM / tool flow.
ESCALATION_KEYWORDS = [
    "escalate", "human", "manager", "speak to",
]
