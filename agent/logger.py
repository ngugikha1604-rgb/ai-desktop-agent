"""Centralized logging — console có màu + timestamp, file plain text."""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "agent.log"

_SENSITIVE_RE = re.compile(
    r"(password|token|api_key|secret|credentials)\s*[=:]\s*\S+",
    re.IGNORECASE,
)

# ── ANSI colors ───────────────────────────────────────────────────────────────

def _supports_color() -> bool:
    """True nếu terminal hỗ trợ ANSI color. Dùng ctypes trên Windows thay vì đoán env vars."""
    if os.environ.get("NO_COLOR"):
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
        except Exception:
            pass
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_USE_COLOR = _supports_color()

_C: dict[str, str] = (
    {
        "gray":    "\033[90m",
        "cyan":    "\033[36m",
        "green":   "\033[32m",
        "yellow":  "\033[33m",
        "red":     "\033[31m",
        "magenta": "\033[35m",
        "bold":    "\033[1m",
        "dim":     "\033[2m",
        "reset":   "\033[0m",
    }
    if _USE_COLOR
    else {k: "" for k in ("gray","cyan","green","yellow","red","magenta","bold","dim","reset")}
)

# Level → color
_LEVEL_COLOR: dict[str, str] = {
    "DEBUG":    _C["gray"],
    "INFO":     _C["cyan"],
    "WARNING":  _C["yellow"],
    "ERROR":    _C["red"],
    "CRITICAL": _C["magenta"],
}


# ── Formatters ────────────────────────────────────────────────────────────────

class _ColorFormatter(logging.Formatter):
    """Console formatter: `HH:MM:SS  <colored message>`

    Không in level name — màu sắc đã đủ để phân biệt:
      gray  = DEBUG  (chi tiết nội bộ, ít quan trọng)
      cyan  = INFO   (flow chính)
      yellow = WARNING
      red    = ERROR
    """
    def format(self, record: logging.LogRecord) -> str:
        ts   = self.formatTime(record, "%H:%M:%S")
        msg  = record.getMessage()
        col  = _LEVEL_COLOR.get(record.levelname, "")
        dim  = _C["dim"]
        rst  = _C["reset"]
        return f"{dim}{ts}{rst}  {col}{msg}{rst}"


class _SensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SENSITIVE_RE.sub(r"\1=[REDACTED]", str(record.msg))
        return True


# ── Factory ───────────────────────────────────────────────────────────────────

def get_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # đã configure, bỏ qua

    logger.setLevel(logging.DEBUG)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # File handler — WARNING+ (plain text, dễ grep)
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    fh.addFilter(_SensitiveFilter())
    logger.addHandler(fh)

    # Console handler — DEBUG+ với màu
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_ColorFormatter())
    logger.addHandler(ch)

    return logger
