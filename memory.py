# -*- coding: utf-8 -*-
"""
Memory Module — Mirror-0 Link Engine v2
Author: Lloyd Christopher Smith
"""

import os
import re
from collections import defaultdict
from io_handler import log

class Memory:
    def __init__(self, path="data/memory.txt"):
        self.path = path
        self.data = []
        self.links = defaultdict(int)   # link strength between symbols
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.load()

    # ---------- BASIC I/O ----------

    def load(self):
        """Load all previous reflections into memory."""
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                self.data = [line.strip() for line in f if line.strip()]
        log(f"🧩 Memory loaded: {len(self.data)} entries")

    def save(self):
        """Write the current memory state to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            for entry in self.data:
                f.write(entry + "\n")
        log(f"💾 Memory saved: {len(self.data)} entries")

    # ---------- STORAGE ----------

    def store(self, entry):
        """Store a new symbolic reflection, updating link weights."""
        self.data.append(entry)
        self._update_links(entry)

    # ---------- LINKING & COMPRESSION ----------

    def _extract_symbols(self, text):
        """Extracts [symbols] from reflection strings."""
        return re.findall(r"\[(.*?)\]", text)

    def _update_links(self, entry):
        """Find symbol relationships within a reflection and strengthen them."""
        symbols = self._extract_symbols(entry)
        if len(symbols) >= 2:
            for i in range(len(symbols) - 1):
                a, b = symbols[i], symbols[i + 1]
                self.links[(a, b)] += 1
                self.links[(b, a)] += 1  # bidirectional link
                log(f"🔗 Linked: {a} ↔ {b} (+1)")

    def summarize_links(self, top_n=5):
        """Return the top symbolic link relationships by strength."""
        if not self.links:
            return "no links yet"
        sorted_links = sorted(self.links.items(), key=lambda x: x[1], reverse=True)
        summary = [f"{a} ↔ {b}: {count}" for (a, b), count in sorted_links[:top_n]]
        return ", ".join(summary)

    # ---------- SEMANTIC COMPRESSION ----------

    def compress(self):
        """Trim redundant memory lines, keep only meaningful reflections."""
        if len(self.data) <= 100:
            return
        old_len = len(self.data)
        self.data = self.data[-100:]  # keep last 100 reflections
        log(f"🧹 Memory compressed: {old_len} → {len(self.data)} entries retained.")

