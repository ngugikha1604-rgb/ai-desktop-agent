"""Centralized logging — ghi vào logs/agent.log, lọc thông tin nhạy cảm."""
import logging
import re
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "agent.log"

_SENSITIVE_RE = re.compile(
    r"(password|token|api_key|secret|credentials)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


class _SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SENSITIVE_RE.sub(r"\1=[REDACTED]", str(record.msg))
        return True


def get_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # File handler — WARNING+
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    fh.addFilter(_SensitiveFilter())
    logger.addHandler(fh)

    # Console handler — DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger
