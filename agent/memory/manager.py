
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

        os.makedirs(MEMORY_DIR, exist_ok=True)
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # WAL mode allows concurrent reads without blocking on writes,
        # which is important for a multi-threaded agent server.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()
        # In-memory short-term store: session_id -> list of message dicts.
        self._sessions: dict[str, list] = {}

    def _init_db(self):

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

        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = []
        return session_id

    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):

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

        self._conn.execute(
            "INSERT OR REPLACE INTO user_preferences (session_id, preferences, updated_at) VALUES (?, ?, ?)",
            (session_id, json.dumps(preferences), datetime.datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_preferences(self, session_id: str) -> dict:

        cursor = self._conn.execute(
            "SELECT preferences FROM user_preferences WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

    def reset_session(self, session_id: str):

        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear_all(self):

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
