"""Tool browser_action — điều khiển tab trình duyệt bằng phím tắt (Windows)."""
from __future__ import annotations

import time

from tools.result import fail, ok

SUPPORTED_BROWSERS = ["chrome.exe", "msedge.exe", "firefox.exe"]

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
        return fail(f"Hành động không hợp lệ: {action}", None)

    try:
        import psutil
        import pyautogui
        import win32gui
    except ImportError as e:
        return fail(
            f"Thiếu thư viện: {e}. Cài bằng: pip install psutil pyautogui pywin32",
            None,
        )

    # 1. Tìm cửa sổ trình duyệt
    hwnd = _find_browser_hwnd()

    # 2. Không có trình duyệt mở → mở trước
    if hwnd is None:
        from tools.browser import open_url
        result = open_url("about:blank")
        if not result["success"]:
            return fail("Không thể mở trình duyệt.")
        for _ in range(30):          # chờ tối đa 3 giây
            time.sleep(0.1)
            hwnd = _find_browser_hwnd()
            if hwnd:
                break
        if hwnd is None:
            return fail("Không tìm thấy cửa sổ trình duyệt sau khi mở.")

    # 3. Đưa focus về trình duyệt
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)
    except Exception:
        pass

    # 4. Gửi phím tắt
    try:
        pyautogui.hotkey(*_ACTION_HOTKEYS[action])
    except Exception as e:
        return fail(f"Không thể gửi phím tắt: {e}", None)

    return ok(f"Đã {_ACTION_LABELS.get(action, action)}.", {"action": action})


def _find_browser_hwnd() -> int | None:
    """Tìm hwnd của cửa sổ trình duyệt được hỗ trợ.
    Ưu tiên cửa sổ foreground nếu đang là trình duyệt.
    """
    try:
        import psutil
        import win32gui

        found: list[int] = []

        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            try:
                _, pid = win32gui.GetWindowThreadProcessId(hwnd)
                if psutil.Process(pid).name().lower() in SUPPORTED_BROWSERS:
                    found.append(hwnd)
            except Exception:
                pass

        win32gui.EnumWindows(_cb, None)
        fg = win32gui.GetForegroundWindow()
        if fg in found:
            return fg
        return found[0] if found else None
    except Exception:
        return None
