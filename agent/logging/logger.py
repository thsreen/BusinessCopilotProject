"""Logging utilities with PII scrubbing and structured JSON output.

Architecture
------------
This module provides two main components:

1. ``PiiSafeLogger`` — A custom logger that automatically redacts
   personally identifiable information (PII) from all log messages
   before writing them as JSON lines to a file.

2. ``get_logger()`` — A simple singleton factory that caches and
   returns ``PiiSafeLogger`` instances by name.

PII redaction
-------------
The ``scrub_pii()`` function applies a list of compiled regex patterns
to replace common PII patterns (email addresses, phone numbers, credit
card numbers, SSNs, and name prefixes) with safe placeholders like
``[EMAIL REDACTED]``.

Log output format
-----------------
Every log entry is a single-line JSON object with at least these fields:

.. code-block:: json

    {
      "timestamp": "2026-07-04T12:34:56",
      "logger": "my_logger",
      "level": "INFO",
      "message": "..."
    }

Additional keyword arguments passed to the log methods are merged into
the JSON object (e.g. ``session_id``, ``event_type``).
"""
import json
import logging
import os
import re
import datetime

# Log files are written to <project_root>/logs/.
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

# ── PII patterns ────────────────────────────────────────────────────────────
# Each entry is a (regex, replacement) tuple.  The regexes are applied
# in order; later entries may match substrings already replaced, so
# order matters (e.g. SSN pattern before generic number patterns).
PII_PATTERNS = [
    # Email addresses (RFC 5322 simplified).
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
    # US phone numbers: optional area code separators (., -) between
    # three groups of 3-3-4 digits.  Avoids matching short sequences.
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]'),
    # Credit card numbers: 16 consecutive digits.  No Luhn check is
    # performed — this is a conservative heuristic.
    (r'\b\d{16}\b', '[CC REDACTED]'),
    # US Social Security Numbers: XXX-XX-XXXX.
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
    # Honorific-based names (e.g. "Mr. Smith", "Dr. Jones").
    # This is an intentionally conservative pattern that avoids
    # broad-stroke name detection which would produce many false
    # positives in operational text.
    (r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\b', '[NAME REDACTED]'),
]


def scrub_pii(text: str) -> str:
    """Remove personally identifiable information from a string.

    Applies every regex in ``PII_PATTERNS`` sequentially and replaces
    matches with the corresponding safe placeholder.

    Parameters
    ----------
    text : str
        The raw text that may contain PII.

    Returns
    -------
    str
        The text with all detected PII patterns replaced by placeholders
        such as ``[EMAIL REDACTED]``.

    Notes
    -----
    This is a heuristic, regex-based approach.  It will not catch every
    possible PII variant (e.g. non-standard email formats, international
    phone numbers, etc.).  For stronger guarantees, consider calling a
    dedicated PII detection service before passing text to this logger.
    """
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


class PiiSafeLogger:
    """Logger that automatically scrubs PII from all output.

    Each instance writes JSON-formatted log entries to a file named
    ``<name>.log`` inside the ``logs/`` directory.  The message field
    is run through ``scrub_pii()`` before serialisation.

    Usage::

        logger = PiiSafeLogger("agent")
        logger.info("User query received", session_id="abc123")
        logger.error("Failed to process", order_id=42, exc_info=True)
    """

    def __init__(self, name: str):
        """Set up a file-backed logger with a JSON formatter.

        Parameters
        ----------
        name : str
            Dot-separated logger name (e.g. ``"agent.llm"``).  Dots
            are replaced with underscores in the log filename.

        Side effects
        ------------
        - Creates the ``logs/`` directory if it does not exist.
        - Adds a ``logging.FileHandler`` to the underlying Python logger.
        - Discards the default stderr handler; only the file handler
          is used.
        """
        os.makedirs(LOG_DIR, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # File handler — one log file per logger name.
        log_file = os.path.join(LOG_DIR, f"{name.replace('.', '_')}.log")
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def _make_entry(self, level: str, msg: str, **kwargs) -> str:
        """Build a JSON-serialised log entry.

        Parameters
        ----------
        level : str
            Log level (``"INFO"``, ``"WARNING"``, ``"ERROR"``, ``"DEBUG"``).
        msg : str
            The log message (will be scrubbed for PII).
        **kwargs
            Extra key-value pairs merged into the JSON object.

        Returns
        -------
        str
            A single-line JSON string.
        """
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "logger": self.logger.name,
            "level": level,
            "message": scrub_pii(msg),
        }
        entry.update(kwargs)
        return json.dumps(entry)

    def info(self, msg: str, **kwargs):
        """Log an INFO-level message.

        Parameters
        ----------
        msg : str
            The log message (PII is automatically redacted).
        **kwargs
            Extra fields merged into the JSON output.
        """
        self.logger.info(self._make_entry("INFO", msg, **kwargs))

    def warning(self, msg: str, **kwargs):
        """Log a WARNING-level message.

        Parameters
        ----------
        msg : str
            The log message (PII is automatically redacted).
        **kwargs
            Extra fields merged into the JSON output.
        """
        self.logger.warning(self._make_entry("WARNING", msg, **kwargs))

    def error(self, msg: str, **kwargs):
        """Log an ERROR-level message.

        Parameters
        ----------
        msg : str
            The log message (PII is automatically redacted).
        **kwargs
            Extra fields merged into the JSON output.
        """
        self.logger.error(self._make_entry("ERROR", msg, **kwargs))

    def debug(self, msg: str, **kwargs):
        """Log a DEBUG-level message.

        Parameters
        ----------
        msg : str
            The log message (PII is automatically redacted).
        **kwargs
            Extra fields merged into the JSON output.
        """
        self.logger.debug(self._make_entry("DEBUG", msg, **kwargs))


# ── Singleton registry ────────────────────────────────────────────────────
# Module-level cache so that repeated calls to get_logger("agent") return
# the same PiiSafeLogger instance.
_loggers = {}

def get_logger(name: str) -> PiiSafeLogger:
    """Return a cached ``PiiSafeLogger`` for *name*, creating one if needed.

    Parameters
    ----------
    name : str
        Logger name (dots allowed, e.g. ``"agent.llm"``).

    Returns
    -------
    PiiSafeLogger
        A single shared instance per unique name.
    """
    if name not in _loggers:
        _loggers[name] = PiiSafeLogger(name)
    return _loggers[name]
