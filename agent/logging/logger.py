
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

    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text

class PiiSafeLogger:

    def __init__(self, name: str):

        os.makedirs(LOG_DIR, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # File handler — one log file per logger name.
        log_file = os.path.join(LOG_DIR, f"{name.replace('.', '_')}.log")
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def _make_entry(self, level: str, msg: str, **kwargs) -> str:

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "logger": self.logger.name,
            "level": level,
            "message": scrub_pii(msg),
        }
        entry.update(kwargs)
        return json.dumps(entry)

    def info(self, msg: str, **kwargs):

        self.logger.info(self._make_entry("INFO", msg, **kwargs))

    def warning(self, msg: str, **kwargs):

        self.logger.warning(self._make_entry("WARNING", msg, **kwargs))

    def error(self, msg: str, **kwargs):

        self.logger.error(self._make_entry("ERROR", msg, **kwargs))

    def debug(self, msg: str, **kwargs):

        self.logger.debug(self._make_entry("DEBUG", msg, **kwargs))

# ── Singleton registry ────────────────────────────────────────────────────
# Module-level cache so that repeated calls to get_logger("agent") return
# the same PiiSafeLogger instance.
_loggers = {}

def get_logger(name: str) -> PiiSafeLogger:

    if name not in _loggers:
        _loggers[name] = PiiSafeLogger(name)
    return _loggers[name]
