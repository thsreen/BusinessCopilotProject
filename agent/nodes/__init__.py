"""
LangGraph node implementations.

This package contains all LangGraph node functions that form the
conversational agent's computation graph. Each module implements
one step in the pipeline: guardrails -> router -> retrieval/tools/llm
-> uncertainty -> feedback -> end.

Nodes read from and write to a shared AgentState dictionary, which
carries all context across the graph execution cycle.
"""

