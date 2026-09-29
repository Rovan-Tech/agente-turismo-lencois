"""Hook Notification (opcional): avisa no SO quando o Claude precisa de você."""

from __future__ import annotations

import shutil
import subprocess
import sys

import hook_common as common

TITLE = "Claude Code"


def send(message: str) -> None:
    """Dispara uma notificação nativa, se houver ferramenta disponível."""
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'display notification "{message}" with title "{TITLE}"'
        cmd = ["osascript", "-e", script]
    elif sys.platform.startswith("linux") and shutil.which("notify-send"):
        cmd = ["notify-send", TITLE, message]
    elif sys.platform == "win32" and shutil.which("msg"):
        cmd = ["msg", "*", "/TIME:5", f"{TITLE}: {message}"]
    else:
        return
    subprocess.run(cmd, check=False, timeout=5, capture_output=True)  # noqa: S603  # cmd fixo acima


def main() -> int:
    """Notifica com a mensagem do evento."""
    data = common.read_input()
    message = str(data.get("message") or "Preciso de você")
    send(message.replace('"', "'")[:200])
    return 0


if __name__ == "__main__":
    sys.exit(common.run_safely(main, "notify"))
