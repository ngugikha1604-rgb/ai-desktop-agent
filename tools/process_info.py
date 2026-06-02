import psutil

from tools.result import fail, ok


def get_running_processes(name_filter: str | None = None, limit: int = 40) -> dict:
    try:
        needle = (name_filter or "").strip().lower()
        processes: list[dict] = []

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                info = proc.info
                name = info.get("name") or ""
                if needle and needle not in name.lower():
                    continue
                processes.append({"pid": info.get("pid"), "name": name})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        processes.sort(key=lambda item: (item["name"] or "").lower())
        processes = processes[: max(1, limit)]

        if not processes:
            if needle:
                return ok(f"Không có process nào khớp '{name_filter}'.", [])
            return ok("Không lấy được danh sách process.", [])

        lines = [f"- {p['name']} (PID {p['pid']})" for p in processes]
        suffix = f" (lọc: {name_filter})" if needle else ""
        message = f"{len(processes)} process{suffix}:\n" + "\n".join(lines)
        return ok(message, processes)
    except Exception as exc:
        return fail(f"Không lấy được danh sách process: {exc}")
