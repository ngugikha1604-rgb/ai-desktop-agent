"""Tool Registry — single source of truth cho tất cả tools.

Mỗi tool được khai báo một lần dưới dạng ToolSpec (description, when_to_use,
returns, args, examples). Registry tự sinh đoạn AVAILABLE TOOLS cho planner
prompt → không cần viết tay trong file .txt nữa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import json


# ── ToolSpec ──────────────────────────────────────────────────────────────────

@dataclass
class ToolSpec:
    """Metadata đầy đủ của một tool."""
    name: str
    fn: Callable
    description: str
    category: str
    when_to_use: str
    returns: str
    args: dict[str, str]           # arg_name → "type, required/optional — mô tả"
    preconditions: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    # example shape: {"user": "...", "call": {"tool": "...", "args": {...}}}


# ── Import tất cả tool functions ──────────────────────────────────────────────

from tools.active_window import get_active_window
from tools.browser import open_url, search_web
from tools.browser_control import browser_action
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
from tools.get_weather import get_weather
from tools.web_search import web_search
from tools.web_read import web_read
from tools.write_file import write_file


# ── Registry definitions ──────────────────────────────────────────────────────

_SPECS: list[ToolSpec] = [

    # ── App control ───────────────────────────────────────────────────────────

    ToolSpec(
        name="open_app",
        fn=open_app,
        category="app",
        description="Open an installed application by name or alias.",
        when_to_use="User wants to launch a program (Chrome, VS Code, Notepad, Spotify, Discord...).",
        returns="Confirmation message with resolved path.",
        args={
            "app_name": "string, required — Application name or alias (e.g. 'chrome', 'vscode', 'notepad').",
        },
        examples=[
            {"user": "mở chrome", "call": {"tool": "open_app", "args": {"app_name": "chrome"}}},
            {"user": "mở VS Code", "call": {"tool": "open_app", "args": {"app_name": "vscode"}}},
        ],
    ),

    ToolSpec(
        name="kill_process",
        fn=kill_process,
        category="app",
        description="Terminate a running process by name or PID.",
        when_to_use="User wants to close/kill/stop a running program.",
        returns="Confirmation with PID of terminated process.",
        args={
            "name_or_pid": "string, required — Process name (e.g. 'chrome.exe') or PID number.",
        },
        examples=[
            {"user": "tắt chrome", "call": {"tool": "kill_process", "args": {"name_or_pid": "chrome.exe"}}},
            {"user": "kill notepad", "call": {"tool": "kill_process", "args": {"name_or_pid": "notepad.exe"}}},
        ],
    ),

    # ── File ──────────────────────────────────────────────────────────────────

    ToolSpec(
        name="search_file",
        fn=search_file,
        category="filesystem",
        description="Search for files by filename keyword, starting from an optional root directory.",
        when_to_use=(
            "User wants to find/locate a file by name. "
            "Always use this BEFORE read_file when the full path is unknown."
        ),
        returns="List of matching file paths.",
        args={
            "keyword": "string, required — Filename keyword to search for.",
            "root":    "string, optional — Root directory to search in (default: C:\\Users\\).",
        },
        examples=[
            {"user": "tìm file README", "call": {"tool": "search_file", "args": {"keyword": "README"}}},
            {"user": "tìm report trong ổ C", "call": {"tool": "search_file", "args": {"keyword": "report", "root": "C:\\"}}},
        ],
    ),

    ToolSpec(
        name="read_file",
        fn=read_file,
        category="filesystem",
        description="Read and return the text content of a file given its full path.",
        when_to_use=(
            "User wants to see/read the content of a file and the full path is known. "
            "If path is unknown, use search_file first."
        ),
        returns="Full text content of the file.",
        args={
            "path": "string, required — Absolute path to the file (e.g. C:\\Users\\user\\notes.txt).",
        },
        preconditions=["search_file"],
        examples=[
            {"user": "đọc file C:\\project\\README.md", "call": {"tool": "read_file", "args": {"path": "C:\\project\\README.md"}}},
        ],
    ),

    ToolSpec(
        name="write_file",
        fn=write_file,
        category="filesystem",
        description="Write or append text content to a file at the given path.",
        when_to_use="User wants to create a new file, overwrite a file, or append text to an existing file.",
        returns="Confirmation that the file was written successfully.",
        args={
            "path":    "string, required — Absolute path to the file.",
            "content": "string, required — Text content to write.",
            "append":  "boolean, optional — If true, append to existing content instead of overwriting (default: false).",
        },
        examples=[
            {"user": "ghi 'Hello' vào C:\\notes.txt", "call": {"tool": "write_file", "args": {"path": "C:\\notes.txt", "content": "Hello"}}},
        ],
    ),

    # ── System ────────────────────────────────────────────────────────────────

    ToolSpec(
        name="get_system_info",
        fn=get_system_info,
        category="system",
        description="Get current system resource usage: RAM, CPU, and disk space.",
        when_to_use=(
            "User asks about RAM, memory, CPU usage, disk space, or general system performance. "
            "Do NOT use get_running_processes for this."
        ),
        returns="RAM used/total, CPU %, disk free/total for each drive.",
        args={},
        examples=[
            {"user": "RAM còn bao nhiêu?", "call": {"tool": "get_system_info", "args": {}}},
            {"user": "CPU đang chạy bao nhiêu?", "call": {"tool": "get_system_info", "args": {}}},
            {"user": "ổ C còn trống không?", "call": {"tool": "get_system_info", "args": {}}},
        ],
    ),

    ToolSpec(
        name="get_running_processes",
        fn=get_running_processes,
        category="system",
        description="List currently running processes, optionally filtered by name.",
        when_to_use=(
            "User wants to see which applications or processes are running. "
            "Different from get_system_info which shows resource usage numbers."
        ),
        returns="List of processes with PID, name, CPU%, and memory usage.",
        args={
            "name_filter": "string, optional — Filter by process name (e.g. 'chrome').",
            "limit":       "integer, optional — Max number of processes to return (default: 40).",
        },
        examples=[
            {"user": "ứng dụng nào đang chạy?", "call": {"tool": "get_running_processes", "args": {}}},
            {"user": "chrome đang dùng bao nhiêu RAM?", "call": {"tool": "get_running_processes", "args": {"name_filter": "chrome"}}},
        ],
    ),

    ToolSpec(
        name="get_active_window",
        fn=get_active_window,
        category="system",
        description="Get information about the currently focused window.",
        when_to_use="User asks what window/application is currently active or in focus.",
        returns="Window title, process name, and PID of the focused window.",
        args={},
        examples=[
            {"user": "cửa sổ nào đang active?", "call": {"tool": "get_active_window", "args": {}}},
            {"user": "ứng dụng nào đang được focus?", "call": {"tool": "get_active_window", "args": {}}},
        ],
    ),

    # ── Shell ─────────────────────────────────────────────────────────────────

    ToolSpec(
        name="run_command",
        fn=run_command,
        category="shell",
        description="Execute a shell command and return its output.",
        when_to_use="User wants to run a terminal/shell command (dir, ipconfig, ping, git, etc.).",
        returns="Stdout/stderr output of the command.",
        args={
            "command": "string, required — Shell command to execute.",
            "cwd":     "string, optional — Working directory for the command.",
        },
        examples=[
            {"user": "chạy lệnh dir", "call": {"tool": "run_command", "args": {"command": "dir"}}},
            {"user": "ping google.com", "call": {"tool": "run_command", "args": {"command": "ping google.com"}}},
        ],
    ),

    # ── Clipboard ─────────────────────────────────────────────────────────────

    ToolSpec(
        name="get_clipboard",
        fn=get_clipboard,
        category="clipboard",
        description="Read the current text content from the clipboard.",
        when_to_use="User asks what is in the clipboard, or wants to see copied text.",
        returns="Text currently in the clipboard.",
        args={},
        examples=[
            {"user": "clipboard có gì?", "call": {"tool": "get_clipboard", "args": {}}},
        ],
    ),

    ToolSpec(
        name="set_clipboard",
        fn=set_clipboard,
        category="clipboard",
        description="Write text to the clipboard.",
        when_to_use="User wants to copy/put specific text into the clipboard.",
        returns="Confirmation that text was copied to clipboard.",
        args={
            "text": "string, required — Text to copy to clipboard.",
        },
        examples=[
            {"user": "copy 'Hello World' vào clipboard", "call": {"tool": "set_clipboard", "args": {"text": "Hello World"}}},
        ],
    ),

    # ── Screen & notification ─────────────────────────────────────────────────

    ToolSpec(
        name="take_screenshot",
        fn=take_screenshot,
        category="screen",
        description="Take a screenshot of the current screen.",
        when_to_use="User wants to capture/screenshot the screen.",
        returns="Confirmation with saved path of the screenshot file.",
        args={
            "save_path": "string, optional — Absolute path to save the image (default: auto-generated in Desktop).",
        },
        examples=[
            {"user": "chụp màn hình", "call": {"tool": "take_screenshot", "args": {}}},
        ],
    ),

    ToolSpec(
        name="send_notification",
        fn=send_notification,
        category="notification",
        description="Send a Windows desktop notification (toast message).",
        when_to_use="User wants to send or show a Windows notification/alert.",
        returns="Confirmation that notification was sent.",
        args={
            "title":   "string, required — Notification title.",
            "message": "string, required — Notification body text.",
        },
        examples=[
            {"user": "gửi thông báo 'Xong rồi'", "call": {"tool": "send_notification", "args": {"title": "Agent", "message": "Xong rồi"}}},
        ],
    ),

    # ── Browser ───────────────────────────────────────────────────────────────

    ToolSpec(
        name="open_url",
        fn=open_url,
        category="browser",
        description="Open a URL in the default browser. Automatically launches the browser if not running.",
        when_to_use=(
            "User wants to visit a website or URL. "
            "Do NOT use open_app(chrome/edge/firefox) before this — open_url handles browser launch automatically."
        ),
        returns="Confirmation that the URL was opened.",
        args={
            "url": "string, required — Full URL to open (e.g. https://github.com).",
        },
        examples=[
            {"user": "mở github.com", "call": {"tool": "open_url", "args": {"url": "https://github.com"}}},
            {"user": "vào youtube.com", "call": {"tool": "open_url", "args": {"url": "https://youtube.com"}}},
        ],
    ),

    ToolSpec(
        name="search_web",
        fn=search_web,
        category="browser",
        # OUTPUT: chỉ mở trình duyệt, KHÔNG trả data về cho agent.
        # Dùng khi user muốn tự xem kết quả bằng mắt trong browser.
        description="Open browser to Google — user sees results visually; agent gets NO text back.",
        when_to_use=(
            "Use ONLY when user explicitly wants to open browser and browse Google themselves. "
            "Do NOT use this when agent needs to read or answer from the web — use web_search instead."
        ),
        returns="Confirmation only (no content). Browser opens, user reads manually.",
        args={
            "query": "string, required — Search keywords (extract only the key terms, remove filler words).",
        },
        examples=[
            {"user": "mở google tìm học máy", "call": {"tool": "search_web", "args": {"query": "học máy"}}},
            {"user": "tìm kiếm python tutorial trên trình duyệt", "call": {"tool": "search_web", "args": {"query": "python tutorial"}}},
        ],
    ),

    ToolSpec(
        name="get_weather",
        fn=get_weather,
        category="browser",
        # OUTPUT: trả thẳng nhiệt độ/độ ẩm/gió từ wttr.in JSON API — không cần web_search hay web_read.
        # Dùng tool này TRƯỜC, chỉ fallback web_search khi thành phố không tìm thấy.
        description="Get current weather (temp, humidity, wind) for a city via wttr.in — direct API, no search needed.",
        when_to_use=(
            "Use immediately when user asks about weather, temperature, humidity, or wind of any city. "
            "Do NOT use web_search for weather — get_weather is faster and always returns actual numbers."
        ),
        returns="Text with temperature (C), feels-like, description, humidity, wind speed.",
        args={
            "city": "string, required — City name in English (e.g. 'Hanoi', 'Ho Chi Minh City', 'London').",
        },
        examples=[
            {"user": "nhiệt độ hà nội hiện tại", "call": {"tool": "get_weather", "args": {"city": "Hanoi"}}},
            {"user": "thời tiết tp hồ chí minh",    "call": {"tool": "get_weather", "args": {"city": "Ho Chi Minh City"}}},
            {"user": "hanoi temperature now",          "call": {"tool": "get_weather", "args": {"city": "Hanoi"}}},
        ],
    ),

    ToolSpec(
        name="web_search",
        fn=web_search,
        category="browser",
        # OUTPUT: trả về text title+URL+snippet thực sự → agent đọc và trả lời.
        # Đây là tool DUY NHẤT có thể lấy thông tin từ internet về cho agent.
        description="Fetch DuckDuckGo results and RETURN text to agent — agent reads and answers.",
        when_to_use=(
            "Use whenever agent must answer a question using internet data: facts, news, prices, weather. "
            "Do NOT use search_web when agent needs to read content — search_web opens browser only, returns nothing."
        ),
        returns="Text with [N] title / url / snippet for each result — agent reads this directly.",
        args={
            "query":       "string, required — Search query in the most effective keywords.",
            "max_results": "integer, optional — Number of results to return (default 5, max 10).",
        },
        examples=[
            {"user": "thời tiết hà nội hôm nay", "call": {"tool": "web_search", "args": {"query": "Hanoi weather today"}}},
            {"user": "bitcoin giá bao nhiêu", "call": {"tool": "web_search", "args": {"query": "bitcoin price usd"}}},
            {"user": "python list comprehension là gì", "call": {"tool": "web_search", "args": {"query": "python list comprehension explained"}}},
        ],
    ),

    ToolSpec(
        name="web_read",
        fn=web_read,
        category="browser",
        description="Read and return the text content of a specific URL.",
        when_to_use=(
            "Use when you have a specific URL (from web_search results) and need to read the full content "
            "to answer the user's question accurately."
        ),
        returns="Full text content of the webpage.",
        args={
            "url": "string, required — The URL to read.",
        },
        preconditions=["web_search"],
        examples=[
            {"user": "đọc trang web này", "call": {"tool": "web_read", "args": {"url": "https://example.com"}}},
        ],
    ),

    ToolSpec(
        name="browser_action",
        fn=browser_action,
        category="browser",
        description="Control the active browser tab (open new tab, close tab, reload, navigate back/forward).",
        when_to_use="User wants to control browser tabs or navigation (new tab, close tab, refresh, go back/forward).",
        returns="Confirmation of the browser action performed.",
        args={
            "action": "string, required — One of: 'new_tab', 'close_tab', 'reload', 'back', 'forward'.",
        },
        examples=[
            {"user": "mở tab mới", "call": {"tool": "browser_action", "args": {"action": "new_tab"}}},
            {"user": "đóng tab này", "call": {"tool": "browser_action", "args": {"action": "close_tab"}}},
            {"user": "reload trang", "call": {"tool": "browser_action", "args": {"action": "reload"}}},
        ],
    ),
]


# ── Public API ────────────────────────────────────────────────────────────────

def get_registry_dict() -> dict[str, Callable]:
    """Trả về {tool_name: fn} — dùng cho Executor (backward compatible)."""
    return {spec.name: spec.fn for spec in _SPECS}


def build_prompt_section(tool_names: list[str] | None = None) -> str:
    """Sinh AVAILABLE TOOLS section — format compact, tiết kiệm ~70% token.

    Mỗi tool chiếm 3–4 dòng thay vì 12–15 dòng:
        tool_name(arg1*, arg2)     (* = required)
          Mô tả + bối cảnh dùng.
          ⚑ DO NOT rule (nếu có).
          → {"type":"tool","tool":"...","args":{...}}

    Args:
        tool_names: Nếu cung cấp, chỉ render các tool có tên trong list này.
                    None = render toàn bộ (mặc định).
    """
    specs = _SPECS if tool_names is None else [s for s in _SPECS if s.name in tool_names]
    blocks: list[str] = []

    for spec in specs:
        lines: list[str] = []

        # Dòng 1: signature — tên + args (* = required)
        if spec.args:
            sig_parts = [
                f"{k}*" if "required" in v else k
                for k, v in spec.args.items()
            ]
            lines.append(f"{spec.name}({', '.join(sig_parts)})")
        else:
            lines.append(f"{spec.name}()")

        # Dòng 2: description + câu đầu of when_to_use (bỏ các câu DO NOT)
        desc = spec.description.rstrip(".")
        wtu_sentences = [s.strip() for s in spec.when_to_use.split(".") if s.strip()]
        first_wtu = next(
            (s for s in wtu_sentences if "NOT" not in s and "NEVER" not in s), ""
        )
        if first_wtu and first_wtu.lower() not in desc.lower():
            summary = f"{desc}. {first_wtu}."
        else:
            summary = f"{desc}."
        lines.append(f"  {summary[:140]}")

        # Dòng 3 (tùy chọn): rule DO NOT / disambiguation quan trọng nhất
        do_not = next(
            (s.strip() for s in wtu_sentences if "NOT" in s or "NEVER" in s),
            None,
        )
        if do_not:
            lines.append(f"  \u26d1 {do_not}.")

        # Dòng 4 (tùy chọn): preconditions
        if spec.preconditions:
            lines.append(f"  Requires: {', '.join(spec.preconditions)} to run first.")

        # Dòng cuối: ví dụ compact (JSON không khoảng trắng thừa)
        if spec.examples:
            ex = spec.examples[0]
            call_json = json.dumps(
                {"type": "tool", **ex["call"]},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            lines.append(f"  \u2192 {call_json}")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


# Sinh một lần tại import time — tránh rebuild mỗi lần Planner khởi tạo.
# Nếu thêm tool mới, restart app để PROMPT_SECTION cập nhật.
PROMPT_SECTION: str = build_prompt_section()
