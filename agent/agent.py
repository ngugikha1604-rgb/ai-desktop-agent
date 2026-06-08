"""Agent — điều phối Agent Loop: Planner → Tool → Observation → repeat."""
from __future__ import annotations

import json
import re
import time
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

_OBS_MAX   = 400   # ký tự tối đa của observation lưu vào state
_OBS_LOG   = 120   # ký tự tối đa khi in observation ra log

# Visual separators — dùng lại nhiều chỗ
_SEP  = "═" * 54          # phân cách giữa các request
_STEP = "  ┄ " + "─" * 46 # phân cách giữa các step trong loop

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
        self.memory    = Memory()
        self.analyzer  = TaskAnalyzer()
        self.planner   = Planner()
        self.planner.set_memory(self.memory)
        self.executor  = Executor()
        self.extractor = MemoryExtractor(self.memory)
        self.on_memory_saved: Callable | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, user_input: str) -> str:
        t0 = time.perf_counter()

        log.info(_SEP)
        log.info('▶  "%s"', user_input)

        try:
            self.memory.save_message("user", user_input)

            special = self._handle_special_queries(user_input)
            if special is not None:
                self.memory.save_message("assistant", special)
                self._log_done(t0)
                return special

            response = self._run_loop(user_input)

            self.memory.save_message("assistant", response)
            self.extractor.extract_async(
                user_input, response,
                on_saved=self._on_memory_saved_callback,
            )
            self._log_done(t0)
            return response

        except OllamaConnectionError:
            log.warning("  ✗  Ollama chưa chạy")
            self._log_done(t0, ok=False)
            return (
                "Ollama chưa chạy. Hãy mở terminal và chạy:\n"
                "`ollama serve`"
            )
        except OllamaModelNotFoundError as e:
            log.warning("  ✗  Model '%s' chưa tải về", e.model)
            self._log_done(t0, ok=False)
            return (
                f"Model '{e.model}' chưa được tải về.\n"
                f"Hãy chạy: `ollama pull {e.model}`"
            )
        except OllamaServerError:
            log.warning("  ✗  Ollama server error")
            self._log_done(t0, ok=False)
            return "Ollama gặp lỗi. Vui lòng thử lại."
        except Exception as e:
            log.warning("  ✗  Lỗi không xác định: %s", e)
            self._log_done(t0, ok=False)
            raise

    # ── Agent Loop ────────────────────────────────────────────────────────────

    def _run_loop(self, goal: str) -> str:
        s           = load_settings()
        max_steps   = s.get("max_agent_steps", 10)
        max_attempts = s.get("max_task_attempts", 3)

        # ── Task analysis ─────────────────────────────────────────────────
        plan  = self.analyzer.analyze(goal)
        state = AgentState(
            goal=plan.goal,
            tasks=[t.model_dump() for t in plan.tasks],
        )
        state.user_name = self._get_user_name()

        task_names = [t.task for t in plan.tasks]
        log.info("  \u26a1  analyze   %d task(s): %s", len(plan.tasks), task_names)

        # ── Main loop ─────────────────────────────────────────────────────
        while state.step_count < max_steps:

            if state.has_tasks and state.all_tasks_done():
                break

            # ── Plan ──────────────────────────────────────────────────────
            log.info(_STEP)
            t_plan = time.perf_counter()
            action = self.planner.plan_step(state)
            elapsed_plan = time.perf_counter() - t_plan
            state.step_count += 1

            a_type = action.get("type")
            a_tool = action.get("tool", "")
            a_args = action.get("args") or {}

            if a_type == "tool":
                log.info(
                    "  🧠  plan     → %s(%s)  %.1fs",
                    a_tool,
                    json.dumps(a_args, ensure_ascii=False),
                    elapsed_plan,
                )
            else:
                log.info(
                    "  🧠  plan     → finish  %.1fs", elapsed_plan,
                )

            # ── Finish từ planner ─────────────────────────────────────────
            if a_type == "finish":
                answer = action.get("answer", "Xong.")
                log.info('  ✅  answer   → "%s"', answer[:100])
                if state.has_tasks and not state.all_tasks_done():
                    state.mark_current_task_done()
                    if state.all_tasks_done():
                        return answer
                    state.observation = ""
                    continue
                return answer

            # ── Execute tool ──────────────────────────────────────────────
            t_exec = time.perf_counter()
            result = self.executor.run_one(action)
            elapsed_exec = time.perf_counter() - t_exec

            obs = self._make_observation(result)
            state.history.append({"action": action, "observation": obs})
            state.observation = obs

            if result.get("success", True):
                log.info(
                    "  ⚙   exec     → ✓ %s  %.1fs",
                    obs[:_OBS_LOG],
                    elapsed_exec,
                )
                if state.has_tasks:
                    log.info("  ✔   task     done: %r", state.current_task)
                    state.mark_current_task_done()
                    if not state.all_tasks_done():
                        state.observation = ""

            elif not result.get("retryable", True):
                log.warning(
                    "  ⚙   exec     → ✗ %s  %.1fs",
                    obs[:_OBS_LOG],
                    elapsed_exec,
                )
                log.warning("  ✘   task     failed (non-retryable): %r", state.current_task)
                if state.has_tasks:
                    state.mark_current_task_failed()

            else:
                attempts = state.increment_task_attempts()
                log.warning(
                    "  ⚙   exec     → ✗ %s  %.1fs",
                    obs[:_OBS_LOG],
                    elapsed_exec,
                )
                log.warning(
                    "  ↺   retry    %d/%d: %r", attempts, max_attempts, state.current_task,
                )
                if attempts >= max_attempts:
                    log.warning("  ✘   task     max attempts → failed: %r", state.current_task)
                    if state.has_tasks:
                        state.mark_current_task_failed()

        # ── Kết thúc loop ─────────────────────────────────────────────────
        if state.step_count >= max_steps:
            log.warning("  ✘  vượt max_steps=%d", max_steps)
            return "Tôi đã thử nhiều bước nhưng chưa hoàn thành được yêu cầu."

        # ── Summary call ──────────────────────────────────────────────────
        state.observation = self._build_summary_obs(state)
        log.info(_STEP)
        log.debug("  obs      → %s", state.observation[:_OBS_LOG])

        t_sum = time.perf_counter()
        action = self.planner.plan_step(state)
        elapsed_sum = time.perf_counter() - t_sum

        if action.get("type") == "finish":
            answer = action.get("answer", "Xong.")
            log.info('  📋  summary  → "%s"  %.1fs', answer[:100], elapsed_sum)
            return answer

        log.warning("  ⚠   planner trả tool thay vì finish khi tổng kết — dùng obs")
        return state.observation or "Đã hoàn thành yêu cầu."

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_done(self, t0: float, ok: bool = True) -> None:
        label = "done" if ok else "error"
        log.info("  %s  %.1fs", label, time.perf_counter() - t0)
        log.info(_SEP)

    def _build_summary_obs(self, state: AgentState) -> str:
        """Tổng hợp kết quả từ history để planner tổng kết chính xác."""
        successful_obs = [
            h["observation"]
            for h in state.history
            if not h["observation"].startswith("FAILED:")
        ]
        parts: list[str] = []
        if successful_obs:
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
            "path":       "📁 Đường dẫn",
            "preference": "⭐ Ưa thích",
            "schedule":   "📅 Lịch trình",
            "personal":   "👤 Cá nhân",
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
