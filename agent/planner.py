"""Planner — chọn một action tiếp theo cho Agent Loop."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal, Optional

_USER_PREFIX_RE = re.compile(r"^\[User:[^\]]+\]\s*")

from pydantic import BaseModel, Field, ValidationError, model_validator

from agent.config import load_prompt_file, load_settings
from agent.llm import OllamaClient, get_planner_llm
from agent.logger import get_logger
from agent.state import AgentState

log = get_logger(__name__)

_MAX_HISTORY = 3       # số bước gần nhất gửi cho LLM
_OBS_IN_HIST = 150     # ký tự tối đa của observation trong history
_MEM_MAX = 5
_MIN_RELEVANCE = 0.3

_STOPWORDS = {
    "tôi", "bạn", "là", "có", "và", "với", "của", "để", "cho",
    "trong", "trên", "một", "các", "này", "đó", "được", "thì",
    "hãy", "giúp", "mở", "chạy", "the", "and", "for", "with",
    "that", "this", "from", "what", "how",
}


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
        self._memory = None  # được set bởi Agent sau khi khởi tạo

    def set_memory(self, memory) -> None:
        self._memory = memory

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_planner_llm()
        return self._llm

    def plan_step(self, state: AgentState) -> dict:
        """Trả về một action dict: {"type": "tool"|"finish", ...}"""
        log.debug("[Planner] step=%d goal=%r", state.step_count, state.goal[:60])

        # ── Stuck detection: nếu bước vừa rồi lặp lại y hệt bước trước → dừng
        if self._is_stuck(state):
            log.warning("[Planner] Stuck detected at step %d — aborting loop", state.step_count)
            return {"type": "finish", "answer": "Tôi gặp vấn đề khi thực hiện yêu cầu. Vui lòng thử lại."}

        try:
            s = load_settings()
            prompt = load_prompt_file(s["planner_prompt"])
            user_msg = self._build_message(state)
            # caveman_mode KHÔNG áp dụng cho Planner: prefix "Respond terse..."
            # xung đột với JSON schema và làm confused small model.
            text = self._get_llm().generate(
                prompt,
                user_msg,
                num_predict=s.get("num_predict_planner", 256),
                caveman=False,
                json_mode=True,
            )
            log.debug("[Planner] raw: %r", text)
            return self._parse(text)

        except (json.JSONDecodeError, ValidationError) as e:
            log.warning("[Planner] parse error: %s", e)
        except Exception:
            raise

        return {"type": "finish", "answer": "Xin lỗi, tôi không hiểu yêu cầu."}

    # ── Build context message ─────────────────────────────────────────────────

    # ── Stuck detection ───────────────────────────────────────────────────────

    @staticmethod
    def _is_stuck(state: AgentState) -> bool:
        """Trả True nếu 2 bước gần nhất thực hiện cùng tool + args."""
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

    # ── Build context message ─────────────────────────────────────────────────

    def _build_message(self, state: AgentState) -> str:
        parts: list[str] = []

        # Strip [User: Name] prefix — chỉ dùng để enrich goal, không nên
        # gửi cho LLM vì có thể gây nhầm lẫn (model nhỏ bám vào token lạ).
        clean_goal = _USER_PREFIX_RE.sub("", state.goal).strip()

        # Memory context — chỉ inject ở bước đầu tiên để tiết kiệm token
        if not state.history:
            mem = self._get_memory_context(clean_goal)
            if mem:
                parts.append(f"[Mem]\n{mem}")

        # Goal
        parts.append(f"Goal: {clean_goal}")

        # History (last N steps)
        if state.history:
            recent = state.history[-_MAX_HISTORY:]
            lines: list[str] = []
            for h in recent:
                act = h["action"]
                obs = str(h["observation"])
                if len(obs) > _OBS_IN_HIST:
                    obs = obs[:_OBS_IN_HIST] + "…"
                if act.get("type") == "tool":
                    act_str = f"{act['tool']}({json.dumps(act.get('args', {}), ensure_ascii=False)})"
                else:
                    act_str = "finish"
                lines.append(f"- {act_str} → {obs}")
            parts.append("History:\n" + "\n".join(lines))

        # Observation hiện tại
        if state.observation:
            obs = state.observation
            if len(obs) > _OBS_IN_HIST:
                obs = obs[:_OBS_IN_HIST] + "…"
            parts.append(f"Observation: {obs}")

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

def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[^\s,.\!\?\:;\"\']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]
