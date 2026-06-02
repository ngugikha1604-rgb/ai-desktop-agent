from tools.active_window import get_active_window
from tools.clipboard import get_clipboard, set_clipboard
from tools.kill_process import kill_process
from tools.notification import send_notification
from tools.open_app import open_app
from tools.process_info import get_running_processes
from tools.read_file import read_file
from tools.run_command import run_command
from tools.screenshot import take_screenshot
from tools.search_file import search_file
from tools.system_info import get_system_info
from tools.write_file import write_file

TOOL_REGISTRY: dict[str, callable] = {
    # App control
    "open_app": open_app,
    "kill_process": kill_process,
    # File operations
    "search_file": search_file,
    "read_file": read_file,
    "write_file": write_file,
    # System info
    "get_system_info": get_system_info,
    "get_running_processes": get_running_processes,
    "get_active_window": get_active_window,
    # Shell
    "run_command": run_command,
    # Clipboard
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
    # Screen & notification
    "take_screenshot": take_screenshot,
    "send_notification": send_notification,
}

__all__ = ["TOOL_REGISTRY"]
