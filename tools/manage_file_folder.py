import os
import shutil
from pathlib import Path

from tools.result import fail, ok

# send2trash chuyen file/thu muc vao Thung rac thay vi xoa vinh vien
# Neu chua cai (pip install send2trash), fallback ve xoa vinh vien kem canh bao.
try:
    import send2trash as _s2t
    _HAS_SEND2TRASH = True
except ImportError:
    _HAS_SEND2TRASH = False


def manage_file_folder(
    action: str,
    src_path: str | None = None,
    dest_path: str | None = None,
) -> dict:
    """Quan ly file va thu muc an toan: copy, move, delete, rename, create_folder.

    Args:
        action:    'copy' | 'move' | 'delete' | 'rename' | 'create_folder'
        src_path:  Duong dan nguon (bat buoc cho moi action tru create_folder).
        dest_path: Duong dan dich (bat buoc cho copy, move, rename).

    Ghi chu:
        'delete' gui vao Thung rac (Recycle Bin) neu send2trash da cai.
        Neu chua cai, xoa vinh vien va canh bao trong ket qua.
    """
    act = (action or "").strip().lower()
    if act not in {"copy", "move", "delete", "rename", "create_folder"}:
        return fail(
            f"Hanh dong khong hop le: '{action}'. "
            "Chon mot trong: copy, move, delete, rename, create_folder"
        )

    # -- create_folder --------------------------------------------------------
    if act == "create_folder":
        if not src_path:
            return fail("Thieu 'src_path': duong dan thu muc can tao.")
        p = Path(src_path.strip())
        try:
            p.mkdir(parents=True, exist_ok=True)
            return ok(f"Da tao thu muc: '{p}'", {"path": str(p)})
        except Exception as e:
            return fail(f"Loi khi tao thu muc '{p}': {e}")

    # Tat ca action con lai can src_path va file/thu muc phai ton tai
    if not src_path:
        return fail(f"Hanh dong '{action}' yeu cau 'src_path'.")

    src = Path(src_path.strip())
    if not src.exists():
        return fail(f"Duong dan nguon khong ton tai: '{src}'", retryable=False)

    # -- delete ---------------------------------------------------------------
    if act == "delete":
        try:
            if _HAS_SEND2TRASH:
                _s2t.send2trash(str(src))
                return ok(
                    f"Da chuyen '{src.name}' vao Thung rac.",
                    {"path": str(src), "method": "recycle_bin"},
                )
            else:
                # Fallback: xoa vinh vien (canh bao trong message)
                if src.is_dir():
                    shutil.rmtree(src)
                else:
                    src.unlink()
                return ok(
                    f"Da xoa vinh vien '{src.name}'. "
                    "(Cai 'send2trash' de chuyen vao Thung rac thay vi xoa vinh vien.)",
                    {"path": str(src), "method": "permanent"},
                )
        except Exception as e:
            return fail(f"Loi khi xoa '{src}': {e}")

    # copy, move, rename deu can dest_path
    if not dest_path:
        return fail(f"Hanh dong '{action}' yeu cau 'dest_path'.")

    dest = Path(dest_path.strip())

    # -- copy -----------------------------------------------------------------
    if act == "copy":
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
                return ok(
                    f"Da sao chep thu muc '{src.name}' sang '{dest}'.",
                    {"src": str(src), "dest": str(dest)},
                )
            else:
                shutil.copy2(src, dest)
                return ok(
                    f"Da sao chep file '{src.name}' sang '{dest}'.",
                    {"src": str(src), "dest": str(dest)},
                )
        except Exception as e:
            return fail(f"Loi khi sao chep '{src}' sang '{dest}': {e}")

    # -- move -----------------------------------------------------------------
    if act == "move":
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return ok(
                f"Da di chuyen '{src.name}' sang '{dest}'.",
                {"src": str(src), "dest": str(dest)},
            )
        except Exception as e:
            return fail(f"Loi khi di chuyen '{src}' sang '{dest}': {e}")

    # -- rename ---------------------------------------------------------------
    if act == "rename":
        try:
            # dest chi la ten moi (khong co parent) -> doi ten tai cho
            if len(dest.parts) == 1:
                target = src.parent / dest
            else:
                target = dest
                if target.parent != src.parent:
                    return fail(
                        "rename chi doi ten tai cho. "
                        "De di chuyen sang thu muc khac, dung hanh dong 'move'.",
                        retryable=False,
                    )
            src.rename(target)
            return ok(
                f"Da doi ten '{src.name}' thanh '{target.name}'.",
                {"src": str(src), "dest": str(target)},
            )
        except Exception as e:
            return fail(f"Loi khi doi ten '{src}' thanh '{dest}': {e}")

    return fail("Hanh dong khong duoc ho tro.")
