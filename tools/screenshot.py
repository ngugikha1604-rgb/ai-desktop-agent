import datetime
from pathlib import Path

from tools.result import fail, ok


def take_screenshot(save_path: str | None = None) -> dict:
    """Chụp toàn bộ màn hình và lưu vào file PNG."""
    try:
        from PIL import ImageGrab
    except ImportError:
        return fail("Thiếu thư viện Pillow. Chạy: pip install Pillow")

    try:
        if save_path:
            dest = Path(save_path.strip())
        else:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = Path.home() / "Desktop" / f"screenshot_{ts}.png"

        dest.parent.mkdir(parents=True, exist_ok=True)

        img = ImageGrab.grab(all_screens=True)
        img.save(str(dest), format="PNG")

        return ok(
            f"Đã chụp màn hình → {dest.name} ({img.width}×{img.height}px).",
            {"path": str(dest), "width": img.width, "height": img.height},
        )
    except Exception as exc:
        return fail(f"Chụp màn hình thất bại: {exc}")
