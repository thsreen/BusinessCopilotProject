"""
AI Operations Copilot — NovaCart Business Decision Support Agent.

This package implements a LangGraph-based conversational agent that
answers operational questions about NovaCart's e-commerce business.
It combines:

  - **Retrieval Augmented Generation (RAG)** over SOP, policy, and
    incident documents stored in Chroma DB.
  - **Tool execution** against synthetic KPI data (order volumes,
    return rates, CSAT scores, fulfillment times, etc.).
  - **Safety guardrails** that detect write / destructive intent and
    refuse with an explanation.
  - **Auto-tuning**: feedback from the user is fed back into the
    prompt strategy to adapt the agent's behaviour over time.
  - **Response caching** (TTL-based LRU) to avoid re-generating the
    same answer for identical queries.

Sub-packages:
  - ``agent.nodes`` — Individual LangGraph node implementations
    (guardrails, router, retrieval, tools, llm, uncertainty, feedback).
  - ``agent.memory`` — Session memory management (short-term message
    history + long-term context extraction).
  - ``agent.logging`` — Structured logging helpers.
  - ``deploy`` — CLI and FastAPI server for user-facing interaction.
  - ``tests`` — Evaluation scenarios and scoring.

Entry point:
  ``agent.graph.run_agent(user_input, session_id, feedback, prompt_variant)``
"""
