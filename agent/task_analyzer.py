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
_PROMPT_PLACEHOLDER = '"{user_input}"'

# Từ nối multi-step rõ ràng — nếu không có → fast-path, bỏ qua LLM
_MULTI_STEP_RE = re.compile(
    r"\b(rồi|sau\s+đó|tiếp\s+theo|xong\s+thì|xong\s+rồi|sau\s+khi"
    r"|đồng\s+thời"                                          # đồng thời = simultaneously
    r"|và\s+(?:cho|mở|tìm|đọc|lấy|xem|kiểm\s*tra|chạy|tắt|gửi|bật|chụp)"  # và + action verb
    r"|then|after\s+that|and\s+then)\b",
    re.IGNORECASE,
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class SubTask(BaseModel):
    task: str

    # Loại hành động — giúp planner hiểu ngữ cảnh
    type: Literal["action", "search", "read", "process", "communicate"] = "action"

    # Gợi ý tool nào nên dùng — tác động lớn nhất đến chất lượng Qwen 3B
    hint: str = ""

    # Dữ liệu đầu vào cần có — planner biết phải lấy từ task trước
    requires: list[str] = Field(default_factory=list)

    # Kết quả kỳ vọng — planner biết khi nào task được coi là xong
    expected_output: str = ""

    # Runtime state (không do LLM sinh ra)
    status: Literal["pending", "done", "failed"] = "pending"
    attempts: int = 0

    @field_validator("task")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("task không được để trống")
        return v

    @field_validator("hint", "expected_output", mode="before")
    @classmethod
    def _strip_str(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v


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

    Fast-path: input không có từ nối multi-step → 1 task, không gọi LLM.
    Fallback: LLM fail / JSON lỗi → 1 task fallback, không crash.
    """

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None
        self._prompt: str | None = None

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_analyzer_llm()
        return self._llm

    def _load_prompt(self) -> str:
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
        """Phân tích user_input → TaskPlan."""
        if not _MULTI_STEP_RE.search(user_input):
            log.debug("[TaskAnalyzer] Fast-path: không có từ nối multi-step")
            return self._fallback(user_input)

        log.debug("[TaskAnalyzer] Phân tích multi-step: %r", user_input[:80])
        try:
            s = load_settings()
            raw = self._get_llm().generate(
                self._load_prompt(),
                f'Input: "{user_input}"',
                num_predict=s.get("num_predict_analyzer", 512),
                caveman=False,
                json_mode=True,
            )
            log.debug("[TaskAnalyzer] raw: %r", raw)
            plan = self._parse(raw)
            log.info(
                "[TaskAnalyzer] goal=%r tasks=%d hint_count=%d",
                plan.goal, len(plan.tasks),
                sum(1 for t in plan.tasks if t.hint),
            )
            return plan

        except Exception as e:
            log.warning("[TaskAnalyzer] Lỗi — fallback 1 task: %s", e)
            return self._fallback(user_input)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse(text: str) -> TaskPlan:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        data = json.loads(cleaned)
        return TaskPlan.model_validate(data)

    @staticmethod
    def _fallback(user_input: str) -> TaskPlan:
        """1 task = nguyên văn user_input, không có metadata."""
        return TaskPlan(
            goal=user_input[:120],
            tasks=[SubTask(task=user_input[:200])],
        )
