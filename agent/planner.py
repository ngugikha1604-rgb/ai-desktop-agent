import json
import re

from agent.config import load_prompt_file, load_settings
from agent.llm import GeminiClient


class Planner:
    """Chia user request thành danh sách task qua Gemini."""

    def __init__(self) -> None:
        self._llm: GeminiClient | None = None

    def _get_llm(self) -> GeminiClient:
        if self._llm is None:
            self._llm = GeminiClient()
        return self._llm

    def _load_planner_prompt(self) -> str:
        settings = load_settings()
        return load_prompt_file(settings["planner_prompt"])

    def plan(self, user_input: str, history: list[dict] | None = None) -> list[dict]:
        print(f"\n[Planner] Bắt đầu lập kế hoạch cho yêu cầu: '{user_input}'")
        try:
            prompt = self._load_planner_prompt()
            user_message = self._build_user_message(user_input, history)
            text = self._get_llm().generate(prompt, user_message)
            print(f"[Planner] Raw Gemini response: {text!r}")
            parsed = self._parse_plan(text)
            if parsed:
                print(f"[Planner] Lập kế hoạch thành công! Các bước dự kiến:")
                for idx, step in enumerate(parsed, 1):
                    print(f"  Bước {idx}: Task={step.get('task')}, Tool={step.get('tool')}, Args={step.get('args')}")
                return parsed
            else:
                print(f"[Planner] Parse trả về rỗng (có thể Gemini trả [] cho request có tính trò chuyện).")
                return []  # để agent xử lý như conversational
        except json.JSONDecodeError as e:
            print(f"[Planner] JSON parse lỗi: {e}")
        except Exception as e:
            print(f"[Planner] LỖI trong quá trình lập kế hoạch: {e}")

        print("[Planner] Sử dụng kế hoạch dự phòng (fallback plan).")
        return [{"task": "handle_request", "input": user_input}]

    def _build_user_message(self, user_input: str, history: list[dict] | None) -> str:
        if not history:
            return user_input
        recent = history[-6:]  # tối đa 6 lượt gần nhất
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        context = "\n".join(lines)
        return f"Conversation history:\n{context}\n\nCurrent request: {user_input}"

    def _parse_plan(self, text: str) -> list[dict]:
        cleaned = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()

        data = json.loads(cleaned)
        if isinstance(data, dict) and "steps" in data:
            data = data["steps"]
        if not isinstance(data, list):
            return []
        return [step for step in data if isinstance(step, dict)]
