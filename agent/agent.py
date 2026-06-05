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

        # ── Task Analyzer: tách goal thành subtask list ────────────────────
        plan = self.analyzer.analyze(goal)
        state = AgentState(
            goal=plan.goal,
            tasks=[t.model_dump() for t in plan.tasks],
        )
        state.user_name = self._get_user_name()
        log.info(
            "[Agent] goal=%r | tasks=%d: %s",
            plan.goal,
            len(plan.tasks),
            [t.task for t in plan.tasks],
        )
        # ──────────────────────────────────────────────────────────────────

        while state.step_count < max_steps:

            # Tất cả tasks đã xong → planner tổng kết lần cuối
            if state.has_tasks and state.all_tasks_done():
                log.info("[Loop] Tất cả tasks done — yêu cầu finish")
                break

            action = self.planner.plan_step(state)
            state.step_count += 1

            log.info(
                "[Loop] step=%d/%d type=%s tool=%s task_idx=%s",
                state.step_count, max_steps,
                action.get("type"), action.get("tool", "–"),
                state.current_task_index if state.has_tasks else "–",
            )

            # ── Planner trả "finish" ──────────────────────────────────────
            if action.get("type") == "finish":
                if state.has_tasks and not state.all_tasks_done():
                    # Planner cho rằng task hiện tại xong
                    state.mark_current_task_done()
                    if state.all_tasks_done():
                        return action.get("answer", "Xong.")
                    # Còn tasks → tiếp tục loop, xoá observation cũ
                    state.observation = ""
                    continue
                return action.get("answer", "Xong.")

            # ── Thực thi tool ─────────────────────────────────────────────
            result = self.executor.run_one(action)
            obs = self._make_observation(result)
            state.history.append({"action": action, "observation": obs})
            state.observation = obs

            # ── Xử lý kết quả theo retryable + attempts ───────────────────
            if result.get("success", True):
                # Tool thành công → đánh dấu task done
                if state.has_tasks:
                    log.info(
                        "[Loop] Task done: %r",
                        state.current_task,
                    )
                    state.mark_current_task_done()
                    state.observation = ""  # xoá obs cũ tránh nhiễu task sau

            elif not result.get("retryable", True):
                # Lỗi vĩnh viễn (app không tồn tại, invalid args...)
                log.warning(
                    "[Loop] Task failed (non-retryable): %r — %s",
                    state.current_task, obs,
                )
                if state.has_tasks:
                    state.mark_current_task_failed()
                # Planner sẽ thấy observation lỗi và trả finish

            else:
                # Lỗi tạm thời (retryable=True) → tăng attempts
                attempts = state.increment_task_attempts()
                log.warning(
                    "[Loop] Task retry %d/%d: %r",
                    attempts, max_attempts, state.current_task,
                )
                if attempts >= max_attempts:
                    log.warning(
                        "[Loop] Task vượt MAX_ATTEMPTS=%d — đánh dấu failed",
                        max_attempts,
                    )
                    if state.has_tasks:
                        state.mark_current_task_failed()

        # ── Hết loop: yêu cầu planner tổng kết ───────────────────────────
        if state.step_count >= max_steps:
            log.warning("[Loop] Vượt MAX_STEPS=%d", max_steps)
            return "Tôi đã thử nhiều bước nhưng chưa hoàn thành được yêu cầu."

        # Tất cả tasks done — inject summary để planner tổng kết chính xác hơn
        if state.has_tasks:
            done = [t["task"] for t in state.tasks if t["status"] == "done"]
            failed = [t["task"] for t in state.tasks if t["status"] == "failed"]
            parts: list[str] = []
            if done:
                parts.append("Completed: " + "; ".join(done))
            if failed:
                parts.append("Failed: " + "; ".join(failed))
            if parts:
                state.observation = " | ".join(parts)

        action = self.planner.plan_step(state)
        return action.get("answer", "Xong.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_user_name(self) -> str:
        """Lấy tên người dùng từ profile, trả về chuỗi rỗng nếu chưa có."""
        try:
            return self.memory.get_user_profile().get("display_name", "")
        except Exception:
            return ""

    def _make_observation(self, result: dict) -> str:
        """Chuyển tool result thành chuỗi observation ngắn gọn."""
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
