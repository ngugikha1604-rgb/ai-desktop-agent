import win32clipboard

from tools.result import fail, ok


def get_clipboard() -> dict:
    """Đọc nội dung văn bản từ clipboard."""
    try:
        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return ok("Clipboard không chứa văn bản.", None)
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        if not text:
            return ok("Clipboard đang trống.", "")
        preview = text[:200] + ("..." if len(text) > 200 else "")
        return ok(f"Clipboard: {preview}", {"text": text, "length": len(text)})
    except Exception as exc:
        return fail(f"Không đọc được clipboard: {exc}")


def set_clipboard(text: str) -> dict:
    """Ghi văn bản vào clipboard."""
    content = str(text or "")
    try:
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(content, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
        preview = content[:100] + ("..." if len(content) > 100 else "")
        return ok(f"Đã copy vào clipboard: {preview}", {"length": len(content)})
    except Exception as exc:
        return fail(f"Không ghi được clipboard: {exc}")
