from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ui.hotkey import HOTKEY_LABEL


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        on_show_command_bar,
        on_quit,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_show = on_show_command_bar
        self._on_quit = on_quit

        icon = QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon
        )
        self.setIcon(icon)
        self.setToolTip("AI Desktop Agent")

        menu = QMenu()
        show_action = QAction(f"Mở command bar ({HOTKEY_LABEL})", menu)
        show_action.triggered.connect(self._on_show)
        quit_action = QAction("Thoát", menu)
        quit_action.triggered.connect(self._on_quit)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_show()
