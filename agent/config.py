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


def load_prompt_file(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")
