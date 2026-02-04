# -*- coding: utf-8 -*-
"""
Mirror-0 Core Interpreter (Adaptive Loop, Config-Driven + Interactive Mode)
Author: Lloyd Christopher Smith
"""

import os, sys, time, yaml
from memory import Memory
from observer import Observer
from io_handler import log, show_summary, divider

sys.stdout.reconfigure(encoding="utf-8")


def load_config():
    """Load runtime configuration from YAML."""
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Mirror0:
    def __init__(self, config):
        self.config = config
        self.seed_path = config["engine"]["seed_path"]
        self.memory_path = config["engine"]["memory_path"]

        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.seed_path), exist_ok=True)

        self.memory = Memory(self.memory_path)
        self.observer = Observer(config["engine"]["observer_label"])

        if not os.path.exists(self.seed_path):
            with open(self.seed_path, "w", encoding="utf-8") as f:
                f.write("symbolic\nrecursion\norigin\n")

    # ----------------------------------------------------------------------

    def load_seed(self):
        try:
            with open(self.seed_path, "r", encoding="utf-8", errors="ignore") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            log(f"⚠️ Seed file not found: {self.seed_path}")
            return []

    def interpret(self, symbol):
        context = self.observer.reflect(self.memory)
        result = f"[{symbol}] → context({context}) → mem({len(self.memory.data)})"
        self.memory.store(result)
        log(result)
        return result

    def evolve(self):
        """Derive a symbolic reflection from last memory entries."""
        if len(self.memory.data) < 2:
            return "init: mirror0 boot sequence complete"
        last = self.memory.data[-2:]
        return f"Δ reflection: {last[0].split('→')[0]} interacts with {last[1].split('→')[0]}"

    # ----------------------------------------------------------------------

    def recurse(self, cycle):
        delay = self.config["runtime"]["recursion_delay"]
        symbols = self.load_seed()
        log(f"🧠 Cycle {cycle}: loaded {len(symbols)} seed symbols.")

        for s in symbols:
            self.interpret(s)
            time.sleep(delay)

        new_symbol = self.evolve()
        self.memory.store(new_symbol)
        if self.config["runtime"]["auto_save"]:
            self.memory.save()

        log(f"✨ New insight stored: {new_symbol}")
        show_summary(self.memory)
        divider("=")
        log("🔁 Re-looping...\n")

    # ----------------------------------------------------------------------

    def chat(self):
        """Interactive symbolic input mode."""
        print("\n💬 Interactive Mode — type a symbol or phrase ('exit' to quit)\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() == "exit":
                print("🌀 Exiting symbolic dialogue.")
                break
            reflection = self.interpret(user_input)
            print(f"Mirror-0: {reflection}\n")


# ----------------------------------------------------------------------

if __name__ == "__main__":
    config = load_config()
    mirror = Mirror0(config)

    # # Run continuous recursion until interrupted
cycle = 1
try:
    while True:
        mirror.recurse(cycle)
        time.sleep(1)
        cycle += 1
except KeyboardInterrupt:
    print("\n🛑 Mirror‑0 loop manually interrupted. Exiting cleanly.")
    input("Press Enter to close...")




