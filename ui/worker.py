from PySide6.QtCore import QThread, Signal

from agent import Agent


class AgentWorker(QThread):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, agent: Agent, message: str) -> None:
        super().__init__()
        self._agent = agent
        self._message = message

    def run(self) -> None:
        try:
            self.finished.emit(self._agent.run(self._message))
        except Exception as exc:
            self.failed.emit(str(exc))
