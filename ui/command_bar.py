"""CommandBar — floating window chính của AI Desktop Agent."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.styles import COMMAND_BAR_STYLE, PROFILE_DIALOG_STYLE


class CommandBar(QWidget):
    """Floating command bar — giao diện chính của agent."""

    submitted    = Signal(str)
    voice_toggle = Signal()   # Yêu cầu bật/tắt voice từ app.py

    WIDTH           = 460
    MAX_CHAT_HEIGHT = 300
    MARGIN_RIGHT    = 20
    MARGIN_BOTTOM   = 20

    def __init__(self) -> None:
        super().__init__()
        self._busy      = False
        self._recording = False
        self._blink_on  = True

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._on_blink)

        self._setup_window()
        self._build_ui()
        self.setStyleSheet(COMMAND_BAR_STYLE)

    # ── Window setup ──────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setObjectName("CommandBarRoot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedWidth(self.WIDTH)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
        shadow.setColor(Qt.GlobalColor.black)
        self.setGraphicsEffect(shadow)

        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self._on_esc)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(0)

        # ── Response area ─────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setObjectName("ChatScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setMaximumHeight(self.MAX_CHAT_HEIGHT)
        self._scroll.setVisible(False)

        self._response_label = QLabel()
        self._response_label.setObjectName("ResponseText")
        self._response_label.setWordWrap(True)
        self._response_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._response_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )

        self._memory_label = QLabel()
        self._memory_label.setObjectName("MemoryNotice")
        self._memory_label.setWordWrap(True)
        self._memory_label.setVisible(False)

        rw = QWidget()
        rw.setObjectName("ResponseWidget")
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(4, 6, 6, 6)
        rl.setSpacing(2)
        rl.addWidget(self._response_label)
        rl.addWidget(self._memory_label)
        rl.addStretch(1)

        self._scroll.setWidget(rw)
        outer.addWidget(self._scroll)

        # ── Divider ───────────────────────────────────────────────────
        self._divider = QWidget()
        self._divider.setObjectName("Divider")
        self._divider.setFixedHeight(1)
        self._divider.setVisible(False)
        outer.addWidget(self._divider)

        # ── Input row ─────────────────────────────────────────────────
        input_wrap = QWidget()
        input_wrap.setObjectName("InputWrap")
        row = QHBoxLayout(input_wrap)
        row.setContentsMargins(0, 10, 0, 0)
        row.setSpacing(6)

        self._input = QLineEdit()
        self._input.setObjectName("CommandInput")
        self._input.setPlaceholderText("Nhắn gì đó…")
        self._input.returnPressed.connect(self._on_submit)
        row.addWidget(self._input)

        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setObjectName("MicButton")
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Nhập bằng giọng nói (Ctrl+Alt+V)")
        self._mic_btn.setFixedSize(42, 42)
        self._mic_btn.clicked.connect(self.voice_toggle.emit)
        row.addWidget(self._mic_btn)

        self._send_button = QPushButton("↵")
        self._send_button.setObjectName("SendButton")
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.setToolTip("Gửi")
        self._send_button.setFixedSize(42, 42)
        self._send_button.clicked.connect(self._on_submit)
        row.addWidget(self._send_button)

        outer.addWidget(input_wrap)

    # ── Event handlers ────────────────────────────────────────────────

    def _on_esc(self) -> None:
        if self._recording:
            self.voice_toggle.emit()   # huỷ recording
        else:
            self.hide_bar()

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if not text or self._busy:
            return
        self._input.clear()
        self.submitted.emit(text)

    def _on_blink(self) -> None:
        self._blink_on = not self._blink_on
        val = "on" if self._blink_on else "off"
        self._mic_btn.setProperty("blink", val)
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)

    # ── Helpers ───────────────────────────────────────────────────────

    def _refresh_geometry(self) -> None:
        self._scroll.widget().adjustSize()
        self._scroll.widget().updateGeometry()
        self._scroll.updateGeometry()
        self.adjustSize()
        self._reposition()
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _reposition(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.move(
            geo.right() - self.width()  - self.MARGIN_RIGHT,
            geo.bottom() - self.height() - self.MARGIN_BOTTOM,
        )

    def _set_recording_style(self) -> None:
        val = "true" if self._recording else "false"
        for w in (self, self._input, self._mic_btn):
            w.setProperty("recording", val)
            w.style().unpolish(w)
            w.style().polish(w)

    # ── Public API ────────────────────────────────────────────────────

    def toggle(self) -> None:
        self.hide_bar() if self.isVisible() else self.show_bar()

    def show_bar(self) -> None:
        self.show()
        self._reposition()
        self.raise_()
        self.activateWindow()
        self._input.setFocus()

    def hide_bar(self) -> None:
        self.hide()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._input.setEnabled(not busy)
        self._send_button.setEnabled(not busy)
        if not self._recording:
            self._mic_btn.setEnabled(not busy)
        self._input.setPlaceholderText("Đang xử lý…" if busy else "Nhắn gì đó…")

        if busy:
            self._response_label.setText("●  ●  ●")
            self._memory_label.setVisible(False)
            self._scroll.setVisible(True)
            self._divider.setVisible(True)
        else:
            if self._response_label.text() == "●  ●  ●":
                self._response_label.clear()
                self._scroll.setVisible(False)
                self._divider.setVisible(False)
        QTimer.singleShot(30, self._refresh_geometry)

    def show_response(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._response_label.setText(text)
        self._memory_label.setVisible(False)
        self._scroll.setVisible(True)
        self._divider.setVisible(True)
        QTimer.singleShot(30, self._refresh_geometry)

    def show_memory_notice(self, items: list[dict]) -> None:
        """Hiển thị thông báo 'Đã ghi nhớ' sau phản hồi chính, tự ẩn sau 6s."""
        if not items:
            return
        lines = [f"📌 Đã ghi nhớ: {i['key']} = {i['value']}" for i in items]
        self._memory_label.setText("\n".join(lines))
        self._memory_label.setVisible(True)
        QTimer.singleShot(30, self._refresh_geometry)
        QTimer.singleShot(6000, lambda: self._memory_label.setVisible(False))

    def clear_response(self) -> None:
        self._response_label.clear()
        self._memory_label.setVisible(False)
        self._scroll.setVisible(False)
        self._divider.setVisible(False)
        QTimer.singleShot(30, self._refresh_geometry)

    def set_recording(self, active: bool) -> None:
        """Bật/tắt trạng thái ghi âm — cập nhật toàn bộ UI."""
        self._recording = active
        self._set_recording_style()
        if active:
            self._blink_timer.start()
            self._input.setPlaceholderText("🔴 Đang nghe…")
            self._send_button.setEnabled(False)
        else:
            self._blink_timer.stop()
            self._blink_on = True
            self._mic_btn.setProperty("blink", "on")
            self._set_recording_style()
            self._input.setPlaceholderText("Nhắn gì đó…")
            if not self._busy:
                self._send_button.setEnabled(True)
                self._mic_btn.setEnabled(True)

    def fill_and_submit(self, text: str) -> None:
        """Điền văn bản STT vào input rồi tự gửi."""
        text = text.strip()
        if not text:
            return
        self._input.setText(text)
        self._on_submit()

    def disable_mic(self, reason: str = "") -> None:
        """Vô hiệu hoá nút mic (khi không có microphone hoặc STT lỗi)."""
        self._mic_btn.setEnabled(False)
        self._mic_btn.setToolTip(reason or "Microphone không khả dụng")

    def win_hwnd(self) -> int:
        return int(self.winId())

    # ── Profile dialog (Req 5) ─────────────────────────────────────────

    def show_name_dialog(self) -> str | None:
        """Hộp thoại hỏi tên lần đầu. Trả về tên hoặc None nếu bỏ qua."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Xin chào!")
        dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dlg.setStyleSheet(PROFILE_DIALOG_STYLE)
        dlg.setFixedWidth(320)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        lbl = QLabel("Bạn tên gì?\n(Nhấn Enter để bỏ qua)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Nhập tên của bạn…")
        name_input.setMaxLength(100)
        layout.addWidget(name_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        skip_btn = QPushButton("Bỏ qua")
        skip_btn.setObjectName("SkipButton")
        skip_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(skip_btn)

        ok_btn = QPushButton("Xác nhận")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)
        name_input.returnPressed.connect(dlg.accept)

        # Hiển thị phía trên CommandBar
        dlg.adjustSize()
        bar = self.geometry()
        dlg.move(
            bar.x() + (bar.width() - dlg.width()) // 2,
            bar.y() - dlg.height() - 10,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            return name_input.text().strip()
        return None
