"""Executor — thực thi một tool call từ Agent Loop."""
from __future__ import annotations

from typing import Callable

from agent.logger import get_logger
from agent.safety import RiskAssessment, SafetyChecker
from tools import TOOL_REGISTRY
from tools.result import fail

log = get_logger(__name__)


class Executor:
    """Chạy một action {"type": "tool", "tool": "...", "args": {...}}."""

    def __init__(self) -> None:
        # Callback: fn(RiskAssessment) -> bool
        # Set bởi DesktopApp (GUI); None → CLI fallback dùng input()
        self.on_confirm: Callable[[RiskAssessment], bool] | None = None

    def run_one(self, action: dict) -> dict:
        """Thực thi 1 tool action, trả về result dict {success, retryable, message, data}."""
        tool_name = action.get("tool", "")
        args = action.get("args") or {}

        if not isinstance(args, dict):
            return fail(f"Args không hợp lệ cho tool '{tool_name}'.", retryable=False)

        if tool_name not in TOOL_REGISTRY:
            return fail(f"Tool '{tool_name}' không tồn tại.", retryable=False)

        # ── Safety gate ────────────────────────────────────────────────────
        assessment = SafetyChecker.assess(tool_name, args)
        if SafetyChecker.needs_confirmation(assessment):
            approved = self._request_confirmation(assessment)
            if not approved:
                log.info("[Safety] Từ chối: %s", assessment.display)
                return fail(
                    f"Người dùng từ chối: {assessment.display}",
                    retryable=False,
                )
            log.info("[Safety] Chấp thuận: %s", assessment.display)

        try:
            log.debug("[Executor] %s(%s)", tool_name, args)
            return TOOL_REGISTRY[tool_name](**args)
        except TypeError as exc:
            return fail(f"Lỗi tham số '{tool_name}': {exc}", retryable=False)
        except Exception as exc:
            return fail(f"Lỗi khi chạy '{tool_name}': {exc}", retryable=True)

    # ── Confirmation ──────────────────────────────────────────────────────────

    def _request_confirmation(self, assessment: RiskAssessment) -> bool:
        """Yêu cầu xác nhận. Blocking cho đến khi có câu trả lời hoặc timeout."""
        if self.on_confirm is not None:
            # GUI mode — delegate sang DesktopApp (sẽ block qua threading.Event)
            return self.on_confirm(assessment)

        # CLI fallback — hỏi trực tiếp trong terminal
        log.warning(
            "[Safety] %s %s — %s",
            assessment.icon, assessment.label, assessment.reason,
        )
        try:
            prompt = (
                f"\n{assessment.icon} [{assessment.label.upper()}] "
                f"{assessment.display}\n"
                f"   {assessment.reason}\n"
                f"Cho phép thực hiện? [y/N]: "
            )
            return input(prompt).strip().lower() == "y"
        except (EOFError, KeyboardInterrupt):
            return False