import os
import subprocess

from tools.result import fail, ok

DEFAULT_TIMEOUT = 60
MAX_OUTPUT_CHARS = 4000


def _trim_output(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n...(đã cắt bớt)"


def run_command(command: str, cwd: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    cmd = (command or "").strip()
    if not cmd:
        return fail("Lệnh trống.")

    work_dir = None
    if cwd:
        work_dir = cwd.strip()
        if not work_dir or not os.path.isdir(work_dir):
            return fail(f"Thư mục làm việc không hợp lệ: {cwd}")

    try:
        completed = subprocess.run(
            cmd,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout)),
        )
    except subprocess.TimeoutExpired:
        return fail(f"Lệnh quá thời gian ({timeout}s): {cmd}")
    except OSError as exc:
        return fail(f"Không chạy được lệnh: {exc}")
    except ValueError:
        return fail(f"Timeout không hợp lệ: {timeout}")

    stdout = _trim_output(completed.stdout or "")
    stderr = _trim_output(completed.stderr or "")
    data = {
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

    if completed.returncode == 0:
        detail = stdout or stderr or "(không có output)"
        return ok(f"Lệnh thành công (code 0):\n{detail}", data)

    detail = stderr or stdout or f"exit code {completed.returncode}"
    return fail(f"Lệnh thất bại (code {completed.returncode}):\n{detail}", data)
