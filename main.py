import os
import sys

# Reconfigure stdout and stderr to UTF-8 to prevent UnicodeEncodeError on Windows
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel

from agent import Agent

# Bật Flash Attention và KV Cache quantization cho Ollama
# (chỉ có hiệu lực nếu Ollama được khởi động từ cùng process này;
#  nếu ollama serve đã chạy sẵn thì set biến môi trường trước khi chạy:
#  OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve)
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")

app = typer.Typer(help="AI Desktop Agent")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Không truyền lệnh → mở giao diện desktop (mặc định)."""
    if ctx.invoked_subcommand is None:
        from ui import run_desktop

        run_desktop()


@app.command()
def gui() -> None:
    """Chạy agent nền + command bar (Ctrl+Alt+J)."""
    from ui import run_desktop

    run_desktop()


@app.command()
def chat(message: str = typer.Argument(..., help="Yêu cầu gửi tới agent")):
    """Chạy một lệnh và in kết quả (CLI)."""
    agent = Agent()
    response = agent.run(message)
    console.print(Panel(response, title="Agent"))


@app.command()
def repl():
    """Vòng lặp chat đơn giản (thoát: exit / quit)."""
    agent = Agent()
    console.print("[bold]AI Desktop Agent[/] — gõ exit để thoát\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        response = agent.run(user_input)
        console.print(f"[bold green]Agent>[/] {response}\n")


if __name__ == "__main__":
    app()
