import psutil

from tools.result import fail, ok


def _bytes_to_gb(value: int) -> float:
    return round(value / (1024**3), 2)


def get_system_info() -> dict:
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        ram_used_gb = _bytes_to_gb(mem.used)
        ram_total_gb = _bytes_to_gb(mem.total)
        disk_used_gb = _bytes_to_gb(disk.used)
        disk_total_gb = _bytes_to_gb(disk.total)

        message = (
            f"CPU: {cpu_percent}% | "
            f"RAM: {ram_used_gb}/{ram_total_gb} GB ({mem.percent}%) | "
            f"Disk C: {disk_used_gb}/{disk_total_gb} GB ({disk.percent}% used)"
        )
        data = {
            "cpu_percent": cpu_percent,
            "ram": {
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "percent": mem.percent,
            },
            "disk_c": {
                "used_gb": disk_used_gb,
                "total_gb": disk_total_gb,
                "percent": disk.percent,
            },
        }
        return ok(message, data)
    except Exception as exc:
        return fail(f"Không lấy được thông tin hệ thống: {exc}")
