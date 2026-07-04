"""Conversation memory manager — short-term and long-term storage.

Architecture
------------
The ``MemoryManager`` implements a **two-tier** memory system:

1. **Short-term (in-memory)** — An ``_sessions`` dictionary that holds
   the most recent messages for every active session.  This provides
   O(1) access for the common "get last N messages" pattern without
   hitting the database.

2. **Long-term (SQLite)** — A persistent ``conversations`` table that
   stores every message with a timestamp and arbitrary metadata JSON.
   A separate ``user_preferences`` table stores per-session key-value
   preferences.

Session lifecycle
-----------------
- ``create_session()`` generates a short UUID and initialises an empty
  in-memory list.
- ``add_message()`` writes to *both* tiers simultaneously.
- ``get_history()`` first checks the in-memory dict; on a cache miss it
  queries SQLite and populates the in-memory cache.
- ``reset_session()`` clears the in-memory list (the long-term record
  is preserved for audit purposes).
- ``clear_all()`` wipes both tiers.

Storage location
----------------
The SQLite database is placed in ``<project_root>/memory_store/conversations.db``.
The directory is created automatically on first use.
"""
import json
import os
import sqlite3
import datetime
import uuid

# Path to the long-term storage directory and SQLite database file.
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "memory_store")
DB_PATH = os.path.join(MEMORY_DIR, "conversations.db")


class MemoryManager:
    """Manages conversation memory with session-based short-term and long-term storage.

    Usage::

        mm = MemoryManager()
        sid = mm.create_session()
        mm.add_message(sid, "user", "What was yesterday's order volume?")
        history = mm.get_history(sid, limit=5)
        mm.close()
    """

    def __init__(self):
        """Open (or create) the SQLite database and initialise the in-memory cache.

        Side effects
        ------------
        - Creates the ``memory_store/`` directory if it does not exist.
        - Opens a SQLite connection with ``check_same_thread=False`` so
          that the manager can be used from any thread.
        - Enables WAL journal mode for better concurrent read performance.
        - Ensures the ``conversations`` and ``user_preferences`` tables
          and the session index exist.
        """
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # WAL mode allows concurrent reads without blocking on writes,
        # which is important for a multi-threaded agent server.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()
        # In-memory short-term store: session_id -> list of message dicts.
        self._sessions: dict[str, list] = {}

    def _init_db(self):
        """Create the database schema if it does not already exist.

        Tables
        ------
        conversations
            Stores every message with session_id, role, content,
            timestamp, and an optional metadata JSON blob.
        user_preferences
            A simple key-value store per session (session_id PRIMARY KEY).

        Indexes
        -------
        idx_session on conversations(session_id) to speed up lookups
        by session.
        """
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                session_id TEXT PRIMARY KEY,
                preferences TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)
        """)
        self._conn.commit()

    def create_session(self) -> str:
        """Create a new conversation session.

        Returns
        -------
        str
            An 8-character hex identifier (first 8 chars of a UUID4).

        Side effects
        ------------
        Adds an empty list to the in-memory ``_sessions`` dict.
        """
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = []
        return session_id

    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Record a message in both short-term and long-term memory.

        Parameters
        ----------
        session_id : str
            The session identifier.
        role : str
            Message author (e.g. ``"user"``, ``"assistant"``, ``"system"``).
        content : str
            The message body.
        metadata : dict, optional
            Arbitrary key-value data to store alongside the message
            (e.g. token count, tool call IDs).

        Side effects
        ------------
        - Appends the message to the in-memory session list.
        - Inserts a row into the ``conversations`` SQLite table.
        - Trims the in-memory list to the last 50 messages to bound
          memory usage for long-running sessions.
        """
        # Auto-vivify the session list in case the session was created
        # externally or restored from the database.
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        })

        # Persist to SQLite immediately — this guarantees durability
        # even if the process crashes before the next commit cycle.
        self._conn.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, datetime.datetime.now().isoformat(),
             json.dumps(metadata or {})),
        )
        self._conn.commit()

        # --- Short-term memory cap ---
        # Keep only the last 50 messages per session in memory to
        # prevent unbounded growth.  The full history is always
        # available from SQLite.
        if len(self._sessions[session_id]) > 50:
            self._sessions[session_id] = self._sessions[session_id][-50:]

    def get_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """Retrieve the most recent messages for a session.

        Parameters
        ----------
        session_id : str
            The session identifier.
        limit : int, optional
            Maximum number of messages to return (default 10).

        Returns
        -------
        list[dict]
            A list of message dicts with keys ``role``, ``content``,
            and ``timestamp``, ordered oldest-first.

        Notes
        -----
        - If the session exists in the in-memory cache, the cache is
          consulted directly (O(1)).
        - On a cache miss, the last ``limit`` messages are fetched from
          SQLite and the cache is populated for future requests.
        """
        if session_id in self._sessions:
            return self._sessions[session_id][-limit:]

        # Cache miss: hydrate from the database.
        cursor = self._conn.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()

        # SQLite returns rows newest-first (ORDER BY id DESC), so we
        # reverse them to maintain chronological order.
        history = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in reversed(rows)
        ]
        self._sessions[session_id] = history
        return history

    def get_long_term_context(self, session_id: str) -> str:
        """Build a short summary of topics the user has discussed.

        Parameters
        ----------
        session_id : str
            The session identifier.

        Returns
        -------
        str
            A human-readable sentence listing detected topics, or an
            empty string if no user queries are on record.

        Notes
        -----
        Topic detection uses simple keyword matching against a fixed
        set of business-domains (fulfillment, returns, CSAT, KPI,
        inventory).  This is intentionally lightweight — no NLP model
        dependency.
        """
        cursor = self._conn.execute(
            "SELECT content FROM conversations WHERE session_id = ? AND role = 'user' ORDER BY id DESC LIMIT 20",
            (session_id,),
        )
        user_queries = [row[0] for row in cursor.fetchall()]

        if not user_queries:
            return ""

        topics = set()
        # Keyword groups mapped to topic labels.  A query is considered
        # to be "about" a topic if any of its associated keywords appear
        # (case-insensitively) in the user's question.
        topic_keywords = {
            "fulfillment": {"fulfillment", "delivery", "shipping", "warehouse"},
            "returns": {"return", "refund", "defective"},
            "csat": {"csat", "satisfaction", "survey", "customer experience"},
            "kpi": {"kpi", "metric", "performance", "dashboard"},
            "inventory": {"inventory", "stock", "sku", "count"},
        }

        for q in user_queries:
            q_lower = q.lower()
            for topic, keywords in topic_keywords.items():
                if any(kw in q_lower for kw in keywords):
                    topics.add(topic)

        if topics:
            return f"User has previously asked about: {', '.join(sorted(topics))}."
        return ""

    def save_preference(self, session_id: str, preferences: dict):
        """Persist user preferences for a session.

        Parameters
        ----------
        session_id : str
            The session identifier.
        preferences : dict
            Arbitrary preference data (e.g. ``{"theme": "dark",
            "timezone": "UTC"}``).

        Side effects
        ------------
        Uses ``INSERT OR REPLACE`` so any existing preferences for this
        session are overwritten.
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO user_preferences (session_id, preferences, updated_at) VALUES (?, ?, ?)",
            (session_id, json.dumps(preferences), datetime.datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_preferences(self, session_id: str) -> dict:
        """Retrieve stored preferences for a session.

        Parameters
        ----------
        session_id : str
            The session identifier.

        Returns
        -------
        dict
            The stored preferences, or an empty dict if none exist.
        """
        cursor = self._conn.execute(
            "SELECT preferences FROM user_preferences WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

    def reset_session(self, session_id: str):
        """Clear the in-memory history for a session.

        Parameters
        ----------
        session_id : str
            The session identifier.

        Side effects
        ------------
        Removes the session from the in-memory dict.  The long-term
        SQLite record is *not* deleted so that conversation data is
        preserved for audit / analytics.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self):
        """Wipe all conversation and preference data from both tiers.

        Side effects
        ------------
        - Empties the in-memory ``_sessions`` dict.
        - Deletes all rows from the ``conversations`` and
          ``user_preferences`` SQLite tables.

        Use with caution — this operation cannot be undone.
        """
        self._sessions.clear()
        self._conn.execute("DELETE FROM conversations")
        self._conn.execute("DELETE FROM user_preferences")
        self._conn.commit()

    def close(self):
        """Close the underlying SQLite connection.

        Should be called when the manager is no longer needed
        (e.g. on application shutdown) to release the database file.
        """
        self._conn.close()
