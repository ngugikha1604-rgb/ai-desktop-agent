import psutil

from tools.result import fail, ok


def kill_process(name_or_pid: str | int) -> dict:
    """Kết thúc process theo tên hoặc PID."""
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
            proc.terminate()
            killed.append(f"{info['name']} (PID {info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not_found:
        return fail(f"Không tìm thấy process '{name_or_pid}'.")
    if not killed:
        return fail(f"Tìm thấy process '{name_or_pid}' nhưng không thể kết thúc (Access Denied).")

    return ok(f"Đã kết thúc: {', '.join(killed)}.", {"killed": killed})
