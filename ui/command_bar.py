from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
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

from ui.styles import COMMAND_BAR_STYLE


class CommandBar(QWidget):
    """Floating command bar — displays chatbot responses and takes input."""

    submitted = Signal(str)

    WIDTH = 460
    MAX_CHAT_HEIGHT = 300
    MARGIN_RIGHT = 20
    MARGIN_BOTTOM = 20

    def __init__(self) -> None:
        super().__init__()
        self._busy = False
        self._setup_window()
        self._build_ui()
        self.setStyleSheet(COMMAND_BAR_STYLE)

    # ── setup ──────────────────────────────────────────────────────────

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
        esc.activated.connect(self.hide_bar)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(0)

        # ── Chatbot response area ─────────────────────────────────────
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
        self._response_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._response_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        
        response_widget = QWidget()
        response_widget.setObjectName("ResponseWidget")
        response_layout = QVBoxLayout(response_widget)
        response_layout.setContentsMargins(4, 6, 6, 6)
        response_layout.setSpacing(2)
        response_layout.addWidget(self._response_label)
        response_layout.addStretch(1)

        self._scroll.setWidget(response_widget)
        outer.addWidget(self._scroll)

        # ── Divider ───────────────────────────────────────────────────
        self._divider = QWidget()
        self._divider.setObjectName("Divider")
        self._divider.setFixedHeight(1)
        self._divider.setVisible(False)
        outer.addWidget(self._divider)

        # ── Input ─────────────────────────────────────────────────────
        input_wrap = QWidget()
        input_wrap.setObjectName("InputWrap")
        input_row = QHBoxLayout(input_wrap)
        input_row.setContentsMargins(0, 10, 0, 0)
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("CommandInput")
        self._input.setPlaceholderText("Nhắn gì đó…")
        self._input.returnPressed.connect(self._on_submit)
        input_row.addWidget(self._input)

        self._send_button = QPushButton("↵")
        self._send_button.setObjectName("SendButton")
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.setToolTip("Gửi")
        self._send_button.setFixedSize(42, 42)
        self._send_button.clicked.connect(self._on_submit)
        input_row.addWidget(self._send_button)

        outer.addWidget(input_wrap)

    # ── internal helpers ───────────────────────────────────────────────

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if not text or self._busy:
            return
        self._input.clear()
        self.submitted.emit(text)

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
        x = geo.right() - self.width() - self.MARGIN_RIGHT
        y = geo.bottom() - self.height() - self.MARGIN_BOTTOM
        self.move(x, y)

    # ── public API (gọi từ app.py) ─────────────────────────────────────

    def toggle(self) -> None:
        if self.isVisible():
            self.hide_bar()
        else:
            self.show_bar()

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
        self._input.setPlaceholderText("Đang xử lý…" if busy else "Nhắn gì đó…")

        if busy:
            self._response_label.setText("●  ●  ●")
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
        self._scroll.setVisible(True)
        self._divider.setVisible(True)
        QTimer.singleShot(30, self._refresh_geometry)

    def clear_response(self) -> None:
        self._response_label.clear()
        self._scroll.setVisible(False)
        self._divider.setVisible(False)
        QTimer.singleShot(30, self._refresh_geometry)

    def win_hwnd(self) -> int:
        return int(self.winId())
