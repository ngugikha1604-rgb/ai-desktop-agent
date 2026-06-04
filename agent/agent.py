"""Agent — điều phối Agent Loop: Planner → Tool → Observation → repeat."""
from __future__ import annotations

import re

from agent.config import load_settings
from agent.executor import Executor
from agent.llm import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaServerError,
)
from agent.logger import get_logger
from agent.memory import Memory
from agent.memory_extractor import MemoryExtractor
from agent.planner import Planner
from agent.state import AgentState

log = get_logger(__name__)

_OBS_MAX = 400  # ký tự tối đa của observation lưu vào state

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

        # Callback để CommandBar hiển thị "📌 Đã ghi nhớ"
        self.on_memory_saved: callable | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        log.debug("[Agent] Input: %r", user_input)
        try:
            self.memory.save_message("user", user_input)

            # Xử lý đặc biệt: xem / xoá bộ nhớ
            special = self._handle_special_queries(user_input)
            if special is not None:
                self.memory.save_message("assistant", special)
                return special

            # Agent loop chính
            response = self._run_loop(user_input)

            self.memory.save_message("assistant", response)
            self.extractor.extract_async(
                user_input, response,
                on_saved=self._on_memory_saved_callback,
            )
            return response

        except OllamaConnectionError:
            return (
                "Ollama chưa chạy. Hãy mở terminal và chạy:\n"
                "`ollama serve`"
            )
        except OllamaModelNotFoundError as e:
            return (
                f"Model '{e.model}' chưa được tải về.\n"
                f"Hãy chạy: `ollama pull {e.model}`"
            )
        except OllamaServerError:
            return "Ollama gặp lỗi. Vui lòng thử lại."
        except Exception as e:
            log.warning("[Agent] Lỗi không xác định: %s", e)
            raise

    # ── Agent Loop ────────────────────────────────────────────────────────────

    def _run_loop(self, goal: str) -> str:
        s = load_settings()
        max_steps = s.get("max_agent_steps", 10)

        state = AgentState(goal=self._enrich_goal(goal))

        while state.step_count < max_steps:
            action = self.planner.plan_step(state)
            state.step_count += 1

            log.info(
                "[Loop] step=%d/%d type=%s tool=%s",
                state.step_count, max_steps,
                action.get("type"), action.get("tool", "–"),
            )

            # Planner quyết định xong → trả kết quả
            if action.get("type") == "finish":
                return action.get("answer", "Xong.")

            # Thực thi tool
            result = self.executor.run_one(action)
            obs = self._make_observation(result)

            state.history.append({"action": action, "observation": obs})
            state.observation = obs

        log.warning("[Loop] Vượt MAX_STEPS=%d", max_steps)
        return "Tôi đã thử nhiều bước nhưng chưa hoàn thành được yêu cầu."

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _enrich_goal(self, goal: str) -> str:
        """Thêm tên người dùng vào goal nếu đã biết."""
        try:
            name = self.memory.get_user_profile().get("display_name", "")
            if name:
                return f"[User: {name}] {goal}"
        except Exception:
            pass
        return goal

    def _make_observation(self, result: dict) -> str:
        """Chuyển tool result thành chuỗi observation ngắn."""
        msg = result.get("message", "")
        if not result.get("success", True):
            msg = f"FAILED: {msg}"
        if len(msg) > _OBS_MAX:
            msg = msg[:_OBS_MAX] + "…"
        return msg

    # ── Special query handlers ────────────────────────────────────────────────

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
        return f"Không tìm thấy bộ nhớ: {search_term}"

    # ── Callback ──────────────────────────────────────────────────────────────

    def _on_memory_saved_callback(self, saved_items: list[dict]) -> None:
        if self.on_memory_saved:
            try:
                self.on_memory_saved(saved_items)
            except Exception:
                pass
