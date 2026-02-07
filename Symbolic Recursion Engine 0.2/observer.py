# observer.py
# -*- coding: utf-8 -*-
"""
Observer — Context + Minimal Integrity Gate
Author: Lloyd Christopher Smith

"""

from __future__ import annotations

import hashlib
import random
import time
from typing import List, Tuple

from memory import Memory


class Observer:
    def __init__(self, name: str = "Mirror-1"):
        self.name = name
        self.tick = 0

    def _sig(self, texts: List[str]) -> str:
        if not texts:
            return "empty"
        joined = "||".join(texts[-5:])
        h = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return h[:8]

    def context(self, memory: Memory) -> str:
        self.tick += 1
        last = [e.text for e in memory.events[-3:]]
        sig = self._sig(last)
        entropy = random.randint(1, 9)
        t = int(time.time()) % 10000
        return f"{self.name}[{self.tick}]::ctx-{sig}::E{entropy}::T{t}"

    def allow(self, text: str) -> bool:
        if not text:
            return False
        if len(text) > 800:
            return False
        return True
