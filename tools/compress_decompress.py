import os
import zipfile
from pathlib import Path

from tools.result import fail, ok


def compress_decompress(action: str, path: str, dest_path: str | None = None) -> dict:
    """Nén (zip) hoặc giải nén (unzip) file và thư mục bằng thư viện Python.

    Args:
        action: Hành động cần thực hiện: "zip" | "unzip".
        path: Đường dẫn tới file/thư mục cần nén, hoặc file zip cần giải nén.
        dest_path: Đường dẫn đích.
                   - Đối với "zip": Đường dẫn file zip kết quả (mặc định: [path].zip).
                   - Đối với "unzip": Thư mục giải nén (mặc định: cùng cấp với file zip).
    """
    act = (action or "").strip().lower()
    if act not in {"zip", "unzip"}:
        return fail(f"Hành động không hợp lệ: '{action}'. Chọn một trong: zip, unzip")

    p = Path((path or "").strip())
    if not p.exists():
        return fail(f"Đường dẫn nguồn không tồn tại: '{path}'")

    if act == "zip":
        # Xác định đường dẫn file zip đích
        if dest_path:
            dest = Path(dest_path.strip())
        else:
            dest = p.with_name(f"{p.name}.zip")

        # Đảm bảo thư mục cha của file zip đích tồn tại
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zipf:
                if p.is_file():
                    zipf.write(p, p.name)
                else:
                    for root, dirs, files in os.walk(p):
                        for file in files:
                            file_path = Path(root) / file
                            # Lưu đường dẫn tương đối trong zip
                            arcname = file_path.relative_to(p.parent)
                            zipf.write(file_path, arcname)
            return ok(f"Đã nén '{p.name}' thành công thành file zip tại '{dest}'", {"dest_path": str(dest)})
        except Exception as e:
            return fail(f"Lỗi khi nén '{p}': {e}")

    elif act == "unzip":
        if not zipfile.is_zipfile(p):
            return fail(f"File không phải định dạng zip hợp lệ: '{p}'")

        # Xác định thư mục đích để giải nén
        if dest_path:
            dest = Path(dest_path.strip())
        else:
            # Giải nén vào thư mục cùng tên với file zip ở cùng cấp
            dest = p.parent / p.stem

        try:
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(p, "r") as zipf:
                zipf.extractall(dest)
            return ok(f"Đã giải nén file '{p.name}' vào thư mục '{dest}'", {"dest_path": str(dest)})
        except Exception as e:
            return fail(f"Lỗi khi giải nén '{p}': {e}")

    return fail("Hành động không được hỗ trợ.")
