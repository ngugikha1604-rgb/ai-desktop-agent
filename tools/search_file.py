import os
from pathlib import Path

from tools.result import fail, ok

_MAX_RESULTS = 20
_MAX_DEPTH = 6

# Thư mục mặc định tìm kiếm
_DEFAULT_ROOTS = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home(),
]


def _walk_limited(root: Path, max_depth: int):
    """os.walk với giới hạn độ sâu."""
    root_depth = len(root.parts)
    for dirpath, dirs, files in os.walk(root):
        current = Path(dirpath)
        depth = len(current.parts) - root_depth
        if depth >= max_depth:
            dirs.clear()  # không đi sâu hơn
        yield current, files


def search_file(keyword: str, root: str | None = None) -> dict:
    kw = (keyword or "").strip().lower()
    if not kw:
        return fail("Từ khoá tìm kiếm trống.")

    search_roots: list[Path]
    if root:
        r = Path(root)
        if not r.exists():
            return fail(f"Thư mục không tồn tại: {root}")
        search_roots = [r]
    else:
        search_roots = [r for r in _DEFAULT_ROOTS if r.exists()]

    found: list[dict] = []
    seen: set[str] = set()

    for search_root in search_roots:
        if len(found) >= _MAX_RESULTS:
            break
        try:
            for dirpath, files in _walk_limited(search_root, _MAX_DEPTH):
                for fname in files:
                    if kw in fname.lower():
                        full = str(dirpath / fname)
                        if full not in seen:
                            seen.add(full)
                            found.append({"name": fname, "path": full})
                            if len(found) >= _MAX_RESULTS:
                                break
                if len(found) >= _MAX_RESULTS:
                    break
        except PermissionError:
            continue

    if not found:
        return ok(f"Không tìm thấy file nào khớp '{keyword}'.", [])

    lines = [f"- {f['name']}\n  {f['path']}" for f in found]
    message = f"Tìm thấy {len(found)} file khớp '{keyword}':\n" + "\n".join(lines)
    return ok(message, found)
