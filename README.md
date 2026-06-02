# AI Desktop Agent

Một AI Agent chạy cục bộ trên Windows, nhận lệnh ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) và thực thi trực tiếp trên hệ điều hành — không cần mở terminal, không cần thao tác chuột.

> Gọi bằng `Ctrl+Alt+J` từ bất kỳ đâu trên màn hình.

---

## Demo nhanh

```
> Ram tôi còn bao nhiêu?
→ RAM đang dùng 9.2 GB / 16 GB (57.5%). CPU: 12%. Ổ C còn 48 GB trống.

> Tắt Chrome đi
→ Đã kết thúc chrome.exe (PID 4821).

> Chụp màn hình lưu lên Desktop
→ Đã chụp màn hình → screenshot_20250602_143012.png (2560×1440px).

> Tìm file báo cáo tháng 5
→ Tìm thấy 3 file: báo cáo tháng 5.docx, ...
```

---

## Tính năng hiện tại

| Nhóm | Tính năng |
|------|-----------|
| App control | Mở app, tắt process |
| File | Tìm file, đọc file, ghi file |
| System | CPU/RAM/Disk, danh sách process, cửa sổ đang active |
| Shell | Chạy lệnh terminal |
| Clipboard | Đọc / ghi clipboard |
| Screen | Chụp màn hình, gửi Windows notification |

---

## Cài đặt

### Yêu cầu

- Windows 10/11
- Python 3.12+

### Cài thư viện

```bash
pip install -r requirements.txt
```

### Cấu hình API key

```bash
cp .env.example .env
```

Mở `.env`, điền API key từ [Google AI Studio](https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=your_key_here
```

### Chạy

```bash
python main.py
```

Agent sẽ chạy nền và xuất hiện ở system tray. Nhấn `Ctrl+Alt+J` để mở command bar.

---

## Cấu trúc thư mục

```
ai-desktop-agent/
├── main.py                  # Entry point
│
├── agent/
│   ├── agent.py             # Điều phối toàn bộ pipeline
│   ├── planner.py           # Gọi Gemini → sinh JSON plan
│   ├── executor.py          # Chạy từng tool theo plan
│   ├── memory.py            # Lưu chat history vào SQLite
│   ├── llm.py               # Gemini API client
│   └── config.py            # Load settings + env
│
├── tools/
│   ├── __init__.py          # TOOL_REGISTRY (13 tools)
│   ├── open_app.py          # Mở ứng dụng
│   ├── kill_process.py      # Tắt process
│   ├── search_file.py       # Tìm file theo tên
│   ├── read_file.py         # Đọc nội dung file
│   ├── write_file.py        # Ghi / tạo file
│   ├── run_command.py       # Chạy lệnh shell
│   ├── system_info.py       # CPU / RAM / Disk
│   ├── process_info.py      # Danh sách process
│   ├── active_window.py     # Cửa sổ đang focus
│   ├── clipboard.py         # Đọc / ghi clipboard
│   ├── screenshot.py        # Chụp màn hình
│   ├── notification.py      # Windows toast notification
│   └── result.py            # Helper ok() / fail()
│
├── ui/
│   ├── app.py               # QApplication + khởi động
│   ├── command_bar.py       # Floating chat window
│   ├── worker.py            # QThread chạy agent
│   ├── hotkey.py            # Global hotkey Ctrl+Alt+J
│   ├── tray.py              # System tray icon
│   └── styles.py            # QSS stylesheet
│
├── prompts/
│   ├── planner_prompt.txt   # System prompt cho Planner
│   └── agent_prompt.txt     # System prompt cho response
│
├── config/
│   └── settings.json        # Model, UI config
│
├── data/                    # SQLite memory (git-ignored)
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Kiến trúc

```
Ctrl+Alt+J
    │
    ▼
CommandBar (PySide6)
    │  user input
    ▼
AgentWorker (QThread)
    │
    ▼
Agent.run()
    ├─► Memory.get_recent_history()
    ├─► Planner  ──► Gemini API ──► JSON plan
    ├─► Executor ──► TOOL_REGISTRY ──► tool functions
    └─► _format_response ──► Gemini API ──► natural language
    │
    ▼
CommandBar — hiển thị bubble response
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Gemini 2.5 Flash (Google AI Studio) |
| UI | PySide6 (Qt6) |
| Database | SQLite via SQLAlchemy |
| System APIs | pywin32, psutil |
| Screenshot | Pillow |

---

## Roadmap

- [x] Phase 1 — MVP: mở app, system info, chạy lệnh
- [x] Phase 2 — File management: tìm, đọc, ghi file
- [x] Phase 3 — Memory: lưu chat history SQLite
- [x] Phase 4 — Multi-step planning: Gemini JSON plan
- [x] Phase 5 — Tool registry: 13 tools, clipboard, screenshot, notification
- [x] Phase 6 — Desktop UX: floating command bar, chat bubbles, hotkey, tray
- [ ] Phase 7 — Local LLM (Ollama / Qwen)
- [ ] Phase 8 — Long-term memory & user profile
- [ ] Phase 9 — Voice input
- [ ] Phase 10 — Browser automation
