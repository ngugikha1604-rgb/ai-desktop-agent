from google import genai
from google.genai import types

from agent.config import get_gemini_api_key, load_settings


class GeminiClient:
    """Google AI Studio (Gemini API)."""

    def __init__(self) -> None:
        settings = load_settings()
        self.model = settings.get("model", "gemini-2.0-flash")
        self._client = genai.Client(api_key=get_gemini_api_key())

    def generate(self, system_prompt: str, user_message: str) -> str:
        print(f"\n[GeminiClient] Đang gửi yêu cầu tới Gemini (Model: {self.model})...")
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_message.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt.strip(),
                ),
            )
            res_text = (response.text or "").strip()
            print(f"[GeminiClient] Nhận response từ Gemini thành công ({len(res_text)} ký tự):")
            print(f"--- Response start ---\n{res_text}\n--- Response end ---")
            return res_text
        except Exception as e:
            print(f"[GeminiClient] LỖI: Gặp sự cố khi gọi Gemini API: {e}")
            raise e
