# mirror0.py
# -*- coding: utf-8 -*-
"""
Symbolic Recursion Engine — Mirror-0 (STABLE + NON-CRASH + LESS REPETITIVE)
Author: Lloyd Christopher Smith
"""

from __future__ import annotations

import os
import sys
import time
import random
import re
from collections import deque
from typing import List, Optional, Tuple, Set, Dict, Any

from memory import Memory, MemEvent
from observer import Observer
from io_handler import log, divider, show_summary

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ================= CONFIG =================

CFG: Dict[str, Any] = {
    # If you want a /data folder, change these to "data/seed.txt" etc.
    "seed_path": "seed.txt",
    "memory_events": "memory.jsonl",
    "memory_graph": "graph.json",
    "max_events": 5000,

    "thoughts_min": 3,
    "thoughts_max": 7,
    "cycle_pause": 0.6,
    "recursion_delay": 0.12,

    # abstraction behaviour
    "insight_chance": 0.55,
    "abstraction_every": 3,     # try abstract every N cycles (stops spam + stabilises)
    "min_pair_support": 6,      # lower = more abstractions, higher = fewer but “stronger”
    "max_abs_depth": 2,         # prevents abs(abs(abs(...)))
    "max_abs_per_100_cycles": 10,

    # anti-repetition / exploration
    "repeat_window": 25,        # avoid reusing same symbols too often
    "explore_chance": 0.28,     # inject seed symbol even when memory is dominant
    "abs_pick_chance": 0.18,    # sometimes pick abstractions once they exist

    # symbol hygiene
    "max_symbol_len": 32,
}

BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")
TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{1,64}")

# ================= HELPERS =================

def ensure_parent(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

def norm(s: str) -> str:
    s = (s or "").strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_\-\(\):]", "", s)
    if not s:
        return "void"
    return s[:CFG["max_symbol_len"]]

def bracket(s: str) -> str:
    return f"[{s}]"

def is_abs(s: str) -> bool:
    return s.startswith("abs(")

def abs_depth(s: str) -> int:
    return s.count("abs(")

def canon_pair(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)

def extract_symbols(text: str) -> List[str]:
    out: List[str] = []

    for b in BRACKET_RE.findall(text):
        s = norm(b)
        if s and not s.isdigit():
            out.append(s)

    if out:
        return out

    for t in TOKEN_RE.findall(text):
        if t.isdigit():
            continue
        s = norm(t)
        if s and not s.isdigit():
            out.append(s)

    return out

def load_seed(seed_path: str) -> List[str]:
    try:
        with open(seed_path, "r", encoding="utf-8", errors="ignore") as f:
            items = [line.strip() for line in f if line.strip()]
        items = [norm(x) for x in items]
        return [x for x in items if x and not x.isdigit()]
    except Exception:
        return []

def ensure_seed(seed_path: str) -> None:
    if os.path.exists(seed_path):
        return
    ensure_parent(seed_path)
    with open(seed_path, "w", encoding="utf-8") as f:
        f.write("\n".join([
            "symbolic", "recursion", "origin", "mirror", "self", "loop",
            # a few extra to prevent “3-word prison”:
            "pattern", "context", "relation", "memory", "difference", "boundary",
            "constraint", "signal", "trace", "bind", "update", "state"
        ]) + "\n")

# ================= ENGINE =================

class Mirror0:
    def __init__(self):
        ensure_seed(CFG["seed_path"])
        self.seed_cache: List[str] = load_seed(CFG["seed_path"])

        self.memory = Memory(
            events_path=CFG["memory_events"],
            graph_path=CFG["memory_graph"],
            max_events=CFG["max_events"],
        )
        self.observer = Observer("Mirror-1")

        self.recent = deque(maxlen=CFG["repeat_window"])
        self.abstracted_pairs: Set[Tuple[str, str]] = set()
        self.abs_rate_window = deque(maxlen=100)  # 1 if abstract happened else 0

    def pick_symbol(self) -> str:
        tops = self.memory.top_symbols(20)
        abstractions = [s for s, _ in tops if is_abs(s) and abs_depth(s) <= CFG["max_abs_depth"]]
        primitives = [s for s, _ in tops if not is_abs(s)]

        # inject seed sometimes to avoid lock-in
        if self.seed_cache and random.random() < CFG["explore_chance"]:
            cands = [s for s in self.seed_cache if s not in self.recent]
            return random.choice(cands) if cands else random.choice(self.seed_cache)

        # sometimes pick an abstraction
        if abstractions and random.random() < CFG["abs_pick_chance"]:
            cands = [a for a in abstractions if a not in self.recent]
            return random.choice(cands) if cands else random.choice(abstractions)

        # otherwise pick a primitive, avoid recent
        if primitives:
            cands = [p for p in primitives if p not in self.recent]
            return random.choice(cands) if cands else random.choice(primitives)

        # fallback
        if self.seed_cache:
            return random.choice(self.seed_cache)
        return "origin"

    def top_pairs(self, limit: int = 60) -> List[Tuple[Tuple[str, str], int]]:
        # use Memory.top_pairs (already present)
        return self.memory.top_pairs(limit)

    def try_abstract(self) -> Optional[str]:
        # rate limit
        if sum(self.abs_rate_window) >= CFG["max_abs_per_100_cycles"]:
            return None

        for (a, b), w in self.top_pairs(80):
            a = norm(a)
            b = norm(b)
            w = int(w)

            if w < CFG["min_pair_support"]:
                continue
            if a == b:
                continue
            if is_abs(a) or is_abs(b):
                continue

            key = canon_pair(a, b)
            if key in self.abstracted_pairs:
                continue

            abs_sym = norm(f"abs({a}_{b})")
            if abs_depth(abs_sym) > CFG["max_abs_depth"]:
                continue

            # link abstraction node strongly enough to be “seen”
            self.memory.link(abs_sym, a, max(2, w // 2))
            self.memory.link(abs_sym, b, max(2, w // 2))

            self.abstracted_pairs.add(key)
            self.abs_rate_window.append(1)

            return f"Δ abstract {bracket(abs_sym)} := {bracket(a)} ⊗ {bracket(b)} (support:{w})"

        self.abs_rate_window.append(0)
        return None

    def cycle(self, n: int) -> None:
        thoughts = random.randint(CFG["thoughts_min"], CFG["thoughts_max"])
        log(f"🧠 Cycle {n} — thoughts:{thoughts}", "green")

        used: List[str] = []

        for _ in range(thoughts):
            s = self.pick_symbol()
            ctx = norm(str(self.observer.context(self.memory)))

            # text format stays simple and parseable
            text = f"{bracket(s)} :: {ctx}"

            # track BOTH s and ctx as symbols so the graph has edges to learn
            syms = [norm(s)]
            if ctx and ctx != "void" and not ctx.isdigit():
                syms.append(ctx)

            ev = MemEvent(
                ts=time.time(),
                kind="reflection",
                text=text,
                meta={"symbols": syms},
            )

            if self.observer.allow(text):
                self.memory.append(ev)
                log(text)

                # strengthen the relationship between s and ctx
                if len(syms) >= 2:
                    self.memory.link(syms[0], syms[1], 1)

            used.append(norm(s))
            self.recent.append(norm(s))

            time.sleep(CFG["recursion_delay"])

        # chain-link within the cycle (adds structure)
        for i in range(len(used) - 1):
            if used[i] != used[i + 1]:
                self.memory.link(used[i], used[i + 1], 1)

        # abstraction attempt (paced)
        if (n % CFG["abstraction_every"] == 0) and (random.random() < CFG["insight_chance"]):
            insight = self.try_abstract()
            if insight:
                self.memory.append(MemEvent(time.time(), "insight", insight, {"symbols": extract_symbols(insight)}))
                log(f"✨ {insight}", "magenta")

        show_summary({
            "events": len(self.memory.events),
            "top_symbols": self.memory.top_symbols(8),
        })
        divider("=")
        log("🔁 Re-looping...\n")

    def save(self) -> None:
        self.memory.save()

# ================= MAIN =================

if __name__ == "__main__":
    engine = Mirror0()
    i = 1
    try:
        while True:
            engine.cycle(i)
            # autosave occasionally to prevent data loss if it crashes
            if i % 10 == 0:
                engine.save()
            time.sleep(CFG["cycle_pause"])
            i += 1
    except KeyboardInterrupt:
        log("\n🛑 Interrupted — saving & exiting.", "red")
        engine.save()
