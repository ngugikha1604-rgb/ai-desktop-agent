"""
LLM clients — dùng Ollama (local).
Hai model riêng biệt:
  - planner_model  (qwen2.5:3b)  : parse JSON plan
  - response_model (qwen2.5:0.5b): format câu trả lời
"""
import json
import re
import urllib.error
import urllib.request

from agent.config import load_settings
from agent.logger import get_logger

log = get_logger(__name__)

_OLLAMA_BASE = "http://localhost:11434"
_TIMEOUT = 300  # 5 phút

_CAVEMAN_PREFIX = (
    "Respond terse. Drop articles/filler/pleasantries. "
    "Keep nouns/verbs/numbers/technical terms. "
    "No intro/outro. Direct answer only.\n\n"
)


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

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        num_predict: int = 256,
    ) -> dict:
        """Gọi Ollama với native tool calling.

        Args:
            messages:    Danh sách message theo format Ollama/OpenAI.
            tools:       JSON schema các tool (OpenAI-compatible).
            num_predict: Số token tối đa.

        Returns:
            message dict: {"role": "assistant", "content": "...", "tool_calls": [...]}
            tool_calls = [] hoặc None → model trả lời trực tiếp (finish).
        """
        log.debug("[Ollama:%s] Đang xử lý...", self.model)

        s = load_settings()
        num_ctx = s.get("num_ctx", 4096)

        payload_dict = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        }

        payload = json.dumps(payload_dict).encode("utf-8")
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
            msg = body.get("message") or {}
            tc  = msg.get("tool_calls") or []

            # Qwen3 known bug: tool_calls duoc tra nhung content chua thinking tokens
            # Strip thinking tokens khoi content neu co ca tool_calls lan content
            content = msg.get("content") or ""
            if tc and content:
                # Bỏ thinking block nếu còn sót
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                msg = dict(msg)
                msg["content"] = content

            log.debug(
                "[Ollama:%s] Xong — tool_calls=%s content=%d ky tu",
                self.model, bool(tc), len(msg.get("content") or ""),
            )
            return msg
        except (OllamaServerError, OllamaConnectionError, OllamaModelNotFoundError):
            raise
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise OllamaModelNotFoundError(self.model) from e
            if e.code >= 500:
                raise OllamaServerError(f"HTTP {e.code}") from e
            raise OllamaConnectionError(f"HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise OllamaConnectionError(str(e)) from e
        except OSError as e:
            raise OllamaConnectionError(str(e)) from e

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        num_predict: int = 512,
        caveman: bool = False,
        json_mode: bool = False,
        think: bool = False,
    ) -> str:
        log.debug("[Ollama:%s] Đang xử lý...", self.model)

        # Caveman: inject prefix nén output trước system prompt
        if caveman:
            system_prompt = _CAVEMAN_PREFIX + system_prompt.strip()

        s = load_settings()
        num_ctx = s.get("num_ctx", 4096)

        payload_dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user",   "content": user_message.strip()},
            ],
            "stream": False,
            "think": think,   # Qwen3: False = tắt chain-of-thought, giữ output nhanh
            "options": {
                "temperature": 0.2,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        }
        if json_mode:
            payload_dict["format"] = "json"

        payload = json.dumps(payload_dict).encode("utf-8")

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
            if e.code == 404:
                raise OllamaModelNotFoundError(self.model) from e
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
    """Kiểm tra Ollama đang chạy và model đã pull chưa.

    BUG FIX: dùng exact match thay vì substring match.
    "qwen2.5" KHÔNG nên khớp với "qwen2.5:7b" khi cần "qwen2.5:3b".
    """
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as r:
            tags = json.loads(r.read())
    except Exception as e:
        raise OllamaConnectionError(str(e)) from e

    available: list[str] = [m["name"] for m in tags.get("models", [])]

    if not available:
        raise OllamaModelNotFoundError(model)

    if model not in available:
        log.warning(
            "[Ollama] Model '%s' không có trong danh sách %s.", model, available
        )
        raise OllamaModelNotFoundError(model)


def get_planner_llm() -> OllamaClient:
    s = load_settings()
    base_url = s.get("ollama_base_url", _OLLAMA_BASE)
    model = s.get("planner_model", "qwen2.5:3b")
    _check_ollama(base_url, model)
    return OllamaClient(model=model, base_url=base_url)


def get_analyzer_llm() -> OllamaClient:
    """LLM cho Task Analyzer.

    Dùng 'analyzer_model' nếu được cấu hình riêng,
    fallback về 'planner_model' (qwen2.5:3b) nếu không.
    Thiết kế này cho phép tách model về sau mà không cần đổi code.
    """
    s = load_settings()
    base_url = s.get("ollama_base_url", _OLLAMA_BASE)
    model = s.get("analyzer_model") or s.get("planner_model", "qwen2.5:3b")
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
