"""browser_utils — shared browser state logic.

Dùng chung bởi open_app, browser_control, open_url.
Tập trung 3 việc:
  - Phát hiện trình duyệt đang chạy
  - Tìm hwnd cửa sổ trình duyệt
  - Đưa trình duyệt lên foreground

Import lazily để không crash khi thiếu thư viện ở startup.
"""
from __future__ import annotations

import time

SUPPORTED_BROWSERS: set[str] = {"chrome.exe", "msedge.exe", "firefox.exe"}
BROWSER_DISPLAY: dict[str, str] = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
}


def get_running_browser() -> str | None:
    """Trả về tên process của trình duyệt đang chạy, hoặc None."""
    try:
        import psutil

        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info["name"] or "").lower()
                if name in SUPPORTED_BROWSERS:
                    return name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass
    return None


def find_browser_hwnd() -> int | None:
    """Tìm hwnd của cửa sổ trình duyệt.

    Ưu tiên foreground window nếu đang là trình duyệt,
    fallback sang cửa sổ trình duyệt đầu tiên tìm được.
    """
    try:
        import psutil
        import win32gui

        found: list[int] = []

        def _cb(hwnd: int, _: object) -> None:
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


def bring_browser_to_foreground() -> bool:
    """Đưa cửa sổ trình duyệt lên foreground. Trả về True nếu thành công."""
    try:
        import win32gui

        hwnd = find_browser_hwnd()
        if hwnd is None:
            return False
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)
        return True
    except Exception:
        return False
