import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def load_settings() -> dict:
    path = ROOT / "config" / "settings.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY chưa được đặt. Thêm key vào file .env "
            "(lấy tại https://aistudio.google.com/apikey)"
        )
    return key


def load_prompt_file(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")
