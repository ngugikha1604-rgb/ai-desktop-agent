"""AgentWorker — chạy Agent.run() trong QThread với timeout 60 giây."""
from __future__ import annotations

import concurrent.futures

from PySide6.QtCore import QThread, Signal

from agent import Agent

_TIMEOUT_SECONDS = 300


class AgentWorker(QThread):
    finished = Signal(str)
    failed   = Signal(str)

    def __init__(self, agent: Agent, message: str) -> None:
        super().__init__()
        self._agent   = agent
        self._message = message

    def run(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(self._agent.run, self._message)
            try:
                result = future.result(timeout=_TIMEOUT_SECONDS)
                self.finished.emit(result)
            except concurrent.futures.TimeoutError:
                self.failed.emit(
                    "Yêu cầu hết thời gian xử lý (60 giây). Vui lòng thử lại."
                )
            except Exception as exc:
                self.failed.emit(str(exc))
