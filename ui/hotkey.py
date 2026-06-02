import ctypes
from ctypes import wintypes

import win32con
import win32gui
from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

HOTKEY_ID = 0xA1D0
HOTKEY_LABEL = "Ctrl+Alt+J"


class GlobalHotkey(QObject, QAbstractNativeEventFilter):
    """Đăng ký Ctrl+Alt+J toàn hệ thống (Windows)."""

    triggered = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._hwnd: int | None = None
        self._registered = False

    def register(self, hwnd: int, modifiers: int, vk: int) -> bool:
        self.unregister()
        self._hwnd = hwnd
        ok = bool(win32gui.RegisterHotKey(hwnd, HOTKEY_ID, modifiers, vk))
        self._registered = ok
        return ok

    def register_default(self, hwnd: int) -> bool:
        modifiers = win32con.MOD_CONTROL | win32con.MOD_ALT
        return self.register(hwnd, modifiers, ord("J"))

    def unregister(self) -> None:
        if self._hwnd is not None and self._registered:
            try:
                win32gui.UnregisterHotKey(self._hwnd, HOTKEY_ID)
            except Exception:
                pass
        self._registered = False

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if event_type != b"windows_generic_MSG":
            return False, 0

        msg = wintypes.MSG.from_address(int(message))
        if msg.message == win32con.WM_HOTKEY and msg.wParam == HOTKEY_ID:
            self.triggered.emit()
            return True, 0
        return False, 0
