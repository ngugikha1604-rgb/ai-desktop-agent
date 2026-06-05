"""TaskAnalyzer — phân tích user input thành danh sách subtask có thứ tự."""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from agent.config import load_prompt_file, load_settings
from agent.llm import OllamaClient, get_analyzer_llm
from agent.logger import get_logger

log = get_logger(__name__)

_MAX_TASKS = 8
_PROMPT_PLACEHOLDER = '"{user_input}"'  # đánh dấu cuối system prompt trong file

# Từ nối multi-step rõ ràng — nếu không có → fast-path, bỏ qua LLM
_MULTI_STEP_RE = re.compile(
    r"\b(rồi|sau\s+đó|tiếp\s+theo|xong\s+thì|xong\s+rồi|sau\s+khi"
    r"|then|after\s+that|and\s+then)\b",
    re.IGNORECASE,
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SubTask(BaseModel):
    task: str
    status: Literal["pending", "done", "failed"] = "pending"
    attempts: int = 0

    @field_validator("task")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("task không được để trống")
        return v


class TaskPlan(BaseModel):
    goal: str = Field(..., min_length=1)
    tasks: list[SubTask] = Field(..., min_length=1)

    @field_validator("tasks")
    @classmethod
    def _limit_tasks(cls, v: list[SubTask]) -> list[SubTask]:
        return v[:_MAX_TASKS]


# ── TaskAnalyzer ──────────────────────────────────────────────────────────────

class TaskAnalyzer:
    """Gọi LLM để tách user input thành TaskPlan (goal + subtask list).

    Nếu LLM fail hoặc trả JSON lỗi → fallback về 1 task duy nhất
    chứa nguyên văn user_input (backward compatible với hành vi cũ).
    """

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None
        self._prompt: str | None = None

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_analyzer_llm()
        return self._llm

    def _load_prompt(self) -> str:
        """Load và cache system prompt một lần mỗi session.

        Cắt dòng placeholder cuối file (nếu có) vì user message
        luôn được build riêng: f'Input: "{user_input}"'.
        """
        if self._prompt is None:
            s = load_settings()
            raw = load_prompt_file(s["analyzer_prompt"])
            marker = f'\nInput: {_PROMPT_PLACEHOLDER}'
            self._prompt = (
                raw[: raw.rfind(marker)].strip()
                if marker in raw
                else raw.strip()
            )
        return self._prompt

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, user_input: str) -> TaskPlan:
        """Phân tích user_input → TaskPlan.

        Fast-path: nếu không có từ nối multi-step (“rồi”, “sau đó”, “then”…)
        → trả về 1-task plan ngay, không gọi LLM.
        Luôn trả về TaskPlan hợp lệ (fallback nếu LLM / parse lỗi).
        """
        if not _MULTI_STEP_RE.search(user_input):
            log.debug("[TaskAnalyzer] Fast-path: không có từ nối multi-step")
            return self._fallback(user_input)

        log.debug("[TaskAnalyzer] Phân tích multi-step: %r", user_input[:80])
        try:
            s = load_settings()
            raw = self._get_llm().generate(
                self._load_prompt(),
                f'Input: "{user_input}"',
                num_predict=s.get("num_predict_analyzer", 256),
                caveman=False,
                json_mode=True,
            )
            log.debug("[TaskAnalyzer] raw: %r", raw)
            plan = self._parse(raw)
            log.info(
                "[TaskAnalyzer] goal=%r tasks=%d",
                plan.goal,
                len(plan.tasks),
            )
            return plan

        except Exception as e:
            log.warning("[TaskAnalyzer] Lỗi — fallback 1 task: %s", e)
            return self._fallback(user_input)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(text: str) -> TaskPlan:
        """Parse raw LLM text → TaskPlan. Raise nếu không hợp lệ."""
        cleaned = text.strip()

        # Bóc JSON khỏi markdown fence nếu có
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()

        data = json.loads(cleaned)
        return TaskPlan.model_validate(data)

    @staticmethod
    def _fallback(user_input: str) -> TaskPlan:
        """Fallback: 1 task = nguyên văn user_input."""
        return TaskPlan(
            goal=user_input[:120],
            tasks=[SubTask(task=user_input[:200])],
        )
