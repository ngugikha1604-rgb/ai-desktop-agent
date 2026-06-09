"""ConfirmDialog — hộp thoại xác nhận trước khi thực thi hành động nguy hiểm."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from agent.safety import RiskAssessment, RiskLevel
from ui.styles import CONFIRM_DIALOG_STYLE


_LEVEL_COLORS: dict[RiskLevel, str] = {
    RiskLevel.DANGEROUS: "#ed8936",   # cam
    RiskLevel.CRITICAL:  "#e53e3e",   # đỏ
}

_HEADER_TEXT: dict[RiskLevel, str] = {
    RiskLevel.DANGEROUS: "Agent muốn thực hiện hành động này:",
    RiskLevel.CRITICAL:  "⚠ CẢNH BÁO: Hành động có thể gây hại hệ thống!",
}


class ConfirmDialog(QDialog):
    """Dialog xác nhận tool nguy hiểm — luôn chạy trên main thread."""

    def __init__(
        self,
        assessment: RiskAssessment,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Xác nhận hành động")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(CONFIRM_DIALOG_STYLE)
        self.setFixedWidth(380)
        self._build_ui(assessment)
        self._position(parent)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self, a: RiskAssessment) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        # Header: icon + risk level badge
        color = _LEVEL_COLORS.get(a.level, "#ed8936")
        header = QLabel(
            f'<span style="font-size:18px">{a.icon}</span> '
            f'<span style="color:{color};font-weight:bold;font-size:12px;'
            f'letter-spacing:1px">{a.label.upper()}</span>'
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        # Message line
        msg_text = _HEADER_TEXT.get(a.level, "Xác nhận hành động:")
        msg = QLabel(msg_text)
        msg.setObjectName("ConfirmMessage")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Tool call display (monospace box)
        tool_lbl = QLabel(a.display)
        tool_lbl.setObjectName("ConfirmTool")
        tool_lbl.setWordWrap(True)
        layout.addWidget(tool_lbl)

        # Reason explanation
        reason = QLabel(a.reason)
        reason.setObjectName("ConfirmReason")
        reason.setWordWrap(True)
        layout.addWidget(reason)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        deny = QPushButton("✕  Từ chối")
        deny.setObjectName("DenyButton")
        deny.setCursor(Qt.CursorShape.PointingHandCursor)
        deny.clicked.connect(self.reject)
        btn_row.addWidget(deny)

        is_critical = a.level >= RiskLevel.CRITICAL
        allow = QPushButton("✔  Cho phép")
        allow.setObjectName("AllowCriticalButton" if is_critical else "AllowButton")
        allow.setCursor(Qt.CursorShape.PointingHandCursor)
        allow.clicked.connect(self.accept)
        btn_row.addWidget(allow)

        layout.addLayout(btn_row)

    # ── Positioning ───────────────────────────────────────────────────────────

    def _position(self, parent: QWidget | None) -> None:
        """Hiển thị dialog phía trên CommandBar (căn giữa theo chiều ngang)."""
        self.adjustSize()
        if parent and parent.isVisible():
            bar = parent.geometry()
            self.move(
                bar.x() + (bar.width() - self.width()) // 2,
                bar.y() - self.height() - 8,
            )