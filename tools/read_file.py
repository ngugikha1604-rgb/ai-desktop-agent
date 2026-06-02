from pathlib import Path

from tools.result import fail, ok

_MAX_CHARS = 8000
_ENCODINGS = ["utf-8", "utf-8-sig", "cp1258", "cp1252", "latin-1"]


def read_file(path: str, max_chars: int = _MAX_CHARS) -> dict:
    p = Path((path or "").strip())

    if not p.exists():
        return fail(f"File không tồn tại: {path}")
    if not p.is_file():
        return fail(f"Không phải file: {path}")

    size = p.stat().st_size
    if size > 5 * 1024 * 1024:  # 5 MB
        return fail(f"File quá lớn ({size // 1024} KB), không đọc: {p.name}")

    content: str | None = None
    for enc in _ENCODINGS:
        try:
            content = p.read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if content is None:
        return fail(f"Không đọc được file (encoding không hợp lệ): {p.name}")

    truncated = False
    limit = max(1, max_chars)
    if len(content) > limit:
        content = content[:limit]
        truncated = True

    note = f"\n\n...(cắt bớt, chỉ hiển {limit} ký tự đầu)" if truncated else ""
    message = f"Nội dung '{p.name}':\n{content}{note}"
    return ok(message, {"path": str(p), "content": content, "truncated": truncated})
