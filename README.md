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
🔴 [NGUY HIỂM] kill_process("chrome.exe")
   Sẽ kết thúc tiến trình: 'chrome.exe'.
→ [Từ chối] / [Cho phép]  ← hộp thoại xác nhận hiện ra

> Ghi nội dung "Hello" vào C:\notes.txt
🔴 [NGUY HIỂM] write_file("C:\notes.txt")
   Sẽ ghi đè (overwrite) file: 'C:\notes.txt'.
→ [Từ chối] / [Cho phép]

> Tìm file report trong ổ C rồi đọc nội dung
→ Đã tìm thấy: C:\Users\ngugi\Documents\report_q3.txt  (không cần xác nhận — SAFE)
  Nội dung: Báo cáo quý 3...

> Desktop của tôi ở D:\Desktop
→ 📌 Đã ghi nhớ: đường dẫn Desktop = D:\Desktop
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
| **Safety layer** | **Chặn + yêu cầu xác nhận trước khi chạy tool nguy hiểm** |

---

## Cài đặt

### Yêu cầu

- Windows 10/11
- Python 3.12+
- [Ollama](https://ollama.com/download)
- Không cần GPU — chạy hoàn toàn trên CPU

### 1. Cài Ollama và pull model

```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:0.5b
```

### 2. Cài thư viện Python

```bash
pip install -r requirements.txt
```

### 3. Chạy

```bash
python main.py          # giao diện desktop (mặc định)
python main.py chat "RAM còn bao nhiêu?"   # CLI một lệnh
python main.py repl     # vòng lặp chat CLI
```

> **Tối ưu CPU:** Set trước khi chạy `ollama serve` độc lập:
> ```bash
> set OLLAMA_FLASH_ATTENTION=1 && set OLLAMA_KV_CACHE_TYPE=q8_0 && ollama serve
> ```

### 4. Cấu hình (tuỳ chọn)

`config/settings.json`:

```json
{
  "planner_model": "qwen2.5:3b",
  "analyzer_model": "qwen2.5:0.5b",
  "num_ctx": 4096,
  "num_predict_planner": 256,
  "max_agent_steps": 10,
  "max_task_attempts": 3
}
```

---

## Phím tắt

| Phím tắt | Chức năng |
|----------|-----------|
| `Ctrl+Alt+J` | Bật / tắt Command Bar |
| `Ctrl+Alt+V` | Bật / tắt nhập giọng nói |
| `Esc` | Đóng bar (hoặc huỷ ghi âm) |
| `Enter` | Gửi lệnh |

---

## Safety Layer

Agent dùng model yếu (3B) nên có thể sinh lệnh sai. **Safety layer chặn tất cả tool nguy hiểm** và yêu cầu xác nhận trước khi thực thi — không tốn LLM token, chỉ dùng static rules + regex (O(1)).

### 4 mức rủi ro

| Mức | Icon | Ý nghĩa | Xác nhận? |
|-----|------|---------|-----------|
| `SAFE` | ✅ | Đọc-only, không thay đổi hệ thống | Không |
| `CAUTION` | ⚠️ | Side effect nhỏ, có thể hoàn tác | Không |
| `DANGEROUS` | 🔴 | Side effect đáng kể, khó hoàn tác | **Có** |
| `CRITICAL` | 🚨 | Phá hoại / cấp hệ thống | **Có (cảnh báo đỏ)** |

### Phân loại từng tool

| Tool | Mặc định | Ngoại lệ |
|------|----------|-----------|
| `get_system_info`, `get_running_processes`, `get_active_window` | ✅ SAFE | — |
| `get_clipboard`, `take_screenshot`, `send_notification` | ✅ SAFE | — |
| `search_file`, `read_file` | ✅ SAFE | — |
| `search_web`, `open_url` | ✅ SAFE | — |
| `open_app`, `set_clipboard`, `browser_action` | ⚠️ CAUTION | — |
| `write_file` (append=True) | ⚠️ CAUTION | — |
| `write_file` (append=False, overwrite) | 🔴 DANGEROUS | — |
| `write_file` (system path) | 🚨 CRITICAL | Path = `C:\Windows\`, `C:\System32\`... |
| `kill_process` | 🔴 DANGEROUS | — |
| `kill_process` (system proc) | 🚨 CRITICAL | `winlogon`, `lsass`, `csrss`... |
| `run_command` (read-only) | ✅ SAFE | `dir`, `ping`, `git status`, `pip list`... |
| `run_command` (thông thường) | 🔴 DANGEROUS | — |
| `run_command` (destructive) | 🚨 CRITICAL | `format`, `shutdown`, `rd /s`, `net user`... |

### Luồng xác nhận (GUI)

```
Worker thread                       Main thread (Qt)
─────────────────                   ─────────────────
Executor.run_one()
  → SafetyChecker.assess()
  → DANGEROUS detected
  → confirm_handler(assessment)
  → QTimer.singleShot(0, show_dlg)  ← schedule trên main thread
  → event.wait(timeout=30s) ─BLOCK─
                                     show_dlg() chạy:
                                       bar.show_bar()
                                       ConfirmDialog.exec() ← nested event loop
                                       user click OK/Cancel
                                       result[0] = True/False
                                       event.set()
  ← event.set() unblocks
  → result[0] = True → execute tool
  → result[0] = False → fail(retryable=False)
```

Timeout 30 giây → tự động từ chối (fail-safe).

CLI mode fallback: hỏi trực tiếp qua `input()` trong terminal.

---

## Cấu trúc thư mục

```
ai-desktop-agent/
├── main.py
│
├── agent/
│   ├── agent.py           # Agent Loop: điều phối pipeline
│   ├── task_analyzer.py   # Tách lệnh → TaskPlan (goal + subtasks)
│   ├── planner.py         # LLM → JSON action
│   ├── executor.py        # Thực thi tool + safety gate
│   ├── safety.py          # SafetyChecker: phân loại rủi ro tool (NEW)
│   ├── state.py           # AgentState
│   ├── memory.py          # SQLite: history, profile, long_term_memory
│   ├── memory_extractor.py
│   ├── llm.py
│   ├── stt_engine.py
│   ├── config.py
│   └── logger.py
│
├── tools/
│   ├── registry.py        # ToolSpec + TOOL_REGISTRY (16 tools)
│   ├── __init__.py
│   └── ... (16 tool files)
│
├── ui/
│   ├── app.py             # DesktopApp: wire safety confirmation
│   ├── command_bar.py     # Floating command bar
│   ├── confirm_dialog.py  # ConfirmDialog cho dangerous tools (NEW)
│   ├── worker.py          # AgentWorker (QThread)
│   ├── stt_worker.py
│   ├── hotkey.py
│   ├── tray.py
│   └── styles.py          # QSS + CONFIRM_DIALOG_STYLE (updated)
│
├── prompts/
├── config/settings.json
└── tests/
```

---

## Kiến trúc

```
Ctrl+Alt+J / Ctrl+Alt+V
        │
        ▼
 CommandBar (PySide6)
        │
        ▼
 AgentWorker (QThread, timeout 300s)
        │
        ▼
   Agent.run()
    ├─► Special query handler (nhớ gì / quên đi)
    ├─► TaskAnalyzer → qwen2.5:0.5b
    │    Fast-path: 1 task, không gọi LLM
    │    Multi-step: LLM tách → TaskPlan
    │
    └─► Agent Loop (max 10 bước)
         │
         ├─► Planner → qwen2.5:3b → JSON action
         │
         ├─► SafetyChecker.assess(tool, args)   ← ZERO LLM
         │    SAFE/CAUTION → thực thi ngay
         │    DANGEROUS/CRITICAL → block worker
         │         │
         │         └─► QTimer → main thread
         │              ConfirmDialog.exec()
         │              user: Cho phép / Từ chối
         │              event.set() → unblock
         │
         ├─► Executor.run_one() → TOOL_REGISTRY
         │
         └─► Observation → update state → repeat
              │
              ▼ xong
         Summary → Planner finish answer
              │
              ▼
    MemoryExtractor (background)
              │
              ▼
    CommandBar — hiển thị response
```

---

## Task Decomposition

`TaskAnalyzer` tự động tách lệnh phức thành subtasks:

**Fast-path** (không LLM): input 1 bước → 1 task, tiết kiệm 1 inference.

**LLM path** (`qwen2.5:0.5b`):
```json
{
  "goal": "Đọc file report",
  "tasks": [
    {"task": "Tìm file report", "type": "search", "hint": "search_file"},
    {"task": "Đọc nội dung", "type": "read", "hint": "read_file"}
  ]
}
```

---

## Dynamic Tool Selection

Thay vì luôn đẩy 16 tools vào prompt, Planner filter chỉ giữ tools phù hợp — không LLM.

| Trường hợp | Tools hiển thị | Tiết kiệm |
|------------|-----------------|----------|
| Single-step (fast-path) | 16 tools | 0% |
| Multi-step: search task | ~4 tools | ~75% |
| Multi-step: read task | ~6 tools | ~62% |
| Multi-step: action task | ~12 tools | ~25% |

---

## Long-term Memory

| Loại | Ví dụ |
|------|-------|
| `path` | "Desktop của tôi ở D:\Desktop" |
| `preference` | "Tôi dùng VS Code" |
| `schedule` | "Họp mỗi thứ Hai 9h" |
| `personal` | "Tên tôi là Nam" |

```
> Bạn còn nhớ gì về tôi?   — xem tất cả
> Quên đi rằng Desktop tôi  — xoá bộ nhớ
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Ollama — Qwen2.5 3B / 0.5B |
| STT | faster-whisper `base` (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite |
| Validation | Pydantic v2 |
| System APIs | pywin32, psutil |
| Browser control | pyautogui |
| Screenshot | Pillow |
| CLI | Typer + Rich |

---

## Roadmap

### Đã hoàn thành

- [x] Phase 1–10: MVP → Tool Registry → Desktop UX → LLM → Memory → Voice → Browser
- [x] Agent Loop: State, Observation, Stuck detection, Retry
- [x] Task Decomposition: TaskAnalyzer (multi-step → subtasks)
- [x] Dynamic Tool Selection: filter tools theo hint/type (zero LLM)
- [x] **Safety Layer: SafetyChecker + ConfirmDialog (4 risk levels, zero LLM)**

### Tiếp theo

- [ ] Phase 5 (PLAN.md) — OCR màn hình, click, type, key press
- [ ] Phase 7 (PLAN.md) — Coding Agent (project_tree, grep_code, apply_patch)