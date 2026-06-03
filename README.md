# AI Desktop Agent

Một AI Agent chạy **hoàn toàn cục bộ** trên Windows, nhận lệnh ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) và thực thi trực tiếp trên hệ điều hành — không cần mở terminal, không cần thao tác chuột, không gửi dữ liệu ra ngoài internet.

> Gọi bằng **`Ctrl+Alt+J`** từ bất kỳ đâu trên màn hình.  
> Nhập lệnh bằng giọng nói bằng **`Ctrl+Alt+V`**.

---

## Demo nhanh

```
> Ram tôi còn bao nhiêu?
→ RAM đang dùng 9.2 GB / 16 GB (57.5%). CPU: 12%. Ổ C còn 48 GB trống.

> Tắt Chrome đi
→ Đã kết thúc chrome.exe (PID 4821).

> Tìm kiếm học máy là gì
→ Đã mở: https://www.google.com/search?q=h%E1%BB%8Dc+m%C3%A1y+l%C3%A0+g%C3%AC

> Mở tab mới
→ Đã mở tab mới.

> Desktop của tôi ở D:\Desktop
→ Đã ghi nhớ: đường dẫn Desktop = D:\Desktop

> Bạn còn nhớ gì về tôi?
→ 📁 Đường dẫn:
    • đường dẫn Desktop: D:\Desktop
  ⭐ Ưa thích:
    • trình duyệt: Firefox
```

---

## Tính năng

| Nhóm | Tính năng |
|------|-----------|
| App control | Mở app, tắt process |
| File | Tìm file, đọc file, ghi file |
| System | CPU/RAM/Disk, danh sách process, cửa sổ đang active |
| Shell | Chạy lệnh terminal |
| Clipboard | Đọc / ghi clipboard |
| Screen | Chụp màn hình, gửi Windows notification |
| Browser | Mở URL, tìm kiếm Google, điều khiển tab (new/close/reload/back/forward) |
| Voice input | Nhập lệnh bằng giọng nói (tiếng Việt + tiếng Anh) — Ctrl+Alt+V |
| Long-term memory | Tự động ghi nhớ thông tin cá nhân, đường dẫn, ứng dụng ưa thích qua nhiều phiên |
| User profile | Lưu tên người dùng, ngôn ngữ ưa thích |

---

## Cài đặt

### Yêu cầu

- Windows 10/11
- Python 3.12+
- [Ollama](https://ollama.com/download) đã cài và đang chạy

### 1. Cài Ollama và pull model

```bash
# Tải Ollama tại https://ollama.com/download, sau đó:
ollama serve

# Pull 2 model (chạy lần đầu, ~2-4 GB)
ollama pull qwen2.5:3b
ollama pull qwen2.5:0.5b
```

### 2. Cài thư viện Python

```bash
pip install -r requirements.txt
```

> **Lưu ý về STT (giọng nói):** Model Whisper `base` (~145 MB) sẽ tự tải lần đầu khi bạn nhấn nút mic 🎤.

### 3. Cấu hình (tuỳ chọn)

Chỉnh `config/settings.json` để đổi model hoặc thiết lập microphone:

```json
{
  "planner_model": "qwen2.5:3b",
  "response_model": "qwen2.5:0.5b",
  "preferred_microphone": null
}
```

### 4. Chạy

```bash
python main.py
```

Agent chạy nền ở system tray. Nhấn **`Ctrl+Alt+J`** để mở command bar.

---

## Phím tắt

| Phím tắt | Chức năng |
|----------|-----------|
| `Ctrl+Alt+J` | Bật / tắt Command Bar |
| `Ctrl+Alt+V` | Bật / tắt nhập lệnh bằng giọng nói |
| `Esc` | Đóng Command Bar (hoặc huỷ ghi âm nếu đang nghe) |
| `Enter` | Gửi lệnh |

---

## Cấu trúc thư mục

```
ai-desktop-agent/
├── main.py                      # Entry point
│
├── agent/
│   ├── agent.py                 # Điều phối pipeline, xử lý lỗi Ollama
│   ├── planner.py               # LLM → JSON plan, inject memory context
│   ├── executor.py              # Chạy từng tool theo plan
│   ├── memory.py                # SQLite: history, user_profile, long_term_memory
│   ├── memory_extractor.py      # Trích xuất thông tin từ hội thoại (background)
│   ├── stt_engine.py            # faster-whisper: speech → text (local)
│   ├── llm.py                   # OllamaClient + typed exceptions
│   ├── config.py                # Load settings + env
│   └── logger.py                # Logging tập trung → logs/agent.log
│
├── tools/
│   ├── __init__.py              # TOOL_REGISTRY (16 tools)
│   ├── open_app.py              # Mở ứng dụng
│   ├── kill_process.py          # Tắt process
│   ├── search_file.py           # Tìm file theo tên
│   ├── read_file.py             # Đọc nội dung file
│   ├── write_file.py            # Ghi / tạo file
│   ├── run_command.py           # Chạy lệnh shell
│   ├── system_info.py           # CPU / RAM / Disk
│   ├── process_info.py          # Danh sách process
│   ├── active_window.py         # Cửa sổ đang focus
│   ├── clipboard.py             # Đọc / ghi clipboard
│   ├── screenshot.py            # Chụp màn hình
│   ├── notification.py          # Windows toast notification
│   ├── browser.py               # open_url, search_web
│   ├── browser_control.py       # browser_action (tab control)
│   └── result.py                # Helper ok() / fail()
│
├── ui/
│   ├── app.py                   # QApplication, STT, profile check
│   ├── command_bar.py           # Floating chat window, mic button
│   ├── worker.py                # QThread + timeout 60s
│   ├── stt_worker.py            # QThread ghi âm + silence detection
│   ├── hotkey.py                # Global hotkeys: Ctrl+Alt+J, Ctrl+Alt+V
│   ├── tray.py                  # System tray icon
│   └── styles.py                # QSS stylesheet
│
├── prompts/
│   ├── planner_prompt.txt       # System prompt cho Planner (16 tools)
│   └── agent_prompt.txt         # System prompt cho response formatter
│
├── config/
│   └── settings.json            # Model, STT, UI config
│
├── data/                        # SQLite memory (git-ignored)
├── logs/                        # agent.log (git-ignored)
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Kiến trúc

```
Ctrl+Alt+J / Ctrl+Alt+V
        │
        ▼
 CommandBar (PySide6)
  ┌─────┴──────┐
  │  text input │  mic button 🎤
  └─────┬──────┘       │
        │         SttWorker (QThread)
        │         → faster-whisper
        │         → fill_and_submit()
        ▼
 AgentWorker (QThread, timeout 60s)
        │
        ▼
   Agent.run()
    ├─► Memory.get_recent_history()
    ├─► Planner  ──► OllamaClient (qwen2.5:3b)
    │               └─ inject long_term_memory context
    │               └─► JSON plan
    ├─► Executor ──► TOOL_REGISTRY (16 tools)
    ├─► _format_response ──► OllamaClient (qwen2.5:0.5b)
    └─► MemoryExtractor (background thread)
            └─► lưu long_term_memory / user_profile
        │
        ▼
 CommandBar — hiển thị response + "📌 Đã ghi nhớ"
```

---

## Long-term Memory

Agent tự động ghi nhớ thông tin qua nhiều phiên làm việc:

| Loại | Ví dụ |
|------|-------|
| `path` | "Desktop của tôi ở D:\Desktop" |
| `preference` | "Tôi dùng VS Code", "Trình duyệt là Firefox" |
| `schedule` | "Họp mỗi thứ Hai 9h sáng" |
| `personal` | "Tên tôi là Nam", "Tôi là lập trình viên" |

**Câu lệnh quản lý bộ nhớ:**

```
> Bạn còn nhớ gì về tôi?      — Xem tất cả bộ nhớ
> Quên đi rằng Desktop tôi    — Xoá bộ nhớ cụ thể
> Tên tôi là [tên]            — Cập nhật tên tự động
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Ollama — Qwen2.5 3B / 0.5B (chạy hoàn toàn cục bộ) |
| STT | faster-whisper `base` — Whisper (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite (thuần Python, không cần server) |
| System APIs | pywin32, psutil |
| Browser control | pyautogui |
| Screenshot | Pillow |

---

## Roadmap

- [x] Phase 1 — MVP: mở app, system info, chạy lệnh
- [x] Phase 2 — File management: tìm, đọc, ghi file
- [x] Phase 3 — Memory: lưu chat history SQLite
- [x] Phase 4 — Multi-step planning: JSON plan
- [x] Phase 5 — Tool registry: 13 tools, clipboard, screenshot, notification
- [x] Phase 6 — Desktop UX: floating command bar, chat bubbles, hotkey, tray
- [x] Phase 7 — Local LLM: chuyển sang Ollama / Qwen2.5
- [x] Phase 8 — Long-term memory & user profile
- [x] Phase 9 — Voice input: faster-whisper, Ctrl+Alt+V
- [x] Phase 10 — Browser automation: open URL, search, tab control
