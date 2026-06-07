"""Agent — điều phối Agent Loop: Planner → Tool → Observation → repeat."""
from __future__ import annotations

import re
from typing import Callable

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
from agent.task_analyzer import TaskAnalyzer

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
        self.analyzer = TaskAnalyzer()
        self.planner = Planner()
        self.planner.set_memory(self.memory)
        self.executor = Executor()
        self.extractor = MemoryExtractor(self.memory)
        self.on_memory_saved: Callable | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        log.debug("[Agent] Input: %r", user_input)
        try:
            self.memory.save_message("user", user_input)

            special = self._handle_special_queries(user_input)
            if special is not None:
                self.memory.save_message("assistant", special)
                return special

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
        max_attempts = s.get("max_task_attempts", 3)

        plan = self.analyzer.analyze(goal)
        state = AgentState(
            goal=plan.goal,
            tasks=[t.model_dump() for t in plan.tasks],
        )
        state.user_name = self._get_user_name()
        log.info(
            "[Agent] goal=%r | tasks=%d: %s",
            plan.goal, len(plan.tasks),
            [t.task for t in plan.tasks],
        )

        while state.step_count < max_steps:

            # Tất cả tasks xong → thoát để tổng kết
            if state.has_tasks and state.all_tasks_done():
                log.info("[Loop] Tất cả tasks done — thoát để tổng kết")
                break

            action = self.planner.plan_step(state)
            state.step_count += 1

            log.info(
                "[Loop] step=%d/%d type=%s tool=%s task=%s",
                state.step_count, max_steps,
                action.get("type"), action.get("tool", "–"),
                state.current_task_index if state.has_tasks else "–",
            )

            # ── Planner trả finish ────────────────────────────────────────
            if action.get("type") == "finish":
                if state.has_tasks and not state.all_tasks_done():
                    # Task hiện tại xong, còn task tiếp theo
                    state.mark_current_task_done()
                    if state.all_tasks_done():
                        return action.get("answer", "Xong.")
                    # Xóa observation cũ để không nhiễu sang task sau
                    state.observation = ""
                    continue
                return action.get("answer", "Xong.")

            # ── Thực thi tool ─────────────────────────────────────────────
            result = self.executor.run_one(action)
            obs = self._make_observation(result)
            state.history.append({"action": action, "observation": obs})
            state.observation = obs

            if result.get("success", True):
                if state.has_tasks:
                    log.info("[Loop] Task done: %r", state.current_task)
                    state.mark_current_task_done()
                    # Chỉ xóa observation khi còn task tiếp theo
                    # (giữ lại nếu đây là task cuối để dùng cho tổng kết)
                    if not state.all_tasks_done():
                        state.observation = ""

            elif not result.get("retryable", True):
                log.warning(
                    "[Loop] Non-retryable fail: %r — %s",
                    state.current_task, obs,
                )
                if state.has_tasks:
                    state.mark_current_task_failed()

            else:
                attempts = state.increment_task_attempts()
                log.warning(
                    "[Loop] Retry %d/%d: %r", attempts, max_attempts, state.current_task,
                )
                if attempts >= max_attempts:
                    log.warning("[Loop] MAX_ATTEMPTS=%d — đánh dấu failed", max_attempts)
                    if state.has_tasks:
                        state.mark_current_task_failed()

        # ── Kết thúc loop ─────────────────────────────────────────────────
        if state.step_count >= max_steps:
            log.warning("[Loop] Vượt MAX_STEPS=%d", max_steps)
            return "Tôi đã thử nhiều bước nhưng chưa hoàn thành được yêu cầu."

        # Tổng kết: build observation từ history thực tế (không chỉ task names)
        state.observation = self._build_summary_obs(state)
        log.debug("[Loop] Summary obs: %r", state.observation[:100])

        # Yêu cầu planner tổng kết — force finish nếu planner bị confused
        action = self.planner.plan_step(state)
        if action.get("type") == "finish":
            return action.get("answer", "Xong.")

        # Planner trả tool action thay vì finish → fallback tự tổng kết
        log.warning("[Loop] Planner trả tool thay vì finish khi tổng kết — dùng obs trực tiếp")
        return state.observation or "Đã hoàn thành yêu cầu."

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_summary_obs(self, state: AgentState) -> str:
        """Tổng hợp kết quả từ history thực tế để planner tổng kết chính xác.

        Lấy các observation thành công (không bắt đầu bằng FAILED:)
        từ history, kèm danh sách tasks failed nếu có.
        """
        successful_obs = [
            h["observation"]
            for h in state.history
            if not h["observation"].startswith("FAILED:")
        ]

        parts: list[str] = []
        if successful_obs:
            # Lấy tối đa 3 kết quả gần nhất, mỗi cái tối đa 150 chars
            trimmed = [o[:150] for o in successful_obs[-3:]]
            parts.append("Results: " + " | ".join(trimmed))

        if state.has_tasks:
            failed = [t["task"] for t in state.tasks if t["status"] == "failed"]
            if failed:
                parts.append("Failed: " + "; ".join(failed))

        return " ".join(parts) if parts else ""

    def _get_user_name(self) -> str:
        try:
            return self.memory.get_user_profile().get("display_name", "")
        except Exception:
            return ""

    def _make_observation(self, result: dict) -> str:
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

    def _on_memory_saved_callback(self, saved_items: list[dict]) -> None:
        if self.on_memory_saved:
            try:
                self.on_memory_saved(saved_items)
            except Exception:
                pass
