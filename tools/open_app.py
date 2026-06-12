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


def _resolve_lnk(lnk_path: str) -> str | None:
    """Giải mã file shortcut .lnk trên Windows để lấy đường dẫn file thực thi."""
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(lnk_path))
        target = shortcut.Targetpath
        if target and os.path.exists(target) and os.path.isfile(target):
            return target
    except Exception:
        pass
    return None


def _find_app_in_start_menu(app_name: str) -> str | None:
    """Quét thư mục Start Menu của Windows để tìm file shortcut trùng khớp."""
    search_paths = []
    
    program_data = os.environ.get("ProgramData")
    if program_data:
        search_paths.append(Path(program_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        
    app_data = os.environ.get("APPDATA")
    if app_data:
        search_paths.append(Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        
    app_name_lower = app_name.lower()
    
    for p in search_paths:
        if not p.exists():
            continue
        for root, dirs, files in os.walk(p):
            for file in files:
                if file.lower().endswith(".lnk"):
                    stem = Path(file).stem.lower()
                    # Khớp nếu tên app trùng hoặc nằm trong tên shortcut
                    if app_name_lower in stem or stem in app_name_lower:
                        resolved = _resolve_lnk(os.path.join(root, file))
                        if resolved:
                            return resolved
    return None


def _find_app_in_registry(app_name: str) -> str | None:
    """Quét Registry của Windows để tìm đường dẫn cài đặt của phần mềm."""
    import winreg
    
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
    ]
    
    app_name_lower = app_name.lower()
    
    for hkey, subkey in keys:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                info = winreg.QueryInfoKey(key)
                for i in range(info[0]):
                    try:
                        name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, name) as subkey_item:
                            try:
                                display_name, _ = winreg.QueryValueEx(subkey_item, "DisplayName")
                                if app_name_lower in display_name.lower() or display_name.lower() in app_name_lower:
                                    install_loc, _ = winreg.QueryValueEx(subkey_item, "InstallLocation")
                                    if install_loc and os.path.isdir(install_loc):
                                        # Tìm file .exe chính trong thư mục cài đặt
                                        for file in os.listdir(install_loc):
                                            if file.lower().endswith(".exe") and (app_name_lower in file.lower() or file.lower().startswith(app_name_lower)):
                                                exe_path = os.path.join(install_loc, file)
                                                if os.path.isfile(exe_path):
                                                    return exe_path
                            except (FileNotFoundError, OSError):
                                pass
                    except (FileNotFoundError, OSError):
                        pass
        except OSError:
            pass
    return None


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

    # Thử danh sách ứng dụng cấu hình tĩnh
    tried: list[str] = []
    if key in _APP_CANDIDATES:
        candidates = _APP_CANDIDATES[key]
        for candidate in candidates:
            resolved = _resolve_candidate(candidate)
            if not resolved:
                tried.append(candidate)
                continue
            if _launch(resolved):
                return ok(f"Đã mở '{app_name}' ({resolved}).", {"path": resolved})
            tried.append(resolved)
    else:
        # Nếu không có trong danh sách alias tĩnh, thử shutil.which trực tiếp
        resolved = _resolve_candidate(app_name.strip())
        if resolved and _launch(resolved):
            return ok(f"Đã mở '{app_name}' ({resolved}).", {"path": resolved})
        if resolved:
            tried.append(resolved)

    # Thử tìm kiếm động qua Start Menu
    dynamic_resolved = _find_app_in_start_menu(app_name)
    if dynamic_resolved and _launch(dynamic_resolved):
        return ok(f"Đã mở '{app_name}' thông qua Start Menu ({dynamic_resolved}).", {"path": dynamic_resolved})
    if dynamic_resolved:
        tried.append(f"StartMenu:{dynamic_resolved}")

    # Thử tìm kiếm động qua Registry
    reg_resolved = _find_app_in_registry(app_name)
    if reg_resolved and _launch(reg_resolved):
        return ok(f"Đã mở '{app_name}' thông qua Registry ({reg_resolved}).", {"path": reg_resolved})
    if reg_resolved:
        tried.append(f"Registry:{reg_resolved}")

    # Nếu hoàn toàn không mở được
    tried_str = ", ".join(tried) if tried else app_name
    return fail(
        f"Không mở được '{app_name}'. Đã thử: {tried_str}.",
        None,
        retryable=False,
    )
