# -*- coding: utf-8 -*-
"""
Observer Module — Mirror-0 Context Engine
Author: Lloyd Christopher Smith
"""

import hashlib
import random
import time

class Observer:
    def __init__(self, name="Ω-0"):
        self.name = name
        self.tick = 0

    def _generate_context_signature(self, data):
        """
        Builds a short symbolic hash of the system's memory to simulate reflection.
        """
        if not data:
            return "empty-memory"

        recent = "".join(data[-3:])  # last few memories
        hashed = hashlib.sha256(recent.encode("utf-8")).hexdigest()
        sig = hashed[:6]  # short symbolic fingerprint
        return f"ctx-{sig}"

    def reflect(self, memory):
        """
        Reflects on current system state.
        Each reflection updates a tick and generates a symbolic context signature.
        """
        self.tick += 1
        base_context = self._generate_context_signature(memory.data)
        entropy = random.randint(1, 9)
        timestamp = int(time.time()) % 10000
        reflection = f"{self.name}[{self.tick}]::{base_context}::E{entropy}::T{timestamp}"
        return reflection

