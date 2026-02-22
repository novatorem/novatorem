#!/usr/bin/env python3
"""
One-stop development launcher for Novatorem.

Usage:
    python start.py          # create venv, install deps, start server, open browser
    python start.py --no-open  # same but skip opening the browser

What it does:
    1. Creates a .venv virtual environment (if it doesn't already exist)
    2. Installs / updates dependencies from requirements.txt
    3. Starts the Flask development server on http://127.0.0.1:5000
    4. Opens http://127.0.0.1:5000/preview in your default browser
    5. Press Ctrl+C to stop.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "5000"))
PREVIEW_URL = f"http://{HOST}:{PORT}/preview"


# ── helpers ──────────────────────────────────────────────────────────────


def _python() -> Path:
    """Return the Python executable inside the venv."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _pip() -> Path:
    """Return the pip executable inside the venv."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


# ── steps ────────────────────────────────────────────────────────────────


def ensure_venv() -> None:
    """Create a virtual environment if one doesn't exist yet."""
    if VENV_DIR.exists():
        print(f"  [ok] Virtual environment found at {VENV_DIR}")
        return
    print("  [..] Creating virtual environment …")
    venv.create(str(VENV_DIR), with_pip=True)
    print(f"  [ok] Virtual environment created at {VENV_DIR}")


def install_deps() -> None:
    """Install / update dependencies from requirements.txt."""
    print("  [..] Installing dependencies …")
    subprocess.check_call(
        [str(_pip()), "install", "-q", "-r", str(REQUIREMENTS)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
    )
    print("  [ok] Dependencies up to date")


def start_server(open_browser: bool = True) -> None:
    """Start the Flask dev server and optionally open the preview page."""
    env = os.environ.copy()
    env["FLASK_APP"] = "api.orchestrator"
    env["FLASK_DEBUG"] = "1"
    env["PORT"] = str(PORT)

    print(f"\n  Starting Flask on http://{HOST}:{PORT}")
    print(f"  Preview page:    {PREVIEW_URL}")
    print("  Press Ctrl+C to stop.\n")

    proc = subprocess.Popen(
        [str(_python()), "-m", "api.orchestrator"],
        cwd=str(ROOT),
        env=env,
    )

    if open_browser:
        # Give the server a moment to bind the port
        time.sleep(2)
        webbrowser.open(PREVIEW_URL)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  Shutting down …")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# ── main ─────────────────────────────────────────────────────────────────


def main() -> None:
    open_browser = "--no-open" not in sys.argv

    print("\n╔══════════════════════════════════════╗")
    print("║   Novatorem — Dev Launcher           ║")
    print("╚══════════════════════════════════════╝\n")

    os.chdir(str(ROOT))
    ensure_venv()
    install_deps()
    start_server(open_browser=open_browser)


if __name__ == "__main__":
    main()
