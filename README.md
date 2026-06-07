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

> Tìm file report trong ổ C rồi đọc nội dung
→ Đã tìm thấy: C:\Users\ngugi\Documents\report_q3.txt
  Nội dung: Báo cáo quý 3...

> Mở github.com rồi mở tab mới
→ Đã mở github.com. Đã mở tab mới.

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
| Task decomposition | Tự động tách lệnh multi-step thành subtasks có thứ tự |
| Long-term memory | Tự nhớ đường dẫn, app ưa thích, thông tin cá nhân qua nhiều phiên |
| User profile | Tên người dùng, ngôn ngữ ưa thích |

---

## Cài đặt

### Yêu cầu

- Windows 10/11
- Python 3.12+
- [Ollama](https://ollama.com/download)
- Không cần GPU — chạy hoàn toàn trên CPU

### 1. Cài Ollama và pull model

```bash
# Tải Ollama tại https://ollama.com/download

# Pull 2 model (chỉ cần làm một lần, ~2-4 GB tổng)
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
# Giao diện desktop (mặc định)
python main.py

# Hoặc tường minh
python main.py gui

# Chạy một lệnh từ CLI
python main.py chat "RAM còn bao nhiêu?"

# Vòng lặp chat CLI (không cần giao diện)
python main.py repl
```

Agent GUI chạy nền ở system tray. Nhấn **`Ctrl+Alt+J`** để mở command bar.

> **Lưu ý về Ollama:** App khởi động bình thường dù Ollama chưa chạy.
> Nếu bạn gửi lệnh khi Ollama chưa lên, app sẽ hiển thị hướng dẫn thay vì báo lỗi kỹ thuật.
> Bật Ollama bất kỳ lúc nào bằng `ollama serve` (hoặc để nó tự chạy nền nếu đã cài dịch vụ).

> **Tối ưu hiệu năng CPU:** Flash Attention và KV Cache quantization được bật tự động
> khi khởi động qua `python main.py`. Nếu bạn chạy `ollama serve` độc lập trước đó,
> hãy set thủ công:
> ```bash
> set OLLAMA_FLASH_ATTENTION=1
> set OLLAMA_KV_CACHE_TYPE=q8_0
> ollama serve
> ```

### 4. Cấu hình (tuỳ chọn)

Chỉnh `config/settings.json`:

```json
{
  "llm_provider": "ollama",
  "planner_model": "qwen2.5:3b",
  "analyzer_model": "qwen2.5:0.5b",
  "response_model": "qwen2.5:0.5b",
  "ollama_base_url": "http://localhost:11434",
  "num_ctx": 4096,
  "num_predict_planner": 256,
  "num_predict_analyzer": 512,
  "num_predict_response": 512,
  "num_predict_extractor": 128,
  "caveman_mode": true,
  "history_limit": 6,
  "max_agent_steps": 10,
  "max_task_attempts": 3,
  "stt_model": "base",
  "preferred_microphone": null
}
```

| Tham số | Mô tả |
|---------|-------|
| `planner_model` | Model chọn action tiếp theo (qwen2.5:3b) |
| `analyzer_model` | Model phân tích subtask (qwen2.5:0.5b) |
| `response_model` | Model dùng cho memory extractor (qwen2.5:0.5b) |
| `num_ctx` | Context window tối đa (tokens) |
| `num_predict_*` | Token tối đa mỗi LLM call theo vai trò |
| `caveman_mode` | Nén output LLM (bỏ filler words) — giảm latency |
| `history_limit` | Số tin nhắn history giữ lại trong context |
| `max_agent_steps` | Số bước tối đa mỗi agent loop |
| `max_task_attempts` | Số lần retry tối đa cho mỗi subtask |

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
├── main.py                      # Entry point (gui / chat / repl)
│
├── agent/
│   ├── agent.py                 # Agent Loop: điều phối toàn bộ pipeline
│   ├── task_analyzer.py         # Tách lệnh multi-step → TaskPlan (goal + subtasks)
│   ├── planner.py               # LLM → JSON action (tool call hoặc finish)
│   ├── executor.py              # Thực thi 1 tool action từ TOOL_REGISTRY
│   ├── state.py                 # AgentState: goal, tasks, history, observation
│   ├── memory.py                # SQLite: history, user_profile, long_term_memory
│   ├── memory_extractor.py      # Trích xuất thông tin từ hội thoại (background thread)
│   ├── llm.py                   # OllamaClient + typed exceptions
│   ├── stt_engine.py            # faster-whisper: speech → text (lazy load)
│   ├── config.py                # Load settings.json + .env
│   └── logger.py                # Logging → logs/agent.log
│
├── tools/
│   ├── registry.py              # ToolSpec + TOOL_REGISTRY (16 tools) + prompt builder
│   ├── __init__.py              # Export TOOL_REGISTRY dict
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
│   ├── browser_utils.py         # Shared browser state: detect/focus browser window
│   └── result.py                # Chuẩn hoá result dict {success, retryable, message}
│
├── ui/
│   ├── app.py                   # DesktopApp: QApplication, STT, hotkey, tray
│   ├── command_bar.py           # Floating command bar + chat bubbles
│   ├── worker.py                # AgentWorker (QThread, timeout 60s)
│   ├── stt_worker.py            # SttWorker (QThread: ghi âm + silence detection)
│   ├── hotkey.py                # Ctrl+Alt+J / Ctrl+Alt+V global hotkeys
│   ├── tray.py                  # System tray icon
│   └── styles.py                # QSS stylesheet
│
├── prompts/
│   ├── planner_prompt.txt       # System prompt cho Planner (inject tool docs tự động)
│   ├── task_analyzer_prompt.txt # System prompt cho TaskAnalyzer
│   └── agent_prompt.txt         # Prompt phụ (response formatting)
│
├── config/
│   └── settings.json            # Cấu hình runtime
│
├── data/                        # SQLite DB (git-ignored)
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
    ├─► Special query handler
    │    (nhớ gì / quên đi → trả lời trực tiếp, bỏ qua loop)
    │
    ├─► TaskAnalyzer ──► OllamaClient (qwen2.5:0.5b)
    │    Fast-path: 1 action → 1 task, không gọi LLM
    │    Multi-step: LLM tách thành TaskPlan (goal + subtasks có thứ tự)
    │
    ├─► AgentState (goal, tasks[], history, observation)
    │
    └─► Agent Loop (max 10 bước)
         │
         ├─► Stuck detection (same tool + args 2 lần liên tiếp → dừng)
         ├─► Planner ──► OllamaClient (qwen2.5:3b)
         │    inject memory context (step đầu)
         │    inject current task + hint + requires
         │    → JSON: {"type": "tool", ...} | {"type": "finish", ...}
         │
         ├─► Executor ──► TOOL_REGISTRY (16 tools)
         │    → result {success, retryable, message}
         │
         ├─► Observation → update state
         │    success → mark task done, move to next
         │    retryable fail → retry (max 3 lần/task)
         │    non-retryable → mark failed, move on
         │
         └─► (repeat)
              │
              ▼ tất cả tasks xong
         Summary observation → Planner tổng kết → finish answer
              │
              ▼
    MemoryExtractor (background thread)
         Heuristic filter → LLM extract → save long_term_memory
         Notify UI nếu có gì mới lưu (tối đa 3 lần/phiên)
              │
              ▼
    CommandBar — hiển thị response + "📌 Đã ghi nhớ"
```

---

## Task Decomposition

`TaskAnalyzer` tự động tách lệnh phức thành subtasks có thứ tự trước khi vào Agent Loop.

**Fast-path** (không gọi LLM): input không có từ nối multi-step (`rồi`, `sau đó`, `tiếp theo`, `then`, `after that`...) → 1 task duy nhất, tiết kiệm ~1 inference call.

**LLM path**: dùng `qwen2.5:0.5b` để sinh `TaskPlan`:

```json
{
  "goal": "Đọc nội dung file report",
  "tasks": [
    {
      "task": "Tìm file report trong ổ C",
      "type": "search",
      "hint": "Use search_file tool with root C:\\",
      "requires": [],
      "expected_output": "file_path",
      "status": "pending"
    },
    {
      "task": "Đọc nội dung file",
      "type": "read",
      "hint": "Use read_file tool",
      "requires": ["file_path"],
      "expected_output": "file content",
      "status": "pending"
    }
  ]
}
```

Mỗi subtask có `hint` (gợi ý tool) và `requires` (output từ task trước) → Planner chọn đúng tool ngay từ bước đầu thay vì phải tự suy luận.

---

## Tool Registry

`tools/registry.py` là single source of truth cho tất cả 16 tools. Mỗi tool được khai báo dưới dạng `ToolSpec` với metadata đầy đủ:

```python
ToolSpec(
    name="search_file",
    fn=search_file,
    description="...",
    when_to_use="...",
    returns="...",
    args={"keyword": "string, required — ...", "root": "string, optional — ..."},
    examples=[{"user": "tìm file README", "call": {"tool": "search_file", "args": {...}}}],
)
```

Registry tự sinh đoạn `AVAILABLE TOOLS` cho planner prompt (`build_prompt_section()`) — không cần viết tay trong file `.txt`.

### 16 Tools hiện có

| Nhóm | Tool | Mô tả |
|------|------|-------|
| App | `open_app` | Mở ứng dụng theo tên / alias |
| App | `kill_process` | Tắt process theo tên hoặc PID |
| File | `search_file` | Tìm file theo từ khoá |
| File | `read_file` | Đọc nội dung file |
| File | `write_file` | Ghi / append nội dung file |
| System | `get_system_info` | RAM, CPU, Disk usage |
| System | `get_running_processes` | Danh sách process đang chạy |
| System | `get_active_window` | Cửa sổ đang được focus |
| Shell | `run_command` | Chạy lệnh terminal |
| Clipboard | `get_clipboard` | Đọc clipboard |
| Clipboard | `set_clipboard` | Ghi vào clipboard |
| Screen | `take_screenshot` | Chụp màn hình |
| Screen | `send_notification` | Gửi Windows toast notification |
| Browser | `open_url` | Mở URL (tự mở browser nếu chưa chạy) |
| Browser | `search_web` | Tìm kiếm Google |
| Browser | `browser_action` | Điều khiển tab (new/close/reload/back/forward) |

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

Memory extraction chạy **background thread** sau mỗi turn, với bộ lọc heuristic để tránh gọi LLM không cần thiết:
- Bỏ qua input < 20 ký tự hoặc thuộc danh sách generic phrase (`ok`, `cảm ơn`, `bye`...)
- Chỉ extract khi input chứa keyword gợi ý có thông tin đáng lưu (`thích`, `là`, `ở`, `path`, `dùng`...)
- UI chỉ hiển thị thông báo "📌 Đã ghi nhớ" tối đa 3 lần mỗi phiên (DB vẫn lưu đầy đủ)
- Không bao giờ lưu thông tin nhạy cảm (mật khẩu, token, API key, số tài khoản...)

---

## SQLite Schema

```
history          — chat history (role, content, created_at)
user_profile     — tên, ngôn ngữ ưa thích (1 hàng duy nhất)
long_term_memory — key/value/type/is_active/access_count/relevance_score
memories         — legacy key-value store (dự phòng)
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Ollama — Qwen2.5 3B (planner) / 0.5B (analyzer, extractor) |
| STT | faster-whisper `base` — Whisper (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite (built-in Python) |
| Validation | Pydantic v2 |
| System APIs | pywin32, psutil |
| Browser control | pyautogui |
| Screenshot | Pillow |
| CLI | Typer + Rich |

---

## Roadmap

### Tính năng đã hoàn thành

- [x] Phase 1 — MVP: mở app, system info, chạy lệnh
- [x] Phase 2 — File management
- [x] Phase 3 — Chat history (SQLite)
- [x] Phase 4 — Multi-step planning
- [x] Phase 5 — Tool Registry (16 tools + ToolSpec metadata)
- [x] Phase 6 — Desktop UX: floating bar, hotkey, tray
- [x] Phase 7 — Local LLM (Ollama / Qwen2.5)
- [x] Phase 8 — Long-term memory & user profile
- [x] Phase 9 — Voice input (faster-whisper)
- [x] Phase 10 — Browser automation
- [x] Agent Loop — State, Observation, Stuck detection, Retry logic
- [x] Task Decomposition — TaskAnalyzer (multi-step → subtasks với hint/requires)

### Tiếp theo (theo PLAN.md)

- [ ] Phase 5 (PLAN.md) — Thêm tools thực tế: OCR màn hình, click, type, key press
- [ ] Phase 6 (PLAN.md) — Validation layer (kiểm tra args trước khi gọi tool)
- [ ] Phase 7 (PLAN.md) — Coding Agent (project_tree, grep_code, apply_patch)
