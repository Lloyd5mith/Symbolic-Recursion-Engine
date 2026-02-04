# -*- coding: utf-8 -*-
"""
I/O Handler — Symbolic Log Interface v2
Author: Lloyd Christopher Smith
"""

import os
import datetime
from colorama import Fore, Style, init

# Initialize colorama for Windows
init(autoreset=True)

LOG_PATH = "data/log.txt"

# ---------- CORE LOGGING ----------

def log(message, color=Fore.CYAN):
    """Logs messages to both console and file with symbolic timestamp."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    
    # Print with color in terminal
    print(color + formatted + Style.RESET_ALL)
    
    # Write to persistent log
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

# ---------- ENHANCED DISPLAY ----------

def show_summary(memory):
    """Displays symbolic link summary at end of each recursion cycle."""
    summary = memory.summarize_links()
    if summary != "no links yet":
        print(Fore.MAGENTA + f"\n🧠  Symbolic Link Summary: {summary}\n" + Style.RESET_ALL)

def divider(text="—", width=50, color=Fore.YELLOW):
    """Prints a symbolic divider for visual separation."""
    line = f"{text * width}"
    print(color + line + Style.RESET_ALL)

