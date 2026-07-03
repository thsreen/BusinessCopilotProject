"""Logging utilities with PII scrubbing and structured JSON output."""
import json
import logging
import os
import re
import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")

# PII patterns to scrub
PII_PATTERNS = [
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]'),
    (r'\b\d{16}\b', '[CC REDACTED]'),
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
    (r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\b', '[NAME REDACTED]'),
]


def scrub_pii(text: str) -> str:
    """Remove PII from text for safe logging."""
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


class PiiSafeLogger:
    """Logger that automatically scrubs PII from all output."""

    def __init__(self, name: str):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # File handler with JSON formatting
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


_loggers = {}

def get_logger(name: str) -> PiiSafeLogger:
    if name not in _loggers:
        _loggers[name] = PiiSafeLogger(name)
    return _loggers[name]
