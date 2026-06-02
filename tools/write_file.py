from pathlib import Path

from tools.result import fail, ok

_MAX_CONTENT_CHARS = 1_000_000  # 1 MB text


def write_file(path: str, content: str, append: bool = False) -> dict:
    """Ghi nội dung vào file. append=True để thêm vào cuối thay vì ghi đè."""
    p = Path((path or "").strip())
    if not p.name:
        return fail("Đường dẫn file không hợp lệ.")

    if len(content or "") > _MAX_CONTENT_CHARS:
        return fail(f"Nội dung quá lớn (>{_MAX_CONTENT_CHARS} ký tự).")

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        p.write_text(content or "", encoding="utf-8") if mode == "w" else p.open("a", encoding="utf-8").write(content or "")
        action = "Đã thêm vào" if append else "Đã ghi"
        return ok(f"{action} file '{p.name}' ({len(content or '')} ký tự).", {"path": str(p)})
    except PermissionError:
        return fail(f"Không có quyền ghi vào: {p}")
    except OSError as exc:
        return fail(f"Lỗi khi ghi file: {exc}")
