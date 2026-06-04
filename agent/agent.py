"""Agent — pipeline điều phối Planner → Executor → ResponseFormatter."""
from __future__ import annotations

import re

from agent.config import load_prompt_file, load_settings
from agent.executor import Executor
from agent.llm import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaServerError,
    get_response_llm,
)
from agent.logger import get_logger
from agent.memory import Memory
from agent.memory_extractor import MemoryExtractor
from agent.planner import Planner

log = get_logger(__name__)

# Giới hạn tool result để tránh gửi quá nhiều token (vd: list_dir hàng trăm dòng)
_RAW_SUMMARY_MAX = 1500

_REMEMBER_PATTERNS = [
    r"bạn (còn )?nhớ gì (về tôi|về mình)",
    r"nhớ gì về tôi",
    r"bạn biết gì về tôi",
    r"bạn đang nhớ gì",
]
_FORGET_PATTERNS = [
    r"quên đi rằng\s+(.+)",
    r"xoá nhớ\s+(.+)",
    r"xóa nhớ\s+(.+)",
    r"hãy quên\s+(.+)",
    r"forget\s+(.+)",
]


class Agent:
    def __init__(self) -> None:
        self.memory = Memory()
        self.planner = Planner()
        self.planner.set_memory(self.memory)
        self.executor = Executor()
        self.extractor = MemoryExtractor(self.memory)
        self._llm: OllamaClient | None = None

        # Callback để CommandBar hiển thị thông báo "Đã ghi nhớ"
        # Được gán từ app.py: agent.on_memory_saved = ...
        self.on_memory_saved: callable | None = None

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_response_llm()
        return self._llm

    # ── Public API ────────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        log.debug("[Agent] Yêu cầu: %r", user_input)
        try:
            self.memory.save_message("user", user_input)

            # Xử lý đặc biệt: truy vấn / xoá bộ nhớ
            special = self._handle_special_queries(user_input)
            if special is not None:
                self.memory.save_message("assistant", special)
                return special

            s = load_settings()
            history_limit = s.get("history_limit", 6)
            history = self.memory.get_recent_history(limit=history_limit)
            plan = self.planner.plan(user_input, history)

            if self._is_fallback_plan(plan):
                response = self._conversational_response(user_input)
            else:
                results = self.executor.execute(plan)
                response = self._format_response(user_input, results)

            self.memory.save_message("assistant", response)

            # Kích hoạt trích xuất bộ nhớ bất đồng bộ
            self.extractor.extract_async(
                user_input,
                response,
                on_saved=self._on_memory_saved_callback,
            )

            return response

        except OllamaConnectionError:
            log.warning("[Agent] Ollama không kết nối.")
            return (
                "Ollama chưa chạy. Hãy mở terminal và chạy lệnh:\n"
                "`ollama serve`"
            )

        except OllamaModelNotFoundError as e:
            log.warning("[Agent] Model không tồn tại: %s", e.model)
            return (
                f"Model '{e.model}' chưa được tải về. "
                f"Hãy mở terminal và chạy:\n"
                f"`ollama pull {e.model}`"
            )

        except OllamaServerError:
            log.warning("[Agent] Ollama server error.")
            return "Ollama gặp lỗi khi xử lý. Vui lòng thử lại sau giây lát."

        except Exception as e:
            log.warning("[Agent] Lỗi không xác định: %s", e)
            raise

    # ── Special query handlers ─────────────────────────────────────────

    def _handle_special_queries(self, user_input: str) -> str | None:
        text = user_input.lower().strip()

        for pattern in _REMEMBER_PATTERNS:
            if re.search(pattern, text):
                return self._list_memories()

        for pattern in _FORGET_PATTERNS:
            m = re.search(pattern, text)
            if m:
                return self._forget_memory(m.group(1).strip())

        return None

    def _list_memories(self) -> str:
        memories = self.memory.get_all_long_term_memories()
        if not memories:
            return "Tôi chưa lưu thông tin gì về bạn."
        groups: dict[str, list[dict]] = {}
        for m in memories:
            groups.setdefault(m["type"], []).append(m)
        type_labels = {
            "path": "📁 Đường dẫn",
            "preference": "⭐ Ưa thích",
            "schedule": "📅 Lịch trình",
            "personal": "👤 Cá nhân",
        }
        lines = ["Đây là những gì tôi nhớ về bạn:\n"]
        for t, items in groups.items():
            lines.append(f"{type_labels.get(t, t.upper())}:")
            for item in items:
                lines.append(f"  • {item['key']}: {item['value']}")
        return "\n".join(lines)

    def _forget_memory(self, search_term: str) -> str:
        key = self.memory.deactivate_long_term_memory(search_term)
        if key:
            return f"Đã xoá bộ nhớ: {key}"
        return f"Không tìm thấy bộ nhớ liên quan đến: {search_term}"

    # ── Response helpers ───────────────────────────────────────────────

    def _is_fallback_plan(self, plan: list[dict]) -> bool:
        if not plan:
            return True
        return (
            len(plan) == 1
            and plan[0].get("task") == "handle_request"
            and not plan[0].get("tool")
        )

    def _conversational_response(self, user_input: str) -> str:
        try:
            settings = load_settings()
            system_prompt = load_prompt_file(settings["agent_prompt"])
            system_prompt = self._enrich_system_prompt(system_prompt)
            num_predict = settings.get("num_predict_response", 512)
            caveman = settings.get("caveman_mode", True)
            return self._get_llm().generate(
                system_prompt, user_input,
                num_predict=num_predict,
                caveman=caveman,
            )
        except (OllamaConnectionError, OllamaModelNotFoundError, OllamaServerError):
            raise
        except Exception as e:
            log.warning("[Agent] _conversational_response lỗi: %s", e)
            return f"Xin lỗi, tôi gặp lỗi khi xử lý: {e}"

    def _format_response(self, user_input: str, results: list[dict]) -> str:
        raw_lines = [r.get("message", "") for r in results if r.get("message")]
        raw_summary = "\n".join(raw_lines) if raw_lines else "(Không có kết quả)"

        # Cắt tool output dài (vd: list_dir, grep) để tiết kiệm token
        if len(raw_summary) > _RAW_SUMMARY_MAX:
            raw_summary = raw_summary[:_RAW_SUMMARY_MAX] + "\n…(truncated)"

        try:
            settings = load_settings()
            system_prompt = load_prompt_file(settings["agent_prompt"])
            system_prompt = self._enrich_system_prompt(system_prompt)
            num_predict = settings.get("num_predict_response", 512)
            caveman = settings.get("caveman_mode", True)
            user_message = (
                f"Req: {user_input}\n\n"
                f"Results:\n{raw_summary}\n\n"
                f"Summarize in Vietnamese."
            )
            return self._get_llm().generate(
                system_prompt, user_message,
                num_predict=num_predict,
                caveman=caveman,
            )
        except (OllamaConnectionError, OllamaModelNotFoundError, OllamaServerError):
            raise
        except Exception as e:
            log.warning("[Agent] _format_response fallback: %s", e)
            return raw_summary

    def _enrich_system_prompt(self, prompt: str) -> str:
        """Thêm tên người dùng vào system prompt nếu đã biết."""
        try:
            profile = self.memory.get_user_profile()
            name = profile.get("display_name", "")
            if name:
                prompt = f"Tên người dùng là: {name}\n\n" + prompt
        except Exception:
            pass
        return prompt

    # ── Callback ───────────────────────────────────────────────────────

    def _on_memory_saved_callback(self, saved_items: list[dict]) -> None:
        if self.on_memory_saved:
            try:
                self.on_memory_saved(saved_items)
            except Exception:
                pass
