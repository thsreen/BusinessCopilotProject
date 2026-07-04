"""Logging module for the AI Operations Copilot.

This package provides PII-safe structured logging:

- ``PiiSafeLogger`` — a logger that redacts emails, phone numbers,
  credit card numbers, SSNs, and honorific-based names from all
  messages before writing them as individual JSON lines to a file.

- ``get_logger()`` — a cached factory that returns one instance per
  logger name, following the standard ``logging.getLogger()`` pattern.

Typical usage::

    from agent.logging.logger import get_logger

    logger = get_logger("agent.llm")
    logger.info("LLM request started", session_id=sid, model="gpt-4o")
    logger.error("LLM request failed", error=str(e))
"""

from .logger import PiiSafeLogger, get_logger, scrub_pii

__all__ = ["PiiSafeLogger", "get_logger", "scrub_pii"]
