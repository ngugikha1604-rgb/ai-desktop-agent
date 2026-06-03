"""HotkeyManager — quản lý phím tắt toàn cục (Windows).

Hotkey 1: Ctrl+Alt+J  → bật/tắt CommandBar
Hotkey 2: Ctrl+Alt+V  → bật/tắt chế độ nhập giọng nói
"""
from ctypes import wintypes

import win32con
import win32gui
from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

HOTKEY_ID_TOGGLE = 0xA1D0   # Ctrl+Alt+J
HOTKEY_ID_VOICE  = 0xA1D1   # Ctrl+Alt+V

HOTKEY_LABEL       = "Ctrl+Alt+J"
HOTKEY_VOICE_LABEL = "Ctrl+Alt+V"


class GlobalHotkey(QObject, QAbstractNativeEventFilter):
    """Đăng ký Ctrl+Alt+J và Ctrl+Alt+V toàn hệ thống (Windows)."""

    triggered       = Signal()  # Ctrl+Alt+J — toggle CommandBar
    voice_triggered = Signal()  # Ctrl+Alt+V — toggle voice input

    def __init__(self, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._hwnd: int | None = None
        self._registered_ids: list[int] = []

    def register_default(self, hwnd: int) -> bool:
        self.unregister()
        self._hwnd = hwnd
        mods = win32con.MOD_CONTROL | win32con.MOD_ALT

        ok_toggle = bool(win32gui.RegisterHotKey(hwnd, HOTKEY_ID_TOGGLE, mods, ord("J")))
        ok_voice  = bool(win32gui.RegisterHotKey(hwnd, HOTKEY_ID_VOICE,  mods, ord("V")))

        if ok_toggle:
            self._registered_ids.append(HOTKEY_ID_TOGGLE)
        if ok_voice:
            self._registered_ids.append(HOTKEY_ID_VOICE)

        if not ok_toggle:
            import warnings
            warnings.warn(f"Không đăng ký được {HOTKEY_LABEL}")
        if not ok_voice:
            import warnings
            warnings.warn(f"Không đăng ký được {HOTKEY_VOICE_LABEL}")

        return ok_toggle  # hotkey chính

    def unregister(self) -> None:
        if self._hwnd is not None:
            for hid in self._registered_ids:
                try:
                    win32gui.UnregisterHotKey(self._hwnd, hid)
                except Exception:
                    pass
        self._registered_ids.clear()

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if event_type != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == win32con.WM_HOTKEY:
            if msg.wParam == HOTKEY_ID_TOGGLE:
                self.triggered.emit()
                return True, 0
            if msg.wParam == HOTKEY_ID_VOICE:
                self.voice_triggered.emit()
                return True, 0
        return False, 0
