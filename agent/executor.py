from tools import TOOL_REGISTRY
from tools.result import fail


class Executor:
    """Map task → tool → thực thi."""

    def execute(self, plan: list[dict]) -> list[dict]:
        print(f"\n[Executor] Bắt đầu thực thi {len(plan)} bước trong kế hoạch...")
        results: list[dict] = []
        for i, step in enumerate(plan, 1):
            print(f"[Executor] Thực thi bước {i}/{len(plan)}: {step.get('task', 'N/A')}")
            res = self._run_step(step)
            if res.get("status") == "fail":
                print(f"[Executor] Bước {i} THẤT BẠI: {res.get('message') or 'Lỗi không xác định'}")
            else:
                print(f"[Executor] Bước {i} HOÀN THÀNH THÀNH CÔNG: {res.get('message') or 'Hoàn tất'}")
            results.append(res)
        print(f"[Executor] Đã hoàn thành thực thi toàn bộ kế hoạch.")
        return results

    def _run_step(self, step: dict) -> dict:
        task = step.get("task", "")
        tool_name = step.get("tool")
        args = step.get("args") or {}

        if not isinstance(args, dict):
            err_msg = f"Tham số tool không hợp lệ cho task '{task}'."
            print(f"[Executor] [LỖI]: {err_msg}")
            return fail(err_msg)

        if tool_name and tool_name in TOOL_REGISTRY:
            try:
                print(f"[Executor] Chạy tool '{tool_name}' với args={args}")
                return TOOL_REGISTRY[tool_name](**args)
            except TypeError as exc:
                err_msg = f"Lỗi tham số tool '{tool_name}': {exc}"
                print(f"[Executor] [LỖI]: {err_msg}")
                return fail(err_msg)
            except Exception as exc:
                err_msg = f"Lỗi khi chạy '{tool_name}': {exc}"
                print(f"[Executor] [LỖI]: {err_msg}")
                return fail(err_msg)

        err_msg = f"Task '{task}' chưa gắn tool (tool_name='{tool_name}' không tồn tại hoặc không hợp lệ)."
        print(f"[Executor] [LỖI]: {err_msg}")
        return fail(err_msg, step)
