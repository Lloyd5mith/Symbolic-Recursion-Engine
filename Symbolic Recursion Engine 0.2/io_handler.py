# io_handler.py
from colorama import Fore, Style, init
import time

init(autoreset=True)

def log(msg, color=None):
    ts = time.strftime("%H:%M:%S")
    c = {"green": Fore.GREEN, "magenta": Fore.MAGENTA, "red": Fore.RED, "cyan": Fore.CYAN}.get(color, "")
    print(f"[{ts}] {c}{msg}{Style.RESET_ALL}")

def divider(ch="="):
    print(ch * 60)

def show_summary(data):
    log("🧠 Summary", "magenta")
    for k, v in data.items():
        print(f" • {k}: {v}")
