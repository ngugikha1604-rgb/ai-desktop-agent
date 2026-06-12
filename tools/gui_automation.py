"""GUI Automation tools -- dieu khien man hinh, chuot, ban phim.

Yeu cau:
  pyautogui  (da co trong requirements.txt)
  pytesseract + Tesseract binary (chi cho screen_ocr):
    pip install pytesseract
    Binary: https://github.com/UB-Mannheim/tesseract/wiki

Neu Tesseract khong nam trong PATH, set duong dan trong settings.json:
    "tesseract_cmd": "C:\\\\Program Files\\\\Tesseract-OCR\\\\tesseract.exe"

Fail-safe pyautogui: di chuot den goc tren-trai de dung khan cap.
"""
from __future__ import annotations

import re
import time

import pyautogui

from tools.result import fail, ok

# Giam delay mac dinh (safety layer xu ly confirmation truoc khi chay)
pyautogui.PAUSE = 0.05


# -- Lazy import pytesseract --------------------------------------------------

_tess = None   # None = chua thu import, False = import that bai


def _get_tess():
    """Lazy-load pytesseract, ap dung tesseract_cmd tu settings neu co."""
    global _tess
    if _tess is None:
        try:
            import pytesseract as _t

            # Doc duong dan Tesseract tu settings (neu co)
            try:
                from agent.config import load_settings
                cmd = load_settings().get("tesseract_cmd")
                if cmd:
                    _t.pytesseract.tesseract_cmd = cmd
            except Exception:
                pass  # settings khong load duoc -> dung PATH mac dinh

            _tess = _t
        except ImportError:
            _tess = False
    return _tess


# -- Tools --------------------------------------------------------------------

def get_screen_size() -> dict:
    """Tra ve kich thuoc man hinh hien tai (pixel)."""
    try:
        w, h = pyautogui.size()
        return ok(f"Kich thuoc man hinh: {w}x{h} px", data={"width": w, "height": h})
    except Exception as e:
        return fail(str(e))


def screen_ocr(x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> dict:
    """Chup man hinh va trich xuat van ban bang OCR.

    Khong truyen tham so -> chup toan man hinh.
    Truyen x, y, width, height de chup vung cu the.
    """
    tess = _get_tess()
    if not tess:
        return fail(
            "pytesseract chua cai.\n"
            "  1. pip install pytesseract\n"
            "  2. Tai Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  3. Neu Tesseract khong trong PATH, set 'tesseract_cmd' trong config/settings.json",
            retryable=False,
        )

    try:
        from PIL import ImageGrab

        region = (x, y, x + width, y + height) if (width > 0 and height > 0) else None
        img    = ImageGrab.grab(bbox=region)

        # psm 3 = fully automatic page segmentation (phu hop man hinh desktop)
        text = tess.image_to_string(img, lang="eng", config="--psm 3").strip()

        if not text:
            loc = f"({x},{y},{width}x{height})" if region else "toan man hinh"
            return ok(f"Khong tim thay van ban tren {loc}.")

        # Trim de tranh token overflow
        if len(text) > 1800:
            text = text[:1800] + "\n...(cat bot, qua 1800 ky tu)"

        loc = f"vung ({x},{y}) {width}x{height}px" if region else "toan man hinh"
        return ok(f"[OCR {loc}]\n{text}")

    except Exception as e:
        return fail(f"OCR that bai: {e}")


def mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> dict:
    """Click chuot tai toa do man hinh (x, y).

    button: 'left' (mac dinh) | 'right' | 'middle'
    double: True de double-click
    """
    try:
        sw, sh = pyautogui.size()
        if not (0 <= x <= sw and 0 <= y <= sh):
            return fail(
                f"Toa do ({x}, {y}) nam ngoai man hinh ({sw}x{sh}).",
                retryable=False,
            )

        btn = button if button in ("left", "right", "middle") else "left"

        if double:
            pyautogui.doubleClick(x, y, button=btn, duration=0.1)
        else:
            pyautogui.click(x, y, button=btn, duration=0.1)

        action = "Double-click" if double else "Click"
        return ok(f"{action} {btn} tai ({x}, {y}) thanh cong.")

    except pyautogui.FailSafeException:
        return fail("Dung khan cap pyautogui (chuot den goc tren-trai man hinh).", retryable=False)
    except Exception as e:
        return fail(f"mouse_click that bai: {e}")


def type_text(text: str) -> dict:
    """Go van ban vao ung dung dang focus.

    Dung clipboard de ho tro day du Unicode va tieng Viet.
    Clipboard cu duoc khoi phuc sau khi go xong.
    """
    if not text:
        return fail("Van ban trong.")

    try:
        import win32clipboard
        import win32con

        # 1. Luu clipboard cu
        old_text: str | None = None
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                old_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

        # 2. Ghi text moi vao clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()

        # 3. Paste vao ung dung dang focus
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.15)

        # 4. Khoi phuc clipboard cu
        if old_text is not None:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_text)
                win32clipboard.CloseClipboard()
            except Exception:
                pass

        return ok(f"Da go {len(text)} ky tu.")

    except pyautogui.FailSafeException:
        return fail("Dung khan cap pyautogui.", retryable=False)
    except Exception as e:
        return fail(f"type_text that bai: {e}")


def key_press(keys: str) -> dict:
    """Nhan phim hoac to hop phim.

    Vi du: 'enter', 'escape', 'tab', 'ctrl+c', 'alt+tab',
           'win+d', 'ctrl+shift+t', 'f5', 'ctrl+z'
    """
    if not keys:
        return fail("Khong co phim nao duoc chi dinh.")

    try:
        parts = [k.strip() for k in re.split(r"[+&]", keys.strip().lower()) if k.strip()]
        if not parts:
            return fail(f"To hop phim khong hop le: '{keys}'.")

        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)

        return ok(f"Da nhan: {keys}.")

    except pyautogui.FailSafeException:
        return fail("Dung khan cap pyautogui.", retryable=False)
    except Exception as e:
        return fail(f"key_press that bai: {e}")
