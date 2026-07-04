"""Memory management module for conversation state.

This package provides ``MemoryManager`` — a two-tier storage system:

- **Short-term**: In-memory Python dict offering O(1) access to recent
  messages for active sessions.
- **Long-term**: SQLite database persisted to ``<project_root>/memory_store/``
  that records every message and per-session user preferences.

Typical usage::

    from agent.memory.manager import MemoryManager

    mm = MemoryManager()
    session_id = mm.create_session()
    mm.add_message(session_id, "user", "Hello")
    print(mm.get_history(session_id))
    mm.close()
"""

from .manager import MemoryManager

__all__ = ["MemoryManager"]
