COMMAND_BAR_STYLE = """

/* ── root panel ───────────────────────────────────────── */
QWidget#CommandBarRoot {
    background-color: #11131a;
    border: 1px solid #2b3140;
    border-radius: 18px;
}

/* ── chat area ────────────────────────────────────────── */
QScrollArea#ChatScroll {
    background: transparent;
    border: none;
}

QWidget#ChatWidget {
    background: transparent;
}

QWidget#Divider {
    background-color: #252b36;
}

/* ── response text ────────────────────────────────────── */
QLabel#ResponseText {
    color: #d7deea;
    font-size: 13px;
    line-height: 1.5;
    background: transparent;
    border: none;
    padding: 9px 12px;
}

QLabel#ResponseText[text="●  ●  ●"] {
    color: #7e8ba3;
    font-size: 11px;
    letter-spacing: 4px;
}

/* ── input ────────────────────────────────────────────── */
QWidget#InputWrap {
    background: transparent;
}

QLineEdit#CommandInput {
    background-color: #181b24;
    border: 1px solid #303746;
    border-radius: 12px;
    color: #eef2f8;
    font-size: 13px;
    padding: 11px 14px;
    selection-background-color: #2f6fed;
}

QLineEdit#CommandInput:focus {
    border-color: #4f8cff;
    background-color: #1b202b;
}

QLineEdit#CommandInput:disabled {
    color: #6d7585;
}

QPushButton#SendButton {
    background-color: #e7edf6;
    border: none;
    border-radius: 12px;
    color: #111827;
    font-size: 18px;
    font-weight: 600;
}

QPushButton#SendButton:hover {
    background-color: #f5f8fc;
}

QPushButton#SendButton:pressed {
    background-color: #d4deeb;
}

QPushButton#SendButton:disabled {
    background-color: #252b36;
    color: #657085;
}

/* ── scrollbar ────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 4px;
    margin: 0;
    border: none;
}

QScrollBar::handle:vertical {
    background: #3a4558;
    border-radius: 2px;
    min-height: 24px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    border: none;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
