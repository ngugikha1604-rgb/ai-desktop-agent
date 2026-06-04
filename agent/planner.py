"""Planner — chia user request thành danh sách task qua LLM, bổ sung context bộ nhớ."""
import json
import re
from typing import List, Dict, Any

from pydantic import BaseModel, Field, ValidationError

from agent.config import load_prompt_file, load_settings
from agent.llm import OllamaClient, get_planner_llm
from agent.logger import get_logger


class StepSchema(BaseModel):
    task: str = Field(description="Mô tả ngắn gọn về bước thực hiện")
    tool: str = Field(description="Tên tool cần gọi")
    args: Dict[str, Any] = Field(default_factory=dict, description="Các đối số truyền vào cho tool")


class PlanSchema(BaseModel):
    steps: List[StepSchema]

log = get_logger(__name__)

_MIN_RELEVANCE = 0.3
_MAX_MEMORY_ITEMS = 5
# Cắt ngắn mỗi turn trong history để tiết kiệm token cho planner
_HISTORY_CONTENT_MAX = 200

_STOPWORDS = {
    "tôi", "bạn", "là", "có", "và", "với", "của", "để", "cho",
    "trong", "trên", "một", "các", "này", "đó", "được", "thì",
    "hãy", "giúp", "mở", "chạy", "the", "and", "for", "with",
    "that", "this", "from", "what", "how",
}


class Planner:
    """Chia user request thành danh sách task qua LLM."""

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None
        self._memory = None  # set sau bởi Agent để tránh circular import

    def set_memory(self, memory) -> None:
        self._memory = memory

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_planner_llm()
        return self._llm

    def _load_planner_prompt(self) -> str:
        settings = load_settings()
        return load_prompt_file(settings["planner_prompt"])

    def plan(self, user_input: str, history: list[dict] | None = None) -> list[dict]:
        log.debug("[Planner] Lập kế hoạch: %r", user_input)
        try:
            s = load_settings()
            num_predict = s.get("num_predict_planner", 256)
            caveman = s.get("caveman_mode", True)

            prompt = self._load_planner_prompt()
            user_message = self._build_user_message(user_input, history)
            text = self._get_llm().generate(
                prompt, user_message,
                num_predict=num_predict,
                caveman=caveman,
                json_mode=True,
            )
            log.debug("[Planner] Raw response: %r", text)
            parsed = self._parse_plan(text)
            if parsed:
                return parsed
            return []
        except (json.JSONDecodeError, ValidationError) as e:
            log.warning("[Planner] JSON/Validation parse lỗi: %s", e)
        except Exception:
            raise

        return [{"task": "handle_request", "input": user_input}]

    def _build_user_message(self, user_input: str, history: list[dict] | None) -> str:
        parts: list[str] = []

        # 1. Memory context
        memory_ctx = self._get_memory_context(user_input)
        if memory_ctx:
            parts.append(f"[Mem]\n{memory_ctx}")

        # 2. Conversation history — giữ 4 turn gần nhất, cắt content dài
        if history:
            recent = history[-4:]
            lines = []
            for msg in recent:
                role = "U" if msg["role"] == "user" else "A"
                content = msg["content"]
                if len(content) > _HISTORY_CONTENT_MAX:
                    content = content[:_HISTORY_CONTENT_MAX] + "…"
                lines.append(f"{role}: {content}")
            parts.append("[Hist]\n" + "\n".join(lines))

        # 3. Current request
        parts.append(f"[Req]\n{user_input}")
        return "\n\n".join(parts)

    def _get_memory_context(self, user_input: str) -> str:
        if self._memory is None:
            return ""
        try:
            keywords = self._extract_keywords(user_input)
            if not keywords:
                return ""
            results = self._memory.search_long_term_memory(keywords, limit=_MAX_MEMORY_ITEMS)
            relevant = [r for r in results if r["relevance_score"] >= _MIN_RELEVANCE]
            if not relevant:
                return ""
            for r in relevant:
                self._memory.increment_access_count(r["id"])
            return "\n".join(f"- {r['key']}: {r['value']}" for r in relevant)
        except Exception as e:
            log.warning("[Planner] Không lấy được memory context: %s", e)
            return ""

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        words = re.findall(r"[^\s,.\!\?\:;\"\']+", text.lower())
        return [w for w in words if len(w) > 2 and w not in _STOPWORDS]

    def _parse_plan(self, text: str) -> list[dict]:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        
        # Thử parse và validate bằng Pydantic PlanSchema
        try:
            plan_obj = PlanSchema.model_validate_json(cleaned)
            return [step.model_dump() for step in plan_obj.steps]
        except ValidationError as e:
            # Fallback nếu model trả về list các steps trực tiếp (ví dụ [ {...} ])
            try:
                data = json.loads(cleaned)
                if isinstance(data, list):
                    validated_steps = []
                    for step in data:
                        if isinstance(step, dict):
                            validated_steps.append(StepSchema.model_validate(step).model_dump())
                    return validated_steps
            except Exception:
                pass
            raise e
