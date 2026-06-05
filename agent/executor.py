"""Executor — thực thi một tool call từ Agent Loop."""
from agent.logger import get_logger
from tools import TOOL_REGISTRY
from tools.result import fail

log = get_logger(__name__)


class Executor:
    """Chạy một action {"type": "tool", "tool": "...", "args": {...}}."""

    def run_one(self, action: dict) -> dict:
        """Thực thi 1 tool action, trả về result dict {success, retryable, message, data}."""
        tool_name = action.get("tool", "")
        args = action.get("args") or {}

        if not isinstance(args, dict):
            return fail(f"Args không hợp lệ cho tool '{tool_name}'.", retryable=False)

        if tool_name not in TOOL_REGISTRY:
            return fail(f"Tool '{tool_name}' không tồn tại.", retryable=False)

        try:
            log.info("[Executor] %s(%s)", tool_name, args)
            return TOOL_REGISTRY[tool_name](**args)
        except TypeError as exc:
            return fail(f"Lỗi tham số '{tool_name}': {exc}", retryable=False)
        except Exception as exc:
            return fail(f"Lỗi khi chạy '{tool_name}': {exc}", retryable=True)
