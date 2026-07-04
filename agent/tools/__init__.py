"""Tool definitions for the AI Operations Copilot.

This package exposes the tool functions and schemas that the agent can invoke
at runtime. Each module in this package implements one callable tool whose
signature and description are registered in definitions.py.

Tools available:
    - query_kpi_data   : Query historical KPI metrics from CSV data sources.
    - get_trend_analysis: Analyse trends, averages, and anomalies in KPI data.
    - escalate_to_analyst: Log an escalation to a human operations analyst.
"""
