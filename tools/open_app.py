import glob
import os
import shutil
import subprocess

from tools.browser_utils import BROWSER_DISPLAY, bring_browser_to_foreground, get_running_browser
from tools.result import fail, ok

# Tên key nào là trình duyệt — xử lý đặc biệt khi đã chạy
_BROWSER_KEYS: set[str] = {"chrome", "edge", "firefox"}

# alias → danh sách lệnh/đường dẫn thử lần lượt
_APP_CANDIDATES: dict[str, list[str]] = {
    "code": [
        "code",
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    ],
    "vscode": [
        "code",
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    ],
    "vs code": [
        "code",
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
    ],
    "chrome": [
        "chrome",
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        "msedge",
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
    "firefox": [
        "firefox",
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
    ],
    "notepad": ["notepad"],
    "explorer": ["explorer"],
    "cmd": ["cmd"],
    "powershell": ["powershell"],
    "terminal": ["wt", "wt.exe"],
    "spotify": ["spotify"],
}


def _resolve_discord() -> str | None:
    """Tìm Discord.exe qua glob vì version folder thay đổi sau mỗi update.

    Ví dụ: %LOCALAPPDATA%\\Discord\\app-1.0.9170\\Discord.exe
    Trả về path của version mới nhất, hoặc None nếu không tìm thấy.
    """
    local = os.environ.get("LOCALAPPDATA", "")
    if not local:
        return None
    matches = sorted(
        glob.glob(os.path.join(local, "Discord", "app-*", "Discord.exe")),
        reverse=True,  # version mới nhất trước (sort theo tên desc)
    )
    return matches[0] if matches else None


def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path.strip()))


def _resolve_candidate(candidate: str) -> str | None:
    expanded = _expand(candidate)
    if os.path.isfile(expanded):
        return expanded

    found = shutil.which(candidate)
    if found:
        return found

    if os.name == "nt" and not candidate.lower().endswith(".exe"):
        found_exe = shutil.which(f"{candidate}.exe")
        if found_exe:
            return found_exe

    return None


def _launch(path: str) -> bool:
    try:
        if path.lower().endswith((".cmd", ".bat")):
            subprocess.Popen([path], shell=False, close_fds=True)
        else:
            os.startfile(path)  # noqa: S606
        return True
    except OSError:
        try:
            subprocess.Popen([path], shell=False, close_fds=True)
            return True
        except OSError:
            return False


def open_app(app_name: str) -> dict:
    key = (app_name or "").strip().lower()
    if not key:
        return fail("Tên ứng dụng trống.")

    # Trình duyệt đã chạy → đưa lên foreground, không mở instance mới
    if key in _BROWSER_KEYS:
        running = get_running_browser()
        if running:
            display = BROWSER_DISPLAY.get(running, key.capitalize())
            brought = bring_browser_to_foreground()
            msg = (
                f"{display} đã đang chạy — đã đưa lên foreground."
                if brought
                else f"{display} đã đang chạy."
            )
            return ok(msg, {"already_running": True, "browser": running})

    # Discord: resolve path đúng qua glob thay vì hardcode Update.exe
    if key == "discord":
        discord_path = _resolve_discord()
        if discord_path:
            try:
                subprocess.Popen([discord_path], close_fds=True)
                return ok("Đã mở Discord.", {"path": discord_path})
            except Exception as e:
                return fail(f"Không thể mở Discord: {e}")
        # Fallback: thử shutil.which
        found = shutil.which("Discord") or shutil.which("discord")
        if found:
            try:
                subprocess.Popen([found], close_fds=True)
                return ok("Đã mở Discord.", {"path": found})
            except Exception as e:
                return fail(f"Không thể mở Discord: {e}")
        return fail("Không tìm thấy Discord. Hãy chắc chắn Discord đã được cài đặt.")

    candidates = _APP_CANDIDATES.get(key, [app_name.strip()])
    tried: list[str] = []

    for candidate in candidates:
        resolved = _resolve_candidate(candidate)
        if not resolved:
            tried.append(candidate)
            continue
        if _launch(resolved):
            return ok(f"Đã mở '{app_name}' ({resolved}).", {"path": resolved})
        tried.append(resolved)

    return fail(
        f"Không mở được '{app_name}'. Đã thử: {', '.join(tried) or app_name}.",
        None,
        retryable=False,
    )
