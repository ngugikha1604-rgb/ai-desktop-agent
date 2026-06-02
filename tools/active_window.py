import win32gui
import win32process
import psutil

from tools.result import fail, ok


def get_active_window() -> dict:
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ok("Không có cửa sổ nào đang active.", None)

        title = win32gui.GetWindowText(hwnd).strip()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        process_name: str | None = None
        try:
            process_name = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        data = {"hwnd": hwnd, "title": title, "pid": pid, "process": process_name}

        parts = []
        if process_name:
            parts.append(process_name)
        if title:
            parts.append(f'"{title}"')
        message = "Cửa sổ hiện tại: " + " — ".join(parts) if parts else "Không lấy được thông tin cửa sổ."

        return ok(message, data)
    except Exception as exc:
        return fail(f"Không lấy được cửa sổ active: {exc}")
