# AI Desktop Agent

Một AI Agent chạy **hoàn toàn cục bộ** trên Windows, nhận lệnh ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) và thực thi trực tiếp trên hệ điều hành — không cần mở terminal, không cần thao tác chuột, không gửi dữ liệu ra ngoài internet.

> Gọi bằng **`Ctrl+Alt+J`** từ bất kỳ đâu trên màn hình.
> Nhập lệnh bằng giọng nói bằng **`Ctrl+Alt+V`**.

---

## Demo nhanh

```
> RAM tôi còn bao nhiêu?
→ RAM đang dùng 9.2 GB / 16 GB (57.5%). CPU: 12%. Ổ C còn 48 GB trống.

> Tắt Chrome đi
→ Đã kết thúc chrome.exe (PID 4821).

> Tìm kiếm học máy là gì
→ Đã mở: https://www.google.com/search?q=học+máy+là+gì

> Tìm file README rồi đọc nội dung
→ [Task 1/2] search_file → Tìm thấy: C:\project\README.md
→ [Task 2/2] read_file  → # AI Desktop Agent ...

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
| System | CPU / RAM / Disk, danh sách process, cửa sổ đang active |
| Shell | Chạy lệnh terminal |
| Clipboard | Đọc / ghi clipboard |
| Screen | Chụp màn hình, gửi Windows notification |
| Browser | Mở URL, tìm kiếm Google, điều khiển tab |
| Multi-step | Tự phân tách lệnh phức tạp thành subtasks có thứ tự |
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

# Pull 2 model (chỉ cần làm một lần, ~2 GB)
ollama pull qwen2.5:3b
ollama pull qwen2.5:0.5b
```

### 2. Cài thư viện Python

```bash
pip install -r requirements.txt
```

> **Về STT (giọng nói):** Model Whisper `base` (~145 MB) tự tải lần đầu khi nhấn nút mic — không ảnh hưởng tốc độ khởi động.

### 3. Chạy

```bash
python main.py
```

Agent chạy nền ở system tray. Nhấn **`Ctrl+Alt+J`** để mở command bar.

> **Lưu ý:** App khởi động bình thường dù Ollama chưa chạy. Nếu gửi lệnh khi Ollama chưa lên, app hiển thị hướng dẫn thay vì báo lỗi kỹ thuật. Bật Ollama bất kỳ lúc nào bằng `ollama serve`.

### 4. Cấu hình (tuỳ chọn)

Chỉnh `config/settings.json`:

```json
{
  "planner_model":    "qwen2.5:3b",
  "analyzer_model":   "qwen2.5:0.5b",
  "response_model":   "qwen2.5:0.5b",
  "max_agent_steps":  10,
  "max_task_attempts": 3,
  "num_ctx":          4096,
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
├── main.py
│
├── agent/
│   ├── agent.py             # Điều phối Agent Loop, xử lý lỗi Ollama
│   ├── task_analyzer.py     # Phân tích multi-step input → TaskPlan (SubTask list)
│   ├── state.py             # AgentState dataclass (goal, tasks, history, observation)
│   ├── planner.py           # Planner: qwen2.5:3b → action JSON mỗi bước
│   ├── executor.py          # Thực thi 1 tool action, trả {success, message, retryable}
│   ├── memory.py            # SQLite: chat history, user_profile, long_term_memory
│   ├── memory_extractor.py  # Trích xuất và lưu memory từ hội thoại (background)
│   ├── stt_engine.py        # faster-whisper: speech → text (lazy load)
│   ├── llm.py               # OllamaClient + typed exceptions
│   ├── config.py            # Load settings.json + env
│   └── logger.py            # Logging → logs/agent.log
│
├── tools/
│   ├── __init__.py          # TOOL_REGISTRY từ registry.py
│   ├── registry.py          # ToolSpec: metadata + build_prompt_section() cho planner
│   ├── result.py            # ok() / fail() — chuẩn hoá tool output
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
│   ├── browser.py           # open_url, search_web
│   ├── browser_control.py   # browser_action (tab control)
│   └── browser_utils.py
│
├── ui/
│   ├── app.py               # QApplication, STT, profile check
│   ├── command_bar.py       # Floating window, mic button, chat bubbles
│   ├── worker.py            # QThread + timeout 60s
│   ├── stt_worker.py        # QThread ghi âm + silence detection
│   ├── hotkey.py            # Ctrl+Alt+J, Ctrl+Alt+V
│   ├── tray.py              # System tray icon
│   └── styles.py            # QSS stylesheet
│
├── prompts/
│   ├── planner_prompt.txt       # System prompt cho Planner
│   └── task_analyzer_prompt.txt # System prompt cho TaskAnalyzer
│
├── config/
│   └── settings.json
│
├── data/    # SQLite DB (git-ignored)
├── logs/    # agent.log (git-ignored)
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
        │         → faster-whisper transcribe
        │         → fill_and_submit()
        ▼
 AgentWorker (QThread, timeout 60s)
        │
        ▼
   Agent.run()
    │
    ├─► Memory (SQLite) — lấy profile, lưu lịch sử hội thoại
    │
    ├─► [nhớ / quên] — xử lý trực tiếp, không qua loop
    │
    └─► _run_loop(goal)
            │
            ├─► TaskAnalyzer
            │     ├─ fast-path (lệnh đơn) → 1 task, không gọi LLM
            │     └─ qwen2.5:0.5b → TaskPlan {goal, tasks[]}
            │           task: {task, type, hint, requires, expected_output}
            │
            └─► AgentState {goal, tasks, history, observation}
                    │
                    └─► while step < MAX_STEPS (10):
                            │
                            ├─► Planner ──► qwen2.5:3b
                            │     inject: memory + user name (step 0)
                            │     inject: current task + hint + requires + expected_output
                            │     inject: history[-5] + observation
                            │     stuck detection → skip LLM nếu lặp
                            │     → {"type": "tool", "tool": "...", "args": {...}}
                            │     → {"type": "finish", "answer": "..."}
                            │
                            ├─► [tool] Executor ──► TOOL_REGISTRY (16 tools)
                            │     → {success, message, retryable}
                            │     success  → mark task done, next task
                            │     retryable fail → tăng attempts (max 3)
                            │     permanent fail → mark task failed
                            │
                            └─► [finish] → trả answer
        │
        ├─► MemoryExtractor (background) ──► qwen2.5:0.5b
        │     → lưu long_term_memory / user_profile vào SQLite
        │
        ▼
 CommandBar — hiển thị response + "📌 Đã ghi nhớ"
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
> Bạn còn nhớ gì về tôi?     — xem tất cả bộ nhớ
> Quên đi rằng Desktop tôi   — xoá bộ nhớ cụ thể
> Tên tôi là [tên]            — cập nhật tên tự động
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM (planner) | Ollama — Qwen2.5 3B (local) |
| LLM (analyzer / memory) | Ollama — Qwen2.5 0.5B (local) |
| STT | faster-whisper `base` — Whisper (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite (built-in Python) |
| Data validation | Pydantic v2 |
| System APIs | pywin32, psutil |
| Browser / GUI control | pyautogui |
| Screenshot | Pillow |

---

## Roadmap

- [x] Agent Loop — planner chọn 1 action/bước, observe, lặp đến khi done
- [x] Task Decomposition — TaskAnalyzer tách multi-step input thành SubTask list
- [x] Tool Registry — ToolSpec với description, examples, hint → sinh prompt tự động
- [x] Observation chuẩn hoá — `{success, message, retryable}` từ mọi tool
- [x] Long-term memory — nhớ đường dẫn, ưu tiên, lịch trình qua nhiều phiên
- [x] Voice input — faster-whisper, vi + en, lazy load
- [x] Browser automation — open URL, search, tab control
- [ ] GUI tools — OCR màn hình, click(x,y), type_text, key_press
- [ ] Coding Agent — project_tree, grep_code, read_code_chunk, apply_patch
