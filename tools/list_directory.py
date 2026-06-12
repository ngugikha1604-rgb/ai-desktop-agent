"""list_directory -- liet ke file va thu muc con voi ten, kich thuoc, ngay sua."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from tools.result import fail, ok

_MAX_ENTRIES = 60   # gioi han de tranh token overflow trong observation


def list_directory(path: str, show_hidden: bool = False) -> dict:
    """Liet ke noi dung thu muc -- thu muc hien thi truoc, file sau.

    Tra ve ten, loai (folder/file), kich thuoc (file), ngay sua cuoi.
    """
    p = Path((path or ".").strip())

    if not p.exists():
        return fail(f"Duong dan khong ton tai: {p}", retryable=False)
    if not p.is_dir():
        return fail(f"Khong phai thu muc: {p}", retryable=False)

    try:
        entries: list[str] = []
        total = 0

        with os.scandir(p) as it:
            # Sap xep: thu muc truoc, sau do file, ca hai theo ten alphabet
            items = sorted(
                it,
                key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
            )
            for entry in items:
                total += 1
                if not show_hidden and entry.name.startswith("."):
                    continue
                if len(entries) >= _MAX_ENTRIES:
                    continue
                try:
                    stat  = entry.stat(follow_symlinks=False)
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m %H:%M")
                    if entry.is_dir(follow_symlinks=False):
                        entries.append(f"[DIR]  {entry.name}/  [{mtime}]")
                    else:
                        entries.append(
                            f"[FILE] {entry.name}  {_fmt_size(stat.st_size)}  [{mtime}]"
                        )
                except (PermissionError, OSError):
                    entries.append(f"[ERR]  {entry.name}  [khong co quyen truy cap]")

        if not entries:
            return ok(f"Thu muc '{p}' rong.")

        shown  = len(entries)
        footer = (
            f"(hien thi {shown}/{total} muc -- bo qua {total - shown} muc con lai)"
            if total > _MAX_ENTRIES
            else f"({total} muc)"
        )
        return ok(f"[{p}]\n" + "\n".join(entries) + f"\n{footer}")

    except PermissionError:
        return fail(f"Khong co quyen truy cap: {p}", retryable=False)
    except OSError as e:
        return fail(f"Loi doc thu muc: {e}")


# -- Helpers ------------------------------------------------------------------

def _fmt_size(size: int) -> str:
    if size < 1_024:
        return f"{size} B"
    if size < 1_048_576:
        return f"{size / 1_024:.1f} KB"
    if size < 1_073_741_824:
        return f"{size / 1_048_576:.1f} MB"
    return f"{size / 1_073_741_824:.1f} GB"
