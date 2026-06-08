"""Planner — chọn một action tiếp theo cho Agent Loop."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from agent.config import load_prompt_file, load_settings
from agent.llm import OllamaClient, get_planner_llm
from agent.logger import get_logger
from agent.state import AgentState
from tools.registry import build_prompt_section

log = get_logger(__name__)

# ── Hằng số ───────────────────────────────────────────────────────────────────

_MAX_HISTORY = 5    # số bước gần nhất gửi cho LLM
_OBS_TRIM = 150     # ký tự tối đa của observation trong history / observation field
_MEM_MAX = 5        # số memory items tối đa inject vào context
_MIN_RELEVANCE = 0.5  # ngưỡng relevance score để inject memory (tăng từ 0.3)

_STOPWORDS = {
    "tôi", "bạn", "là", "có", "và", "với", "của", "để", "cho",
    "trong", "trên", "một", "các", "này", "đó", "được", "thì",
    "hãy", "giúp", "mở", "chạy", "the", "and", "for", "with",
    "that", "this", "from", "what", "how",
}

# ── Dynamic tool selection ────────────────────────────────────────────────────

# Tools luôn có mặt dù filter thế nào (versatile fallback)
_CORE_TOOLS: frozenset[str] = frozenset({"get_system_info", "run_command"})

# Mapping task.type → tools liên quan
_TYPE_TOOLS: dict[str, frozenset[str]] = {
    "search":      frozenset({"search_file", "read_file"}),
    "read":        frozenset({"read_file", "get_clipboard", "search_file", "get_active_window"}),
    "action":      frozenset({"open_app", "kill_process", "write_file", "browser_action",
                               "open_url", "search_web", "send_notification", "take_screenshot",
                               "set_clipboard"}),
    "communicate": frozenset({"send_notification", "set_clipboard", "get_clipboard", "open_url"}),
    "process":     frozenset({"get_running_processes", "get_active_window"}),
}

# Regex tìm tên tool trong chuỗi hint
_HINT_TOOL_RE = re.compile(
    r"\b(open_app|kill_process|search_file|read_file|write_file"
    r"|get_system_info|get_running_processes|get_active_window|run_command"
    r"|get_clipboard|set_clipboard|take_screenshot|send_notification"
    r"|open_url|search_web|browser_action)\b"
)


# ── Schema ────────────────────────────────────────────────────────────────────

class ActionSchema(BaseModel):
    type: Literal["tool", "finish"]
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = Field(default_factory=dict)
    answer: Optional[str] = None

    @model_validator(mode="after")
    def _check(self) -> "ActionSchema":
        if self.type == "tool" and not self.tool:
            raise ValueError("tool action cần trường 'tool'")
        if self.type == "finish" and not self.answer:
            raise ValueError("finish action cần trường 'answer'")
        return self


# ── Planner ───────────────────────────────────────────────────────────────────

class Planner:
    """Gọi LLM để chọn một action tiếp theo dựa trên AgentState."""

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None
        self._memory = None
        self._prompt_template: str | None = None  # cache: raw template, {tool_docs} chưa thế

    def set_memory(self, memory) -> None:
        self._memory = memory

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_planner_llm()
        return self._llm

    def _get_prompt_template(self) -> str:
        """Load file prompt một lần, giữ nguyên placeholder {tool_docs}."""
        if self._prompt_template is None:
            s = load_settings()
            self._prompt_template = load_prompt_file(s["planner_prompt"])
        return self._prompt_template

    def _get_system_prompt(self, tool_names: list[str] | None) -> str:
        """Build system prompt với danh sách tool đã filter. Không cache (dynamic per step)."""
        return self._get_prompt_template().replace(
            "{tool_docs}", build_prompt_section(tool_names)
        )

    # ── Main ──────────────────────────────────────────────────────────────────

    def plan_step(self, state: AgentState) -> dict:
        """Trả về một action dict: {"type": "tool"|"finish", ...}"""
        log.debug("[Planner] step=%d goal=%r", state.step_count, state.goal[:60])

        # Stuck detection trước khi gọi LLM — tiết kiệm 1 inference call
        if self._is_stuck(state):
            log.warning("[Planner] Stuck tại step %d — dừng loop", state.step_count)
            return {
                "type": "finish",
                "answer": "Tôi gặp khó khăn khi xử lý yêu cầu. Vui lòng thử diễn đạt lại.",
            }

        try:
            s = load_settings()
            tool_names = self._select_tools(state)
            log.debug(
                "[Planner] tools=%s",
                "all" if tool_names is None else str(len(tool_names)),
            )
            text = self._get_llm().generate(
                self._get_system_prompt(tool_names),
                self._build_message(state),
                num_predict=s.get("num_predict_planner", 256),
                caveman=False,   # caveman prefix xung đột với JSON schema
                json_mode=True,
            )
            log.debug("[Planner] raw: %r", text)
            return self._parse(text)

        except (json.JSONDecodeError, ValidationError) as e:
            log.warning("[Planner] parse error: %s", e)
        except Exception:
            raise

        return {"type": "finish", "answer": "Xin lỗi, tôi không hiểu yêu cầu."}

    # ── Stuck detection ───────────────────────────────────────────────────────

    @staticmethod
    def _is_stuck(state: AgentState) -> bool:
        """True nếu 2 bước gần nhất thực hiện cùng tool + args."""
        if len(state.history) < 2:
            return False
        last = state.history[-1]["action"]
        prev = state.history[-2]["action"]
        if last.get("type") != "tool" or prev.get("type") != "tool":
            return False
        return (
            last.get("tool") == prev.get("tool")
            and last.get("args") == prev.get("args")
        )

    # ── Dynamic tool selection ──────────────────────────────────────────

    @staticmethod
    def _select_tools(state: AgentState) -> list[str] | None:
        """Chọn tập con tools phù hợp cho task hiện tại.

        Returns:
            list[str]: tên các tools cần hiển thị (sorted)
            None:      dùng toàn bộ 16 tools (fallback an toàn)
        """
        if not state.has_tasks:
            return None  # không có task info → full list

        task = state.current_task_dict
        if not task:
            return None  # hết tasks (vd: summary step) → full list

        hint: str = task.get("hint", "")
        task_type: str = task.get("type", "")

        if not hint and not task_type:
            return None

        selected: set[str] = set(_CORE_TOOLS)

        # 1. Tool từ hint (ưu tiên nhất — TaskAnalyzer đã suy luận sẵn)
        m = _HINT_TOOL_RE.search(hint) if hint else None
        if m:
            selected.add(m.group(1))

        # 2. Type-based tools
        # Bỏ qua "action" + không có hint: "action" là type default của fast-path
        # fallback (_fallback()) — quá generic, filter sẽ loại mất các tools cần thiết.
        # Chỉ dùng TYPE_TOOLS["action"] khi hint đã xác nhận đây đúng là action task.
        should_use_type = (
            task_type in _TYPE_TOOLS
            and not (task_type == "action" and not hint)
        )
        if should_use_type:
            selected |= _TYPE_TOOLS[task_type]

        # 3. Safety: nếu filter không thêm được gì ngoài core → không có signal
        #    hữu ích → trả None để dùng full list, tránh planner bị mù tool
        if selected == _CORE_TOOLS:
            return None

        log.debug(
            "[Planner._select_tools] hint=%r type=%r → %d tools: %s",
            hint[:60], task_type, len(selected), sorted(selected),
        )
        return sorted(selected)

    # ── Build context message ─────────────────────────────────────────────────

    def _build_message(self, state: AgentState) -> str:
        parts: list[str] = []

        # Bước đầu tiên: inject user name + memory context (chỉ một lần)
        if not state.history:
            if state.user_name:
                parts.append(f"User: {state.user_name}")
            mem = self._get_memory_context(state.goal)
            if mem:
                parts.append(f"[Mem]\n{mem}")

        # Goal — luôn là chuỗi sạch, không prefix
        parts.append(f"Goal: {state.goal}")

        # Current Task — hint / requires / expected_output là reserved fields,
        # sẽ được populate khi TaskAnalyzer được nâng cấp. Hiện tại luôn rỗng.
        if state.has_tasks:
            task = state.current_task_dict
            if task:
                lines = [f"Current Task: {task['task']}"]
                if task.get("hint"):
                    lines.append(f"  Hint: {task['hint']}")
                if task.get("requires"):
                    lines.append(f"  Requires: {', '.join(task['requires'])}")
                if task.get("expected_output"):
                    lines.append(f"  Expected output: {task['expected_output']}")
                parts.append("\n".join(lines))

        # History (last N steps)
        if state.history:
            recent = state.history[-_MAX_HISTORY:]
            lines: list[str] = []
            for h in recent:
                act = h["action"]
                obs = _trim(str(h["observation"]), _OBS_TRIM)
                if act.get("type") == "tool":
                    act_str = (
                        f"{act['tool']}"
                        f"({json.dumps(act.get('args', {}), ensure_ascii=False)})"
                    )
                else:
                    act_str = "finish"
                lines.append(f"- {act_str} → {obs}")
            parts.append("History:\n" + "\n".join(lines))

        # Observation hiện tại
        if state.observation:
            parts.append(f"Observation: {_trim(state.observation, _OBS_TRIM)}")

        return "\n\n".join(parts)

    # ── Memory helpers ────────────────────────────────────────────────────────

    def _get_memory_context(self, goal: str) -> str:
        if self._memory is None:
            return ""
        try:
            keywords = _extract_keywords(goal)
            if not keywords:
                return ""
            results = self._memory.search_long_term_memory(keywords, limit=_MEM_MAX)
            relevant = [r for r in results if r["relevance_score"] >= _MIN_RELEVANCE]
            if not relevant:
                return ""
            for r in relevant:
                self._memory.increment_access_count(r["id"])
            return "\n".join(f"- {r['key']}: {r['value']}" for r in relevant)
        except Exception as e:
            log.warning("[Planner] memory error: %s", e)
            return ""

    # ── Parse ─────────────────────────────────────────────────────────────────

    def _parse(self, text: str) -> dict:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        action = ActionSchema.model_validate_json(cleaned)
        return action.model_dump(exclude_none=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trim(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[^\s,.\!\?\:;\"\'()\[\]{}]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]
