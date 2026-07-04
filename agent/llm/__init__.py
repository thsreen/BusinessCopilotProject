"""LLM integration module for the AI Operations Copilot.

This package provides:

- ``LLMClient`` — a unified client that wraps OpenAI and Ollama APIs
  with automatic fallback between providers.

- ``get_prompt()`` — a template resolver that selects and fills one of
  three prompt variants (Minimal, Safety-First, Structured) based on
  the current conversation context.

Typical usage::

    from agent.llm.client import LLMClient
    from agent.llm.prompts import get_prompt

    client = LLMClient()
    prompt = get_prompt("v3_structured", user_input=user_msg, context=docs)
    reply = client.invoke(prompt)
"""

# Public API
from .client import LLMClient
from .prompts import get_prompt

__all__ = ["LLMClient", "get_prompt"]
