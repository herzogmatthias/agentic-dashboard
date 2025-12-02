import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional


_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extras if present
        for key in ("run_id", "session_id", "phase", "agent"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    fmt = os.getenv("LOG_FORMAT", "plain").lower()  # plain|json

    handler = logging.StreamHandler(stream=sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a configured logger. Set via env:
      - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
      - LOG_FORMAT=plain|json
    """
    _ensure_configured()
    return logging.getLogger(name or __name__)
