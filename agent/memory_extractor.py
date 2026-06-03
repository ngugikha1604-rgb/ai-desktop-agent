"""MemoryExtractor — trích xuất thông tin có giá trị từ hội thoại, chạy nền."""
from __future__ import annotations

import json
import re
import threading
from typing import Callable

from agent.logger import get_logger

log = get_logger(__name__)

_SENSITIVE_KEYWORDS = [
    "mật khẩu", "password", "token", "api key", "secret",
    "số tài khoản", "số thẻ", "cvv", "otp", "pin",
]

_NAME_PATTERNS = [
    r"(?:tên tôi là|gọi tôi là|tôi tên là|tên mình là)\s+([^\.,\!\?\n]{1,100})",
]

_EXTRACT_SYSTEM_PROMPT = """Bạn là công cụ trích xuất thông tin có giá trị lâu dài từ hội thoại.
Chỉ trích xuất nếu thông tin RÕ RÀNG và CÓ GIÁ TRỊ LÂU DÀI.

Các loại được chấp nhận:
- "path"       : đường dẫn thư mục/file cụ thể (vd: Desktop ở D:/Desktop)
- "preference" : ứng dụng/công cụ ưa thích (vd: dùng VS Code, trình duyệt Firefox)
- "schedule"   : lịch trình/thói quen định kỳ (vd: họp mỗi thứ Hai 9h)
- "personal"   : thông tin cá nhân như tên, tuổi, nghề nghiệp

Trả về JSON array: [{"key": "...", "value": "...", "type": "..."}]
Nếu không có gì đáng lưu, trả về: []

TUYỆT ĐỐI KHÔNG lưu: mật khẩu, token, api key, secret, số tài khoản, số thẻ, cvv, otp, pin.
Chỉ trả về JSON thuần, không có markdown, không giải thích thêm."""


class MemoryExtractor:
    """Chạy trích xuất bộ nhớ bất đồng bộ sau mỗi turn hội thoại."""

    _MAX_NOTIFICATIONS = 3

    def __init__(self, memory) -> None:
        self._memory = memory
        self._llm = None
        self._notification_count = 0  # reset mỗi khi khởi động lại app

    def _get_llm(self):
        if self._llm is None:
            from agent.llm import get_raw_llm
            self._llm = get_raw_llm()
        return self._llm

    def extract_async(
        self,
        user_input: str,
        assistant_response: str,
        on_saved: Callable[[list[dict]], None] | None = None,
    ) -> None:
        """Chạy trích xuất trong background thread — không block UI."""
        t = threading.Thread(
            target=self._extract,
            args=(user_input, assistant_response, on_saved),
            daemon=True,
            name="MemoryExtractor",
        )
        t.start()

    # ── Private ───────────────────────────────────────────────────────

    def _extract(
        self,
        user_input: str,
        assistant_response: str,
        on_saved: Callable[[list[dict]], None] | None,
    ) -> None:
        try:
            saved: list[dict] = []

            # 1. Kiểm tra pattern tên trực tiếp (không cần LLM)
            name_item = self._check_name_pattern(user_input)
            if name_item:
                saved.append(name_item)

            # 2. Dùng LLM trích xuất các loại còn lại
            llm_items = self._llm_extract(user_input, assistant_response)
            saved.extend(llm_items)

            if not saved:
                return

            # Notify UI (tối đa _MAX_NOTIFICATIONS lần mỗi phiên)
            if on_saved:
                if self._notification_count < self._MAX_NOTIFICATIONS:
                    self._notification_count += 1
                    on_saved(saved)
                # Còn lại: vẫn lưu DB nhưng không notify

        except Exception as e:
            log.warning("[MemoryExtractor] Lỗi nền: %s", e)

    def _check_name_pattern(self, user_input: str) -> dict | None:
        """Phát hiện 'Tên tôi là X' / 'Gọi tôi là X' → cập nhật user_profile."""
        for pattern in _NAME_PATTERNS:
            m = re.search(pattern, user_input, re.IGNORECASE)
            if m:
                name = m.group(1).strip().rstrip(".,!?")[:100]
                if 1 <= len(name) <= 100 and not _is_sensitive(name):
                    self._memory.save_user_profile(display_name=name)
                    self._memory.save_long_term_memory(
                        "tên người dùng", name, "personal"
                    )
                    return {"key": "tên người dùng", "value": name}
        return None

    def _llm_extract(self, user_input: str, assistant_response: str) -> list[dict]:
        """Dùng LLM để trích xuất thông tin có giá trị."""
        try:
            conversation = f"User: {user_input}\nAssistant: {assistant_response}"
            result_text = self._get_llm().generate(_EXTRACT_SYSTEM_PROMPT, conversation)

            cleaned = result_text.strip()
            fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if fence:
                cleaned = fence.group(1).strip()

            items = json.loads(cleaned)
            if not isinstance(items, list):
                return []

            saved = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                key   = str(item.get("key", "")).strip()
                value = str(item.get("value", "")).strip()
                mem_type = str(item.get("type", "personal"))
                if not key or not value:
                    continue
                if _is_sensitive(key) or _is_sensitive(value):
                    continue
                if self._memory.save_long_term_memory(key, value, mem_type):
                    saved.append({"key": key, "value": value})
            return saved
        except Exception as e:
            log.warning("[MemoryExtractor] LLM extract lỗi: %s", e)
            return []


def _is_sensitive(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _SENSITIVE_KEYWORDS)
