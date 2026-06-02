import subprocess

from tools.result import fail, ok

_PS_NOTIFY = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(4000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Milliseconds 5000
$notify.Dispose()
"""


def send_notification(title: str, message: str) -> dict:
    """Hiển thị Windows balloon notification (toast) ở góc taskbar."""
    t = (title or "AI Agent").replace("'", "\\'")
    m = (message or "").replace("'", "\\'")

    ps_script = _PS_NOTIFY.format(title=t, message=m)

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return ok(f"Đã gửi thông báo: '{title}'.", {"title": title, "message": message})
    except Exception as exc:
        return fail(f"Không gửi được thông báo: {exc}")
