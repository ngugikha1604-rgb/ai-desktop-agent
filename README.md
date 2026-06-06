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
→ 📌 Đã ghi nhớ: đường dẫn Desktop = D:\Desktop

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
| Browser | Mở URL, tìm kiếm Google, điều khiển tab |
| Voice input | Nhập lệnh bằng giọng nói (vi + en) — `Ctrl+Alt+V` |
| Long-term memory | Tự nhớ đường dẫn, app ưa thích, thông tin cá nhân qua nhiều phiên |
| User profile | Tên người dùng, ngôn ngữ ưa thích |

---

## Cài đặt

### Yêu cầu

- Windows 10/11
- Python 3.12+
- [Ollama](https://ollama.com/download)

### 1. Cài Ollama và pull model

```bash
# Tải Ollama tại https://ollama.com/download

# Pull 2 model (chỉ cần làm một lần, ~2-4 GB)
ollama pull qwen2.5:3b
ollama pull qwen2.5:0.5b
```

### 2. Cài thư viện Python

```bash
pip install -r requirements.txt
```

> **Về STT (giọng nói):** Tính năng này cần `faster-whisper` (đã có trong `requirements.txt`).
> Model Whisper `base` (~145 MB) tự tải lần đầu khi bạn nhấn nút mic — **không ảnh hưởng tốc độ khởi động app**.

### 3. Chạy

```bash
python main.py
```

Agent chạy nền ở system tray. Nhấn **`Ctrl+Alt+J`** để mở command bar.

> **Lưu ý về Ollama:** App khởi động bình thường dù Ollama chưa chạy.
> Nếu bạn gửi lệnh khi Ollama chưa lên, app sẽ hiển thị hướng dẫn thay vì báo lỗi kỹ thuật.
> Bật Ollama bất kỳ lúc nào bằng `ollama serve` (hoặc để nó tự chạy nền nếu đã cài dịch vụ).

### 4. Cấu hình (tuỳ chọn)

Chỉnh `config/settings.json`:

```json
{
  "planner_model": "qwen2.5:3b",
  "response_model": "qwen2.5:0.5b",
  "preferred_microphone": null
}
```

---

## Phím tắt

| Phím tắt | Chức năng |
|----------|-----------|
| `Ctrl+Alt+J` | Bật / tắt Command Bar |
| `Ctrl+Alt+V` | Bật / tắt nhập giọng nói |
| `Esc` | Đóng bar (hoặc huỷ ghi âm nếu đang nghe) |
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
│   ├── stt_engine.py            # faster-whisper: speech → text (lazy load)
│   ├── llm.py                   # OllamaClient + typed exceptions
│   ├── config.py                # Load settings + env
│   └── logger.py                # Logging → logs/agent.log
│
├── tools/
│   ├── __init__.py              # TOOL_REGISTRY (Dynamic Registry)
│   ├── open_app.py
│   ├── kill_process.py
│   ├── search_file.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── run_command.py
│   ├── system_info.py
│   ├── process_info.py
│   ├── active_window.py
│   ├── clipboard.py
│   ├── screenshot.py
│   ├── notification.py
│   ├── browser.py               # open_url, search_web
│   ├── browser_control.py       # browser_action (tab control)
│   └── result.py
│
├── ui/
│   ├── app.py                   # QApplication, STT, profile check
│   ├── command_bar.py           # Floating window, mic button
│   ├── worker.py                # QThread + timeout 60s
│   ├── stt_worker.py            # QThread ghi âm + silence detection
│   ├── hotkey.py                # Ctrl+Alt+J, Ctrl+Alt+V
│   ├── tray.py                  # System tray icon
│   └── styles.py                # QSS stylesheet
│
├── prompts/
│   ├── planner_prompt.txt
│   └── agent_prompt.txt
│
├── config/
│   └── settings.json
│
├── data/                        # SQLite (git-ignored)
├── logs/                        # agent.log (git-ignored)
└── tests/
```

---

## Kiến trúc

```
Ctrl+Alt+J / Ctrl+Alt+V
        │
        ▼
 CommandBar (PySide6)
  ┌─────┴──────┐
  │ text input │  🎤 mic button
  └─────┬──────┘       │
        │         SttWorker (QThread)
        │         load model khi lần đầu dùng
        │         → faster-whisper transcribe
        │         → fill_and_submit()
        ▼
 AgentWorker (QThread, timeout 60s)
        │
        ▼
   Agent.run()
    ├─► Memory (SQLite)
    ├─► Planner ────► OllamaClient (qwen2.5:3b)
    │              inject long_term_memory context
    │              → JSON plan
    ├─► TaskAnalyzer ► fast-path: không gọi LLM nếu lệnh đơn giản
    │                └► OllamaClient (qwen2.5:0.5b) → multi-task JSON plan
    ├─► Executor ──► TOOL_REGISTRY (16 tools)
    ├─► ResponseFormatter ──► OllamaClient (qwen2.5:0.5b)
    └─► MemoryExtractor (background thread)
            save long_term_memory / user_profile
        │
        ▼
 CommandBar — response + "📌 Đã ghi nhớ"
```

---

## Long-term Memory

| Loại | Ví dụ |
|------|-------|
| `path` | "Desktop của tôi ở D:\Desktop" |
| `preference` | "Tôi dùng VS Code", "Trình duyệt là Firefox" |
| `schedule` | "Họp mỗi thứ Hai 9h sáng" |
| `personal` | "Tên tôi là Nam", "Tôi là lập trình viên" |

```
> Bạn còn nhớ gì về tôi?   — xem tất cả bộ nhớ
> Quên đi rằng Desktop tôi  — xoá bộ nhớ cụ thể
> Tên tôi là [tên]          — cập nhật tên tự động
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Ollama — Qwen2.5 3B / 0.5B (local) |
| STT | faster-whisper `base` — Whisper (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite (built-in Python) |
| System APIs | pywin32, psutil |
| Browser control | pyautogui |
| Screenshot | Pillow |
