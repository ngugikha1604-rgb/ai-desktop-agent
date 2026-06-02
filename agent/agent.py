import json

from agent.config import load_prompt_file, load_settings
from agent.executor import Executor
from agent.llm import GeminiClient
from agent.memory import Memory
from agent.planner import Planner


class Agent:
    def __init__(self) -> None:
        self.planner = Planner()
        self.executor = Executor()
        self.memory = Memory()
        self._llm: GeminiClient | None = None

    def _get_llm(self) -> GeminiClient:
        if self._llm is None:
            self._llm = GeminiClient()
        return self._llm

    def run(self, user_input: str) -> str:
        print(f"\n[Agent] Khởi chạy xử lý yêu cầu của người dùng: '{user_input}'")
        try:
            self.memory.save_message("user", user_input)

            history = self.memory.get_recent_history(limit=10)
            plan = self.planner.plan(user_input, history)

            if self._is_fallback_plan(plan):
                print("[Agent] Planner trả về fallback, chuyển sang conversational response.")
                response = self._conversational_response(user_input)
            else:
                results = self.executor.execute(plan)
                response = self._format_response(user_input, results)

            self.memory.save_message("assistant", response)
            print(f"[Agent] Xử lý hoàn tất thành công!")
            return response
        except Exception as e:
            print(f"[Agent] LỖI: Gặp lỗi trong quá trình xử lý: {e}")
            raise e

    def _is_fallback_plan(self, plan: list[dict]) -> bool:
        if not plan:
            return True
        return (
            len(plan) == 1
            and plan[0].get("task") == "handle_request"
            and not plan[0].get("tool")
        )

    def _conversational_response(self, user_input: str) -> str:
        try:
            settings = load_settings()
            system_prompt = load_prompt_file(settings["agent_prompt"])
            return self._get_llm().generate(system_prompt, user_input)
        except Exception as e:
            print(f"[Agent] _conversational_response lỗi: {e}")
            return f"Xin lỗi, tôi gặp lỗi khi xử lý: {e}"

    def _format_response(self, user_input: str, results: list[dict]) -> str:
        # Tóm tắt kết quả thô từ các tool
        raw_lines = [r.get("message", "") for r in results if r.get("message")]
        raw_summary = "\n".join(raw_lines) if raw_lines else "(Không có kết quả)"

        try:
            settings = load_settings()
            system_prompt = load_prompt_file(settings["agent_prompt"])
            user_message = (
                f"User request: {user_input}\n\n"
                f"Tool results:\n{raw_summary}\n\n"
                f"Please summarize the results naturally in Vietnamese."
            )
            return self._get_llm().generate(system_prompt, user_message)
        except Exception as e:
            print(f"[Agent] _format_response fallback do lỗi LLM: {e}")
            return raw_summary
