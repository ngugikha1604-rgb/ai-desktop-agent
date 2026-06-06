"""kill_process — kết thúc process theo tên hoặc PID."""
from __future__ import annotations

import psutil

from tools.result import fail, ok

_TERMINATE_TIMEOUT = 3  # giây chờ sau terminate() trước khi dùng kill()


def kill_process(name_or_pid: str | int) -> dict:
    """Kết thúc process theo tên hoặc PID.

    Thử terminate() (SIGTERM) trước. Nếu process không dừng
    sau _TERMINATE_TIMEOUT giây, dùng kill() (SIGKILL) để buộc dừng.
    """
    target = str(name_or_pid).strip() if name_or_pid is not None else ""
    if not target:
        return fail("Cần truyền tên process hoặc PID.")

    # Thử parse PID
    pid: int | None = None
    try:
        pid = int(target)
    except ValueError:
        pass

    killed: list[str] = []
    not_found = True

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            info = proc.info
            match = (pid is not None and info["pid"] == pid) or (
                pid is None and target.lower() in (info["name"] or "").lower()
            )
            if not match:
                continue
            not_found = False

            # Giai đoạn 1: SIGTERM — cho process tự dọn dẹp
            proc.terminate()
            try:
                proc.wait(timeout=_TERMINATE_TIMEOUT)
            except psutil.TimeoutExpired:
                # Giai đoạn 2: SIGKILL — buộc dừng nếu process không phản hồi
                proc.kill()

            killed.append(f"{info['name']} (PID {info['pid']})")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not_found:
        return fail(f"Không tìm thấy process '{name_or_pid}'.")
    if not killed:
        return fail(
            f"Tìm thấy process '{name_or_pid}' nhưng không thể kết thúc (Access Denied)."
        )

    return ok(f"Đã kết thúc: {', '.join(killed)}.", {"killed": killed})
