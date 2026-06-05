import os
import shutil
import subprocess

from tools.result import fail, ok

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
    "discord": [
        "discord",
        r"%LOCALAPPDATA%\Discord\Update.exe",
    ],
    "spotify": ["spotify"],
}


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
            os.startfile(path)  # noqa: S606 — desktop agent mở app trên Windows
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
        retryable=False,  # app không tồn tại → không retry
    )
