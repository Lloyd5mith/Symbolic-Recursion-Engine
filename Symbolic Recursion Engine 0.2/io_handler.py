# io_handler.py
# -*- coding: utf-8 -*-
"""
I/O Handler — Symbolic Log Interface v3 (no-fragile deps)
Author: Lloyd Christopher Smith

"""

from __future__ import annotations

import os
import datetime
from typing import Any, Dict, Optional

LOG_PATH = "data/log.txt"

# Optional color (works even if colorama isn't installed)
try:
    from colorama import Fore, Style, init  # type: ignore
    init(autoreset=True)
    _C = {
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "yellow": Fore.YELLOW,
        "red": Fore.RED,
        "green": Fore.GREEN,
        "reset": Style.RESET_ALL,
    }
except Exception:
    _C = {k: "" for k in ["cyan", "magenta", "yellow", "red", "green", "reset"]}


def log(message: str, color: str = "cyan") -> None:
    """Log to console + file with timestamp."""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {message}"

    col = _C.get(color, "")
    reset = _C.get("reset", "")
    print(f"{col}{formatted}{reset}")

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def divider(ch: str = "—", width: int = 70, color: str = "yellow") -> None:
    line = ch * width
    col = _C.get(color, "")
    reset = _C.get("reset", "")
    print(f"{col}{line}{reset}")


def show_summary(summary: Dict[str, Any]) -> None:
    """Pretty print a small summary dict."""
    log("🧠 Summary", "magenta")
    for k, v in summary.items():
        log(f"  • {k}: {v}", "magenta")
