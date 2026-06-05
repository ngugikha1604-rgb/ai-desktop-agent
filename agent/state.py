"""AgentState — lưu trạng thái của agent trong một vòng lặp."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentState:
    """Trạng thái xuyên suốt Agent Loop.

    Attributes:
        goal:               Mục tiêu tóm tắt (từ Task Analyzer).
        user_name:          Tên người dùng nếu đã biết.
        history:            Các bước đã thực hiện: [{"action": dict, "observation": str}]
        observation:        Kết quả bước vừa thực thi (string ngắn, truncated).
        step_count:         Số bước đã thực hiện.
        tasks:              Danh sách subtask: [{"task": str, "status": str, "attempts": int}]
        current_task_index: Index của task đang xử lý trong tasks[].
    """

    goal: str
    user_name: str = ""
    history: list[dict] = field(default_factory=list)
    observation: str = ""
    step_count: int = 0
    tasks: list[dict] = field(default_factory=list)
    current_task_index: int = 0

    # ── Task helpers ──────────────────────────────────────────────────────────

    @property
    def has_tasks(self) -> bool:
        """True nếu state được khởi tạo với task list (Task Analyzer mode)."""
        return bool(self.tasks)

    @property
    def current_task(self) -> str | None:
        """Task hiện tại đang xử lý, hoặc None nếu hết / không có tasks."""
        if self.tasks and self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]["task"]
        return None

    @property
    def current_task_attempts(self) -> int:
        """Số lần đã thử task hiện tại."""
        if self.tasks and self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index].get("attempts", 0)
        return 0

    def all_tasks_done(self) -> bool:
        """True nếu tất cả tasks đã xong (hoặc không có tasks)."""
        return self.current_task_index >= len(self.tasks)

    def mark_current_task_done(self) -> None:
        """Đánh dấu task hiện tại là 'done' và chuyển sang task tiếp theo."""
        if self.tasks and self.current_task_index < len(self.tasks):
            self.tasks[self.current_task_index]["status"] = "done"
        self.current_task_index += 1

    def mark_current_task_failed(self) -> None:
        """Đánh dấu task hiện tại là 'failed' và dừng tại đây."""
        if self.tasks and self.current_task_index < len(self.tasks):
            self.tasks[self.current_task_index]["status"] = "failed"
        self.current_task_index += 1

    def increment_task_attempts(self) -> int:
        """Tăng attempts của task hiện tại lên 1. Trả về số attempts mới."""
        if self.tasks and self.current_task_index < len(self.tasks):
            self.tasks[self.current_task_index]["attempts"] = (
                self.tasks[self.current_task_index].get("attempts", 0) + 1
            )
            return self.tasks[self.current_task_index]["attempts"]
        return 0
