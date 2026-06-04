"""DesktopApp — dây nối toàn bộ UI, Agent, STT, hotkey."""
from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from agent import Agent
from agent.logger import get_logger
from agent.stt_engine import STTEngine
from ui.command_bar import CommandBar
from ui.hotkey import HOTKEY_LABEL, GlobalHotkey
from ui.stt_worker import SttWorker
from ui.tray import TrayIcon
from ui.worker import AgentWorker

log = get_logger(__name__)


class DesktopApp:
    def __init__(self) -> None:
        self._agent  = Agent()
        self._worker: AgentWorker | None = None

        # ── UI ──────────────────────────────────────────────────────
        self._bar = CommandBar()
        self._bar.submitted.connect(self._on_submit)
        self._bar.voice_toggle.connect(self._on_voice_toggle)

        # ── Hotkeys ─────────────────────────────────────────────────
        self._hotkey = GlobalHotkey()
        self._hotkey.triggered.connect(self._bar.toggle)
        self._hotkey.voice_triggered.connect(self._on_voice_toggle)

        # ── Tray ────────────────────────────────────────────────────
        self._tray = TrayIcon(
            on_show_command_bar=self._bar.show_bar,
            on_quit=QApplication.instance().quit,
        )

        # ── STT (khởi tạo lazy — không tải model ở đây) ─────────────
        self._stt_engine: STTEngine | None = None
        self._stt_worker: SttWorker | None = None
        self._init_stt()

        # ── Memory callback ─────────────────────────────────────────
        self._agent.on_memory_saved = self._on_memory_saved

    # ── Initialization ─────────────────────────────────────────────────

    def _init_stt(self) -> None:
        """Chỉ kiểm tra faster-whisper có được cài chưa.
        Model KHÔNG được tải ở đây — tải lần đầu khi user dùng voice.
        """
        try:
            engine = STTEngine()
            if engine.importable:
                self._stt_engine = engine
                log.debug("[App] STTEngine sẵn sàng (model chưa load, sẽ load khi dùng).")
            else:
                self._bar.disable_mic(
                    "faster-whisper chưa cài. Chạy: pip install faster-whisper"
                )
        except Exception as e:
            log.warning("[App] STT init lỗi: %s", e)
            self._bar.disable_mic(str(e))

    def setup(self) -> None:
        app = QApplication.instance()
        app.installNativeEventFilter(self._hotkey)

        # Lấy HWND sau khi window khởi tạo
        self._bar.show()
        hwnd = self._bar.win_hwnd()
        self._bar.hide()

        if not self._hotkey.register_default(hwnd):
            log.warning("Không đăng ký được hotkey %s.", HOTKEY_LABEL)

        self._tray.show()
        self._tray.showMessage(
            "AI Desktop Agent",
            f"Đang chạy nền. Nhấn {HOTKEY_LABEL} để mở.",
            self._tray.MessageIcon.Information,
            3000,
        )

        # Kiểm tra profile sau 500ms (đợi event loop ổn định)
        QTimer.singleShot(500, self._check_user_profile)

    # ── User profile ───────────────────────────────────────────────────

    def _check_user_profile(self) -> None:
        try:
            profile = self._agent.memory.get_user_profile()
            if not profile.get("display_name", ""):
                self._bar.show_bar()
                entered = self._bar.show_name_dialog()
                if entered is not None:
                    truncated = self._agent.memory.save_user_profile(
                        display_name=entered
                    )
                    if truncated:
                        self._bar.show_response(
                            "Tên đã được cắt ngắn xuống 100 ký tự."
                        )
        except Exception as e:
            log.warning("[App] Lỗi kiểm tra profile: %s", e)

    # ── Agent submission ───────────────────────────────────────────────

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
        self._bar.show_response(error)

    # ── Memory notification ────────────────────────────────────────────

    def _on_memory_saved(self, saved_items: list[dict]) -> None:
        # Chuyển về main thread qua QTimer.singleShot (thread-safe)
        QTimer.singleShot(0, lambda: self._bar.show_memory_notice(saved_items))

    # ── Voice input ────────────────────────────────────────────────────

    def _on_voice_toggle(self) -> None:
        if self._stt_engine is None:
            self._bar.show_response(
                "Không thể truy cập microphone. "
                "Hãy kiểm tra quyền truy cập trong Settings → Privacy → Microphone."
            )
            return

        # Đang ghi → dừng/huỷ
        if self._stt_worker and self._stt_worker.isRunning():
            self._stt_worker.stop()
            self._bar.set_recording(False)
            return

        # Agent đang bận → bỏ qua
        if self._worker and self._worker.isRunning():
            return

        # Hiện bar nếu đang ẩn
        if not self._bar.isVisible():
            self._bar.show_bar()

        self._start_recording()

    def _start_recording(self) -> None:
        from agent.config import load_settings
        try:
            preferred = load_settings().get("preferred_microphone", None)
        except Exception:
            preferred = None

        self._stt_worker = SttWorker(self._stt_engine, preferred_device=preferred)
        self._stt_worker.transcribed.connect(self._on_stt_done)
        self._stt_worker.error_occurred.connect(self._on_stt_error)
        self._stt_worker.cancelled.connect(self._on_stt_cancelled)
        self._bar.set_recording(True)
        self._stt_worker.start()

    def _on_stt_done(self, text: str) -> None:
        self._bar.set_recording(False)
        if text:
            self._bar.fill_and_submit(text)

    def _on_stt_error(self, msg: str) -> None:
        self._bar.set_recording(False)
        self._bar.show_response(msg)

    def _on_stt_cancelled(self) -> None:
        self._bar.set_recording(False)

    # ── Shutdown ───────────────────────────────────────────────────────

    def shutdown(self) -> None:
        self._hotkey.unregister()
        if self._stt_worker and self._stt_worker.isRunning():
            self._stt_worker.stop()
            self._stt_worker.wait(2000)


def run_desktop() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("AI Desktop Agent")

    desktop = DesktopApp()
    desktop.setup()

    code = app.exec()
    desktop.shutdown()
    sys.exit(code)
