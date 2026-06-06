"""Tool browser_action — điều khiển tab trình duyệt bằng phím tắt (Windows)."""
from __future__ import annotations

import time

from tools.browser_utils import bring_browser_to_foreground, find_browser_hwnd
from tools.result import fail, ok

# action → pyautogui hotkey args
_ACTION_HOTKEYS: dict[str, tuple[str, ...]] = {
    "new_tab":   ("ctrl", "t"),
    "close_tab": ("ctrl", "w"),
    "reload":    ("f5",),
    "back":      ("alt", "left"),
    "forward":   ("alt", "right"),
}

_ACTION_LABELS: dict[str, str] = {
    "new_tab":   "mở tab mới",
    "close_tab": "đóng tab",
    "reload":    "tải lại trang",
    "back":      "quay lại",
    "forward":   "tiến tới",
}


def browser_action(action: str) -> dict:
    """Thực hiện hành động điều khiển trình duyệt.

    action: "new_tab" | "close_tab" | "reload" | "back" | "forward"
    """
    if action not in _ACTION_HOTKEYS:
        return fail(f"Hành động không hợp lệ: {action!r}. "
                    f"Chọn một trong: {', '.join(_ACTION_HOTKEYS)}")

    try:
        import pyautogui
    except ImportError as e:
        return fail(f"Thiếu thư viện: {e}. Cài bằng: pip install pyautogui")

    # 1. Tìm cửa sổ trình duyệt (dùng shared util)
    hwnd = find_browser_hwnd()

    # 2. Không có trình duyệt mở → mở trước rồi chờ
    if hwnd is None:
        from tools.browser import open_url
        result = open_url("about:blank")
        if not result["success"]:
            return fail("Không thể mở trình duyệt.")
        for _ in range(30):          # chờ tối đa 3 giây
            time.sleep(0.1)
            hwnd = find_browser_hwnd()
            if hwnd:
                break
        if hwnd is None:
            return fail("Không tìm thấy cửa sổ trình duyệt sau khi mở.")

    # 3. Đưa focus về trình duyệt (dùng shared util)
    bring_browser_to_foreground()

    # 4. Gửi phím tắt
    try:
        pyautogui.hotkey(*_ACTION_HOTKEYS[action])
    except Exception as e:
        return fail(f"Không thể gửi phím tắt: {e}")

    return ok(f"Đã {_ACTION_LABELS.get(action, action)}.", {"action": action})
