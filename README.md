# AI Desktop Agent

Một AI Agent chạy **hoàn toàn cục bộ** trên Windows, nhận lệnh ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) và thực thi trực tiếp trên hệ điều hành — không cần mở terminal, không cần thao tác chuột, không gửi dữ liệu ra ngoài internet.

> Gọi bằng **`Ctrl+Alt+J`** từ bất kỳ đâu trên màn hình.  
> Nhập lệnh bằng giọng nói bằng **`Ctrl+Alt+V`**.

---

## Demo nhanh

```
> RAM còn bao nhiêu?
→ RAM: 9.2 GB / 16 GB (57.5%). CPU: 12%. Ổ C còn 48 GB trống.

> Xem nội dung thư mục D:\projects
→ 📁 ai-desktop-agent/  [12/06 09:41]
  📁 flask-api/  [10/06 14:20]
  📄 notes.txt  1.2 KB  [11/06 20:03]
  (3 mục)

> Tắt Chrome đi
🔴 [NGUY HIỂM] kill_process("chrome.exe") → [Từ chối] / [Cho phép]

> OCR màn hình xem có gì
→ [OCR toàn màn hình] — trả về toàn bộ text đang hiển thị

> Click vào nút OK ở giữa màn hình
🔴 [NGUY HIỂM] mouse_click("960") → [Từ chối] / [Cho phép]

> Gõ "Xin chào" vào ô đang focus
🔴 [NGUY HIỂM] type_text("Xin chào") → [Từ chối] / [Cho phép]
```

---

## Tính năng

| Nhóm | Tools |
|------|-------|
| **App control** | `open_app`, `kill_process` |
| **File system** | `search_file`, `read_file`, `write_file`, `list_directory`, `manage_file_folder`, `compress_decompress` |
| **GUI Automation** ✨ | `screen_ocr`, `mouse_click`, `type_text`, `key_press`, `get_screen_size` |
| **System** | `get_system_info`, `get_running_processes`, `get_active_window` |
| **Shell** | `run_command` |
| **Clipboard** | `get_clipboard`, `set_clipboard` |
| **Screen** | `take_screenshot`, `send_notification` |
| **Browser** | `open_url`, `search_web`, `web_search`, `web_read`, `get_weather`, `browser_action` |
| **Agent features** | Task decomposition, Long-term memory, Voice input, Safety layer |

**Tổng cộng: 27 tools**

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

### 3. (Tuỳ chọn) Cài Tesseract cho `screen_ocr`

`screen_ocr` yêu cầu Tesseract OCR binary (ngoài `pytesseract`):

1. Tải từ [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Cài đặt và thêm vào PATH (hoặc set biến môi trường `TESSDATA_PREFIX`)

Nếu chưa cài, các tool khác vẫn hoạt động bình thường — chỉ `screen_ocr` báo lỗi.

### 4. Chạy

```bash
python main.py          # giao diện desktop (mặc định)
python main.py chat "RAM còn bao nhiêu?"   # CLI một lệnh
python main.py repl     # vòng lặp chat CLI
```

> **Tối ưu CPU:** Set trước khi chạy `ollama serve`:
> ```bash
> set OLLAMA_FLASH_ATTENTION=1 && set OLLAMA_KV_CACHE_TYPE=q8_0 && ollama serve
> ```

### 5. Cấu hình (tuỳ chọn)

`config/settings.json`:

```json
{
  "planner_model": "qwen2.5:3b",
  "analyzer_model": "qwen2.5:0.5b",
  "num_ctx": 8192,
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

Agent dùng model nhỏ (3B) nên có thể sinh lệnh sai. **Safety layer chặn tất cả tool nguy hiểm** và yêu cầu xác nhận — không tốn LLM token, chỉ dùng static rules + regex (O(1)).

### 4 mức rủi ro

| Mức | Icon | Ý nghĩa | Xác nhận? |
|-----|------|---------|-----------|
| `SAFE` | ✅ | Đọc-only, không thay đổi hệ thống | Không |
| `CAUTION` | ⚠️ | Side effect nhỏ, có thể hoàn tác | Không |
| `DANGEROUS` | 🔴 | Side effect đáng kể, khó hoàn tác | **Có** |
| `CRITICAL` | 🚨 | Phá hoại / cấp hệ thống | **Có (cảnh báo đỏ)** |

### Phân loại tool

| Tool | Mức | Ghi chú |
|------|-----|---------|
| `get_system_info`, `get_running_processes`, `get_active_window` | ✅ SAFE | |
| `get_clipboard`, `take_screenshot`, `send_notification` | ✅ SAFE | |
| `search_file`, `read_file`, `list_directory` | ✅ SAFE | |
| `search_web`, `open_url`, `web_search`, `web_read`, `get_weather` | ✅ SAFE | |
| `screen_ocr`, `get_screen_size` | ✅ SAFE | Đọc màn hình, không tương tác |
| `open_app`, `set_clipboard`, `browser_action` | ⚠️ CAUTION | |
| `manage_file_folder` (`copy`, `create_folder`) | ⚠️ CAUTION | |
| `compress_decompress` (`zip`) | ⚠️ CAUTION | |
| `write_file` (append=True) | ⚠️ CAUTION | |
| `mouse_click`, `type_text`, `key_press` | 🔴 DANGEROUS | Luôn cần xác nhận |
| `write_file` (overwrite) | 🔴 DANGEROUS | |
| `manage_file_folder` (`move`, `delete`, `rename`) | 🔴 DANGEROUS | |
| `compress_decompress` (`unzip`) | 🔴 DANGEROUS | Có thể ghi đè file |
| `kill_process` | 🔴 DANGEROUS | |
| `run_command` (thông thường) | 🔴 DANGEROUS | |
| `write_file` (system path) | 🚨 CRITICAL | |
| `kill_process` (system process) | 🚨 CRITICAL | `winlogon`, `lsass`... |
| `run_command` (destructive) | 🚨 CRITICAL | `format`, `shutdown`, `rd /s`... |

---

## GUI Automation

Agent có thể **nhìn thấy và điều khiển** bất kỳ ứng dụng nào trên màn hình — không cần API.

### Workflow điển hình

```
[Mục tiêu] Điền form trong Chrome

1. screen_ocr()              → đọc text trên màn hình, tìm vị trí ô input
2. mouse_click(x=480, y=320) → click vào ô "Họ tên" [CẦN XÁC NHẬN]
3. type_text("Nguyễn Văn A") → gõ tên [CẦN XÁC NHẬN]
4. key_press("tab")          → chuyển sang ô tiếp theo [CẦN XÁC NHẬN]
5. type_text("0912345678")   → gõ số điện thoại [CẦN XÁC NHẬN]
6. key_press("enter")        → submit form [CẦN XÁC NHẬN]
```

### Fail-safe

`pyautogui` có cơ chế dừng khẩn cấp: **di chuột đến góc trên-trái màn hình** để dừng ngay.

---

## Cấu trúc thư mục

```
ai-desktop-agent/
├── main.py
│
├── agent/
│   ├── agent.py           # Agent Loop: điều phối pipeline
│   ├── task_analyzer.py   # Tách lệnh → TaskPlan (goal + subtasks)
│   ├── planner.py         # Ollama native tool calling → action
│   ├── executor.py        # Thực thi tool + safety gate
│   ├── safety.py          # SafetyChecker: phân loại rủi ro (zero LLM)
│   ├── state.py           # AgentState
│   ├── memory.py          # SQLite: history, profile, long_term_memory
│   ├── memory_extractor.py
│   ├── llm.py
│   ├── stt_engine.py
│   ├── config.py
│   └── logger.py
│
├── tools/
│   ├── registry.py           # ToolSpec + TOOL_REGISTRY (27 tools)
│   ├── gui_automation.py     # ✨ screen_ocr, mouse_click, type_text, key_press, get_screen_size
│   ├── list_directory.py     # ✨ list_directory
│   ├── manage_file_folder.py # copy, move, delete, rename, create_folder
│   ├── compress_decompress.py# zip, unzip
│   ├── web_search.py         # DuckDuckGo (no API key)
│   ├── web_read.py           # Đọc URL + Jina AI fallback
│   ├── get_weather.py        # wttr.in API (no API key)
│   └── ... (20 tool files tổng)
│
├── ui/
│   ├── app.py             # DesktopApp: wire safety confirmation
│   ├── command_bar.py     # Floating command bar
│   ├── confirm_dialog.py  # ConfirmDialog cho dangerous tools
│   ├── worker.py          # AgentWorker (QThread)
│   ├── stt_worker.py
│   ├── hotkey.py
│   ├── tray.py
│   └── styles.py
│
├── prompts/
├── config/settings.json
└── tests/
```

---

## Kiến trúc pipeline

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
         ├─► Planner → qwen2.5:3b (Ollama native tool calling)
         │    tools=[27 JSON schemas] → model trả tool_calls
         │    Dynamic filter: chỉ gửi subset tools phù hợp
         │
         ├─► SafetyChecker.assess(tool, args)   ← ZERO LLM, O(1)
         │    SAFE/CAUTION → thực thi ngay
         │    DANGEROUS/CRITICAL → block worker thread
         │         │
         │         └─► QTimer → main thread
         │              ConfirmDialog.exec()
         │              user: Cho phép / Từ chối (timeout 30s)
         │              event.set() → unblock
         │
         ├─► Executor.run_one() → TOOL_REGISTRY[tool_name](args)
         │
         └─► Observation → update state → repeat
              │
              ▼ xong
         Summary → Planner finish answer
              │
              ▼
    MemoryExtractor (background, qwen2.5:0.5b)
              │
              ▼
    CommandBar — hiển thị response
```

---

## Công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| LLM | Ollama — Qwen2.5 3B (planner) / Qwen2.5 0.5B (analyzer, response) |
| STT | faster-whisper `base` (local, vi + en) |
| UI | PySide6 (Qt6) |
| Database | SQLite |
| Validation | Pydantic v2 |
| Web search | ddgs (DuckDuckGo, no API key) |
| Web read | requests + beautifulsoup4 + Jina AI Reader fallback |
| Weather | wttr.in (no API key) |
| System APIs | pywin32, psutil |
| GUI automation | pyautogui + pytesseract (OCR) |
| Screenshot | Pillow |
| File ops | send2trash (recycle bin), shutil, zipfile |
| CLI | Typer + Rich |

---

## Roadmap

### Đã hoàn thành

- [x] Agent Loop: State, Observation, Stuck detection, Retry
- [x] Task Decomposition: TaskAnalyzer (multi-step → subtasks, fast-path)
- [x] Dynamic Tool Selection: filter tools theo hint/type (zero LLM)
- [x] Safety Layer: SafetyChecker + ConfirmDialog (4 risk levels, zero LLM)
- [x] Web: DuckDuckGo search, URL reader, Jina AI fallback, wttr.in weather
- [x] Native Tool Calling: Ollama tools API — system prompt ~150 token
- [x] Long-term Memory: SQLite, MemoryExtractor
- [x] Voice Input: faster-whisper (vi + en)
- [x] **File Power Tools: `list_directory`, `manage_file_folder`, `compress_decompress`**
- [x] **GUI Automation: `screen_ocr`, `mouse_click`, `type_text`, `key_press`, `get_screen_size`**

### Tiếp theo

- [ ] Streaming output — hiện text real-time trong UI thay vì chờ toàn bộ
- [ ] Follow-up context — nhận diện câu hỏi liên tiếp, inject last_response
- [ ] Phase 7: Coding Agent — `project_tree`, `grep_code`, `apply_patch`
