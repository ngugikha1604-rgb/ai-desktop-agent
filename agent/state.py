"""AgentState — lưu trạng thái của agent trong một vòng lặp."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentState:
    """Trạng thái xuyên suốt Agent Loop.

    Attributes:
        goal:        Yêu cầu gốc của người dùng (bất biến trong suốt loop).
        history:     Danh sách các bước đã thực hiện.
                     Mỗi phần tử: {"action": dict, "observation": str}
        observation: Kết quả của bước vừa thực thi (string ngắn).
        step_count:  Số bước đã thực hiện (tăng sau mỗi action).
    """

    goal: str
    history: list[dict] = field(default_factory=list)
    observation: str = ""
    step_count: int = 0
