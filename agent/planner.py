"""Planner -- chon mot action tiep theo cho Agent Loop.

Su dung Ollama native tool calling thay vi prompt-based JSON:
- Tools truyen qua tham so rieng (OpenAI schema) thay vi text trong prompt
- Model tra ve tool_calls (structured) thay vi raw JSON string
- System prompt ngan gon hon (~150 token thay vi ~650 token)
"""
from __future__ import annotations

import json
import re

from agent.config import load_prompt_file, load_settings
from agent.llm import OllamaClient, get_planner_llm
from agent.logger import get_logger
from agent.state import AgentState
from tools.registry import build_tool_schemas

log = get_logger(__name__)

# -- Hang so ------------------------------------------------------------------

_MAX_HISTORY  = 5    # so buoc gan nhat gui cho LLM
_OBS_MSG_TRIM = 800  # ky tu toi da cua tool result trong message (du cho 2 web_search results)
_MEM_MAX      = 5    # so memory items toi da inject vao context
_MIN_RELEVANCE = 0.5  # nguong relevance score de inject memory

_STOPWORDS = {
    "toi", "ban", "la", "co", "va", "voi", "cua", "de", "cho",
    "trong", "tren", "mot", "cac", "nay", "do", "duoc", "thi",
    "hay", "giup", "mo", "chay", "the", "and", "for", "with",
    "that", "this", "from", "what", "how",
}

# -- Dynamic tool selection ---------------------------------------------------

_CORE_TOOLS: frozenset[str] = frozenset({"get_system_info", "run_command"})

_TYPE_TOOLS: dict[str, frozenset[str]] = {
    "search":      frozenset({"search_file", "read_file", "web_search", "get_weather"}),
    "read":        frozenset({"read_file", "get_clipboard", "search_file",
                               "get_active_window", "web_read", "web_search"}),
    "action":      frozenset({"open_app", "kill_process", "write_file", "browser_action",
                               "open_url", "search_web", "web_search", "web_read",
                               "get_weather", "send_notification", "take_screenshot",
                               "set_clipboard"}),
    "communicate": frozenset({"send_notification", "set_clipboard", "get_clipboard", "open_url"}),
    "process":     frozenset({"get_running_processes", "get_active_window"}),
}

_HINT_TOOL_RE = re.compile(
    r"\b(open_app|kill_process|search_file|read_file|write_file"
    r"|get_system_info|get_running_processes|get_active_window|run_command"
    r"|get_clipboard|set_clipboard|take_screenshot|send_notification"
    r"|open_url|search_web|web_search|web_read|get_weather|browser_action)\b"
)


# -- Planner ------------------------------------------------------------------

class Planner:
    """Goi LLM de chon mot action tiep theo dua tren AgentState."""

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None
        self._memory = None
        self._system_prompt: str | None = None  # cache

    def set_memory(self, memory) -> None:
        self._memory = memory

    def _get_llm(self) -> OllamaClient:
        if self._llm is None:
            self._llm = get_planner_llm()
        return self._llm

    def _get_system_prompt(self) -> str:
        """Load planner_prompt.txt mot lan, cache lai. Khong con {tool_docs}."""
        if self._system_prompt is None:
            s = load_settings()
            self._system_prompt = load_prompt_file(s["planner_prompt"])
        return self._system_prompt

    # -- Main -----------------------------------------------------------------

    def plan_step(self, state: AgentState) -> dict:
        """Tra ve mot action dict: {"type": "tool"|"finish", ...}"""
        log.debug("[Planner] step=%d goal=%r", state.step_count, state.goal[:60])

        # Stuck detection truoc khi goi LLM -- tiet kiem 1 inference call
        if self._is_stuck(state):
            log.warning("[Planner] Stuck tai step %d -- dung loop", state.step_count)
            return {
                "type": "finish",
                "answer": "Toi gap kho khan khi xu ly yeu cau. Vui long thu dien dat lai.",
            }

        s = load_settings()
        tool_names = self._select_tools(state)
        log.debug("[Planner] tools=%s", "all" if tool_names is None else str(len(tool_names)))

        messages    = self._build_messages(state, self._get_system_prompt())
        tool_schemas = build_tool_schemas(tool_names)

        msg = self._get_llm().chat_with_tools(
            messages=messages,
            tools=tool_schemas,
            num_predict=s.get("num_predict_planner", 256),
        )

        tool_calls = msg.get("tool_calls") or []
        content    = (msg.get("content") or "").strip()

        if tool_calls:
            tc        = tool_calls[0]["function"]
            tool_name = tc.get("name", "")
            tool_args = tc.get("arguments") or {}
            # Ollama doi khi tra arguments dang string JSON
            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {}
            log.debug("[Planner] raw: tool=%r args=%r", tool_name, tool_args)
            log.info(
                "  \U0001f9e0  plan     \u2192 %s(%s)",
                tool_name,
                json.dumps(tool_args, ensure_ascii=False),
            )
            return {"type": "tool", "tool": tool_name, "args": tool_args}

        log.debug("[Planner] raw: finish content=%r", content[:80])
        log.info("  \U0001f9e0  plan     \u2192 finish")
        return {"type": "finish", "answer": content or "Xong."}

    # -- Stuck detection ------------------------------------------------------

    @staticmethod
    def _is_stuck(state: AgentState) -> bool:
        """True neu 2 buoc gan nhat la cung tool + args VA khong phai retry thanh cong."""
        if len(state.history) < 2:
            return False
        last = state.history[-1]
        prev = state.history[-2]
        la, pa = last["action"], prev["action"]
        if la.get("type") != "tool" or pa.get("type") != "tool":
            return False
        if la.get("tool") != pa.get("tool") or la.get("args") != pa.get("args"):
            return False
        # Retry pattern: truoc FAILED, sau SUCCESS -> khong phai stuck
        prev_failed    = str(prev["observation"]).startswith("FAILED:")
        last_succeeded = not str(last["observation"]).startswith("FAILED:")
        if prev_failed and last_succeeded:
            return False
        return True

    # -- Dynamic tool selection -----------------------------------------------

    @staticmethod
    def _select_tools(state: AgentState) -> list[str] | None:
        """Chon tap con tools phu hop cho task hien tai. None = full list."""
        if not state.has_tasks:
            return None
        task = state.current_task_dict
        if not task:
            return None
        hint: str      = task.get("hint", "")
        task_type: str = task.get("type", "")
        if not hint and not task_type:
            return None

        selected: set[str] = set(_CORE_TOOLS)

        m = _HINT_TOOL_RE.search(hint) if hint else None
        if m:
            selected.add(m.group(1))

        should_use_type = (
            task_type in _TYPE_TOOLS
            and not (task_type == "action" and not hint)
        )
        if should_use_type:
            selected |= _TYPE_TOOLS[task_type]

        if selected == _CORE_TOOLS:
            return None

        log.debug(
            "[Planner._select_tools] hint=%r type=%r -> %d tools: %s",
            hint[:60], task_type, len(selected), sorted(selected),
        )
        return sorted(selected)

    # -- Build messages (Ollama format) ---------------------------------------

    def _build_messages(self, state: AgentState, system_prompt: str) -> list[dict]:
        """Build danh sach message theo format Ollama/OpenAI cho tool calling."""
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # User message: goal + context (chi inject memory o buoc dau)
        user_parts: list[str] = []
        if not state.history:
            if state.user_name:
                user_parts.append(f"(User: {state.user_name})")
            mem = self._get_memory_context(state.goal)
            if mem:
                user_parts.append(f"[Context]\n{mem}")
        user_parts.append(state.goal)
        messages.append({"role": "user", "content": "\n\n".join(user_parts)})

        # History: tung cap (tool call → tool result)
        for h in state.history[-_MAX_HISTORY:]:
            action = h["action"]
            obs    = h["observation"]

            if action.get("type") == "tool":
                # Assistant da goi tool nay
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "function": {
                            "name":      action["tool"],
                            "arguments": action.get("args") or {},
                        }
                    }],
                })
                # Ket qua tra ve tu tool
                messages.append({
                    "role":    "tool",
                    "content": str(obs)[:_OBS_MSG_TRIM],
                    "name":    action["tool"],
                })

        return messages

    # -- Memory helpers -------------------------------------------------------

    def _get_memory_context(self, goal: str) -> str:
        if self._memory is None:
            return ""
        try:
            keywords = _extract_keywords(goal)
            if not keywords:
                return ""
            results  = self._memory.search_long_term_memory(keywords, limit=_MEM_MAX)
            relevant = [r for r in results if r["relevance_score"] >= _MIN_RELEVANCE]
            if not relevant:
                return ""
            for r in relevant:
                self._memory.increment_access_count(r["id"])
            return "\n".join(f"- {r['key']}: {r['value']}" for r in relevant)
        except Exception as e:
            log.warning("[Planner] memory error: %s", e)
            return ""


# -- Helpers ------------------------------------------------------------------

def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[^\s,.\!\?\:;\"\'()\[\]{}]+", text.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]
