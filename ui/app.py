import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from agent import Agent
from ui.command_bar import CommandBar
from ui.hotkey import HOTKEY_LABEL, GlobalHotkey
from ui.tray import TrayIcon
from ui.worker import AgentWorker


class DesktopApp:
    def __init__(self) -> None:
        self._agent = Agent()
        self._worker: AgentWorker | None = None

        self._bar = CommandBar()
        self._bar.submitted.connect(self._on_submit)

        self._hotkey = GlobalHotkey()
        self._hotkey.triggered.connect(self._bar.toggle)

        self._tray = TrayIcon(
            on_show_command_bar=self._bar.show_bar,
            on_quit=QApplication.instance().quit,
        )

    def setup(self) -> None:
        app = QApplication.instance()
        app.installNativeEventFilter(self._hotkey)

        # HWND hợp lệ sau khi window được tạo (ẩn)
        self._bar.show()
        hwnd = self._bar.win_hwnd()
        self._bar.hide()

        if not self._hotkey.register_default(hwnd):
            QMessageBox.warning(
                None,
                "Hotkey",
                f"Không đăng ký được {HOTKEY_LABEL}.\n"
                "Có thể phím đã được app khác dùng.\n"
                "Vẫn mở được qua icon khay hệ thống.",
            )

        self._tray.show()
        self._tray.showMessage(
            "AI Desktop Agent",
            f"Đang chạy nền. Nhấn {HOTKEY_LABEL} để mở.",
            self._tray.MessageIcon.Information,
            3000,
        )

    def _on_submit(self, message: str) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._bar.clear_response()
        self._bar.set_busy(True)

        self._worker = AgentWorker(self._agent, message)
        self._worker.finished.connect(self._on_agent_done)
        self._worker.failed.connect(self._on_agent_error)
        self._worker.start()

    def _on_agent_done(self, response: str) -> None:
        self._bar.set_busy(False)
        self._bar.show_response(response)

    def _on_agent_error(self, error: str) -> None:
        self._bar.set_busy(False)
        self._bar.show_response(f"Lỗi: {error}")

    def shutdown(self) -> None:
        self._hotkey.unregister()


def run_desktop() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("AI Desktop Agent")

    desktop = DesktopApp()
    desktop.setup()

    code = app.exec()
    desktop.shutdown()
    sys.exit(code)
