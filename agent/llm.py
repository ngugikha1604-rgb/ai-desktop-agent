"""
LLM clients — dùng Ollama (local).
Hai model riêng biệt:
  - planner_model  (qwen2.5:3b)  : parse JSON plan
  - response_model (qwen2.5:0.5b): format câu trả lời
"""
import json
import urllib.error
import urllib.request

from agent.config import load_settings
from agent.logger import get_logger

log = get_logger(__name__)

_OLLAMA_BASE = "http://localhost:11434"
_TIMEOUT = 300  # 5 phút


# ── Custom exceptions ─────────────────────────────────────────────────────────

class OllamaConnectionError(RuntimeError):
    """Ollama daemon không phản hồi (chưa chạy hoặc connection refused)."""


class OllamaModelNotFoundError(RuntimeError):
    """Model chưa được pull về."""
    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(model)


class OllamaServerError(RuntimeError):
    """Ollama trả về HTTP 5xx."""


# ── Client ────────────────────────────────────────────────────────────────────

class OllamaClient:
    """Ollama local LLM client."""

    def __init__(self, model: str, base_url: str = _OLLAMA_BASE) -> None:
        self.model = model
        self.base_url = base_url

    def generate(self, system_prompt: str, user_message: str) -> str:
        log.debug("[Ollama:%s] Đang xử lý...", self.model)

        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user",   "content": user_message.strip()},
            ],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 1024},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                if resp.status >= 500:
                    raise OllamaServerError(f"HTTP {resp.status}")
                body = json.loads(resp.read().decode("utf-8"))
            text = (body.get("message", {}).get("content") or "").strip()
            log.debug("[Ollama:%s] Xong (%d ký tự)", self.model, len(text))
            return text
        except (OllamaServerError, OllamaConnectionError, OllamaModelNotFoundError):
            raise
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                raise OllamaServerError(f"HTTP {e.code}") from e
            raise OllamaConnectionError(f"HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise OllamaConnectionError(str(e)) from e
        except OSError as e:
            raise OllamaConnectionError(str(e)) from e

    def check_connection(self) -> bool:
        """Kiểm tra Ollama có đang chạy không (dùng cho UI status indicator)."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Trả về danh sách model đang có trong Ollama."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5) as r:
                data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_ollama(base_url: str, model: str) -> None:
    """Kiểm tra Ollama đang chạy và model đã pull chưa. Raise ngoại lệ cụ thể."""
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
    except Exception as e:
        raise OllamaConnectionError(str(e)) from e

    available = [m["name"] for m in tags.get("models", [])]
    base_name = model.split(":")[0]
    found = any(base_name in m for m in available)
    if not found:
        log.warning("[Ollama] Model '%s' chưa thấy trong danh sách.", model)
        raise OllamaModelNotFoundError(model)


def get_planner_llm() -> OllamaClient:
    s = load_settings()
    base_url = s.get("ollama_base_url", _OLLAMA_BASE)
    model = s.get("planner_model", "qwen2.5:3b")
    _check_ollama(base_url, model)
    return OllamaClient(model=model, base_url=base_url)


def get_response_llm() -> OllamaClient:
    s = load_settings()
    base_url = s.get("ollama_base_url", _OLLAMA_BASE)
    model = s.get("response_model", "qwen2.5:0.5b")
    _check_ollama(base_url, model)
    return OllamaClient(model=model, base_url=base_url)


def get_raw_llm() -> OllamaClient:
    """Client không kiểm tra model — dùng nội bộ cho MemoryExtractor."""
    s = load_settings()
    base_url = s.get("ollama_base_url", _OLLAMA_BASE)
    model = s.get("response_model", "qwen2.5:0.5b")
    return OllamaClient(model=model, base_url=base_url)
