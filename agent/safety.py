"""Safety checker — đánh giá rủi ro trước khi thực thi tool.

Không dùng LLM: chỉ static rules + regex, O(1) per check.
4 mức độ rủi ro:
  SAFE      — đọc-only, không cần xác nhận
  CAUTION   — side effect nhỏ, không cần xác nhận
  DANGEROUS — side effect đáng kể → yêu cầu xác nhận
  CRITICAL  — phá hoại / cấp hệ thống → yêu cầu xác nhận + cảnh báo mạnh
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar


# ── Risk levels ───────────────────────────────────────────────────────────────

class RiskLevel(IntEnum):
    SAFE      = 0   # đọc-only, không side effect
    CAUTION   = 1   # side effect nhỏ, có thể undo
    DANGEROUS = 2   # side effect đáng kể, khó undo → cần xác nhận
    CRITICAL  = 3   # phá hoại / cấp hệ thống → cần xác nhận mạnh


RISK_LABELS: dict[RiskLevel, str] = {
    RiskLevel.SAFE:      "An toàn",
    RiskLevel.CAUTION:   "Thận trọng",
    RiskLevel.DANGEROUS: "Nguy hiểm",
    RiskLevel.CRITICAL:  "Rất nguy hiểm",
}

RISK_ICONS: dict[RiskLevel, str] = {
    RiskLevel.SAFE:      "✅",
    RiskLevel.CAUTION:   "⚠️",
    RiskLevel.DANGEROUS: "🔴",
    RiskLevel.CRITICAL:  "🚨",
}


# ── Assessment result ─────────────────────────────────────────────────────────

@dataclass
class RiskAssessment:
    level:  RiskLevel
    tool:   str
    args:   dict
    reason: str   # lý do ngắn gọn hiển thị cho người dùng

    @property
    def label(self) -> str:
        return RISK_LABELS[self.level]

    @property
    def icon(self) -> str:
        return RISK_ICONS[self.level]

    @property
    def display(self) -> str:
        """tool_name("key_arg") — hiển thị ngắn gọn trong confirm dialog."""
        _KEY: dict[str, str] = {
            "kill_process":  "name_or_pid",
            "write_file":    "path",
            "run_command":   "command",
            "open_app":      "app_name",
            "open_url":      "url",
            "search_web":    "query",
            "set_clipboard": "text",
            "browser_action":"action",
        }
        key = _KEY.get(self.tool)
        if key and key in self.args:
            val = str(self.args[key])
            short = val[:60] + "…" if len(val) > 60 else val
            return f'{self.tool}("{short}")'
        return f"{self.tool}()"


# ── Regex patterns ────────────────────────────────────────────────────────────

# Tiến trình hệ thống quan trọng — dừng có thể crash Windows
_SYSTEM_PROC_RE = re.compile(
    r"\b(winlogon|lsass|csrss|smss|wininit|services|dwm|system|ntoskrnl)\b",
    re.IGNORECASE,
)

# Đường dẫn hệ thống Windows — không được ghi vào
_SYSTEM_PATH_RE = re.compile(
    r"^[A-Za-z]:\\(windows|system32|syswow64"
    r"|programdata\\microsoft|program files\\windows)",
    re.IGNORECASE,
)

# Lệnh cực kỳ nguy hiểm → CRITICAL
_CRITICAL_CMD_RE = re.compile(
    r"\b("
    r"format\s+\w:"
    r"|shutdown(\s+/[rfsh]|\s*$)"
    r"|rd\s+/[sq]|rmdir\s+/[sq]"
    r"|del\s+/[fsq]|erase\s+/[fsq]"
    r"|net\s+(user|localgroup|accounts)\b"
    r"|reg\s+(delete|add|import|export)\b"
    r"|bcdedit\b|diskpart\b"
    r"|cipher\s+/[wd]"
    r"|takeown\b|icacls\b"
    r"|powershell\s+(-e\s|-enc\s|-encodedcommand\s)"
    r")\b",
    re.IGNORECASE,
)

# Lệnh đọc-only → SAFE (không cần xác nhận)
_SAFE_CMD_RE = re.compile(
    r"^\s*("
    r"dir(\s|$)|ls(\s|$)"
    r"|echo\s|ping\s"
    r"|ipconfig(\s|$)|ifconfig(\s|$)"
    r"|hostname(\s|$)|ver(\s|$)|whoami(\s|$)"
    r"|date\s+/t|time\s+/t"
    r"|systeminfo(\s|$)|tasklist(\s|$)"
    r"|netstat(\s|$)|nslookup\s|tracert\s"
    r"|where\s+|which\s+|type\s+|cat\s+"
    r"|git\s+(status|log|diff|branch|remote\s+-v|show\b)(\s|$)"
    r"|pip\s+(list|show\s|freeze)(\s|$)"
    r"|npm\s+(list|--version)(\s|$)"
    r"|python(\s+--version|\s+-V|\s*$)"
    r"|node(\s+--version|\s+-v|\s*$)"
    r"|java\s+-version"
    r")",
    re.IGNORECASE,
)


# ── SafetyChecker ─────────────────────────────────────────────────────────────

class SafetyChecker:
    """Đánh giá rủi ro của một tool call — không dùng LLM, O(1) per check."""

    # Ngưỡng để yêu cầu xác nhận từ người dùng
    CONFIRM_THRESHOLD: ClassVar[RiskLevel] = RiskLevel.DANGEROUS

    # Tool luôn SAFE (đọc-only, không side effect)
    _ALWAYS_SAFE: ClassVar[frozenset[str]] = frozenset({
        "get_system_info",
        "get_running_processes",
        "get_active_window",
        "get_clipboard",
        "take_screenshot",
        "send_notification",
        "search_file",
        "read_file",
        "search_web",
        "open_url",
    })

    # Tool CAUTION (side effect nhỏ, có thể undo)
    _ALWAYS_CAUTION: ClassVar[frozenset[str]] = frozenset({
        "open_app",
        "set_clipboard",
        "browser_action",
    })

    @classmethod
    def assess(cls, tool_name: str, args: dict) -> RiskAssessment:
        """Trả về RiskAssessment cho (tool_name, args) — không raise exception."""
        args = args or {}

        if tool_name in cls._ALWAYS_SAFE:
            return RiskAssessment(
                RiskLevel.SAFE, tool_name, args,
                "Tool chỉ đọc thông tin, không thay đổi hệ thống.",
            )

        if tool_name in cls._ALWAYS_CAUTION:
            return RiskAssessment(
                RiskLevel.CAUTION, tool_name, args,
                "Side effect nhỏ, có thể hoàn tác.",
            )

        if tool_name == "kill_process":
            return cls._kill_process(args)
        if tool_name == "write_file":
            return cls._write_file(args)
        if tool_name == "run_command":
            return cls._run_command(args)

        # Tool không xác định → DANGEROUS (fail-safe: xác nhận trước)
        return RiskAssessment(
            RiskLevel.DANGEROUS, tool_name, args,
            f"Tool không xác định: '{tool_name}'.",
        )

    @classmethod
    def needs_confirmation(cls, a: RiskAssessment) -> bool:
        """True nếu mức rủi ro >= DANGEROUS."""
        return a.level >= cls.CONFIRM_THRESHOLD

    # ── Per-tool assessment ──────────────────────────────────────────────────

    @classmethod
    def _kill_process(cls, args: dict) -> RiskAssessment:
        target = str(args.get("name_or_pid", ""))
        if _SYSTEM_PROC_RE.search(target):
            return RiskAssessment(
                RiskLevel.CRITICAL, "kill_process", args,
                f"Tiến trình hệ thống: '{target}'. Dừng có thể làm crash Windows.",
            )
        return RiskAssessment(
            RiskLevel.DANGEROUS, "kill_process", args,
            f"Sẽ kết thúc tiến trình: '{target}'.",
        )

    @classmethod
    def _write_file(cls, args: dict) -> RiskAssessment:
        path   = str(args.get("path", ""))
        append = bool(args.get("append", False))

        if _SYSTEM_PATH_RE.match(path):
            return RiskAssessment(
                RiskLevel.CRITICAL, "write_file", args,
                f"Ghi vào đường dẫn hệ thống: '{path}'.",
            )
        if not append:
            return RiskAssessment(
                RiskLevel.DANGEROUS, "write_file", args,
                f"Sẽ ghi đè (overwrite) file: '{path}'.",
            )
        # append=True → chỉ thêm vào cuối, ít rủi ro hơn
        return RiskAssessment(
            RiskLevel.CAUTION, "write_file", args,
            f"Thêm nội dung vào cuối file: '{path}'.",
        )

    @classmethod
    def _run_command(cls, args: dict) -> RiskAssessment:
        cmd = str(args.get("command", ""))

        if _CRITICAL_CMD_RE.search(cmd):
            return RiskAssessment(
                RiskLevel.CRITICAL, "run_command", args,
                f"Lệnh có thể gây hại nghiêm trọng cho hệ thống: '{cmd[:80]}'.",
            )
        if _SAFE_CMD_RE.match(cmd):
            return RiskAssessment(
                RiskLevel.SAFE, "run_command", args,
                "Lệnh đọc-only, không thay đổi hệ thống.",
            )
        return RiskAssessment(
            RiskLevel.DANGEROUS, "run_command", args,
            f"Lệnh shell có thể thay đổi hệ thống: '{cmd[:80]}'.",
        )