
TOOL_DEFINITIONS = [
    {
        # ------------------------------------------------------------------
        # Tool 1: query_kpi_data
        # Queries one of four CSV data files (daily_metrics,
        # daily_category_metrics, daily_warehouse_metrics,
        # daily_channel_metrics) based on the supplied filters. Read-only.
        # ------------------------------------------------------------------
        "name": "query_kpi_data",
        "description": (
            "Query historical KPI data for a specific metric or set of "
            "metrics. Returns daily values for the requested period. "
            "Read-only access."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": (
                        "The KPI metric to query (e.g., order_volume, "
                        "fulfillment_time_avg, return_rate, csat_score, "
                        "revenue)"
                    ),
                },
                "period": {
                    "type": "string",
                    "description": (
                        "Time period (e.g., 'last 7 days', 'last 30 days', "
                        "'this month', or specific date range)"
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Optional: Filter by product category (Electronics, "
                        "Clothing, Home & Garden, Books, Sports & Outdoors, "
                        "Beauty & Health, Toys & Games, Automotive)"
                    ),
                },
                "warehouse": {
                    "type": "string",
                    "description": "Optional: Filter by warehouse (A, B, C)",
                },
                "channel": {
                    "type": "string",
                    "description": "Optional: Filter by channel (web, mobile, phone)",
                },
            },
            "required": ["metric"],
        },
    },
    {
        # ------------------------------------------------------------------
        # Tool 2: get_trend_analysis
        # Computes averages, split-half trend direction, and anomaly
        # detection (1.5-sigma rule) on a KPI time series. Read-only.
        # ------------------------------------------------------------------
        "name": "get_trend_analysis",
        "description": (
            "Analyze trends in operational metrics over time. Detects "
            "anomalies, computes averages, and identifies patterns. "
            "Read-only access."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": (
                        "The metric to analyze (order_volume, "
                        "fulfillment_time_avg, fulfillment_time_p95, "
                        "return_rate, csat_score, revenue, etc.)"
                    ),
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default 30)",
                },
                "category": {
                    "type": "string",
                    "description": "Optional: Filter by category",
                },
                "warehouse": {
                    "type": "string",
                    "description": "Optional: Filter by warehouse",
                },
                "channel": {
                    "type": "string",
                    "description": "Optional: Filter by channel",
                },
            },
            "required": ["metric"],
        },
    },
    {
        # ------------------------------------------------------------------
        # Tool 3: escalate_to_analyst
        # Persists an escalation request to a JSON log file and returns
        # instructions for the user to contact the operations team.
        # ------------------------------------------------------------------
        "name": "escalate_to_analyst",
        "description": (
            "Escalate a question or issue to a human operations analyst. "
            "Use when the user requests a human, when confidence is low, "
            "or when the request is outside the agent's scope."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason for escalation",
                },
                "details": {
                    "type": "string",
                    "description": "Additional context or details",
                },
            },
            "required": ["reason"],
        },
    },
]
