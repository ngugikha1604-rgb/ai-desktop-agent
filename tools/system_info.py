"""system_info — CPU, RAM, tất cả ổ đĩa thực tế."""
from __future__ import annotations

import psutil

from tools.result import fail, ok


def _gb(b: int) -> float:
    return round(b / 1024**3, 1)


def _read_disk(mountpoint: str) -> psutil._common.sdiskusage | None:
    try:
        return psutil.disk_usage(mountpoint)
    except (PermissionError, OSError):
        return None


def get_system_info() -> dict:
    try:
        # interval=0.5 — đủ chính xác mà không block quá lâu
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()

        # Enumerate tất cả partition thực tế (bỏ qua CD/ổ ảo không mount được)
        disks: dict[str, dict] = {}
        disk_parts: list[str] = []
        for part in psutil.disk_partitions(all=False):
            usage = _read_disk(part.mountpoint)
            if usage is None:
                continue
            label = part.mountpoint.rstrip("\\").rstrip("/") or part.device
            disks[label] = {
                "free_gb":  _gb(usage.free),
                "used_gb":  _gb(usage.used),
                "total_gb": _gb(usage.total),
                "percent":  usage.percent,
            }
            disk_parts.append(
                f"Ổ {label}: {_gb(usage.free)} GB trống / {_gb(usage.total)} GB"
            )

        disk_str = " | ".join(disk_parts) if disk_parts else "Không đọc được ổ đĩa"
        message = (
            f"CPU: {cpu_percent}% | "
            f"RAM: {_gb(mem.used)}/{_gb(mem.total)} GB ({mem.percent}%) | "
            f"{disk_str}"
        )

        return ok(message, {
            "cpu_percent": cpu_percent,
            "ram": {
                "used_gb":  _gb(mem.used),
                "total_gb": _gb(mem.total),
                "percent":  mem.percent,
            },
            "disks": disks,
        })

    except Exception as exc:
        return fail(f"Không lấy được thông tin hệ thống: {exc}")
