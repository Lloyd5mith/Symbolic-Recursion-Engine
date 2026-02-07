# memory.py
# -*- coding: utf-8 -*-
"""
Memory + Symbol Graph + Rewrite Store (persisted)
Author: Lloyd Christopher Smith

"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from collections import Counter, defaultdict

from io_handler import log


@dataclass
class MemEvent:
    ts: float
    kind: str          # "reflection" | "action" | "insight" | "user"
    text: str
    meta: Dict[str, Any]


class Memory:
    """
    - Stores events as JSONL (structured, append-only)
    - Maintains a weighted symbol graph: graph[a][b] = weight
    - Maintains rewrite rules: rules[name] = {"pattern":..., "replace":...}
    """

    SYMBOL_RE = re.compile(r"\[([^\[\]]+)\]")

    def __init__(
        self,
        events_path: str = "data/memory.jsonl",
        graph_path: str = "data/graph.json",
        rules_path: str = "data/rules.json",
        max_events: int = 5000,
    ):
        self.events_path = events_path
        self.graph_path = graph_path
        self.rules_path = rules_path
        self.max_events = max_events

        os.makedirs(os.path.dirname(self.events_path), exist_ok=True)

        self.events: List[MemEvent] = []
        self.symbol_counts: Counter[str] = Counter()
        self.graph: Dict[str, Counter[str]] = defaultdict(Counter)
        self.rules: Dict[str, Dict[str, str]] = {}  # {name: {pattern, replace}}

        self._load_events()
        self._load_graph()
        self._load_rules()
        self._reindex()

    # -------------------- Persistence --------------------

    def _load_events(self) -> None:
        if not os.path.exists(self.events_path):
            return
        with open(self.events_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    self.events.append(
                        MemEvent(
                            ts=float(obj.get("ts", 0.0)),
                            kind=str(obj.get("kind", "event")),
                            text=str(obj.get("text", "")),
                            meta=dict(obj.get("meta", {})),
                        )
                    )
                except Exception:
                    continue
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def _load_graph(self) -> None:
        if not os.path.exists(self.graph_path):
            return
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for a, nbrs in raw.items():
                if isinstance(nbrs, dict):
                    for b, w in nbrs.items():
                        try:
                            self.graph[a][b] = int(w)
                        except Exception:
                            continue
        except Exception:
            return

    def _load_rules(self) -> None:
        if not os.path.exists(self.rules_path):
            return
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for name, rr in raw.items():
                    if isinstance(rr, dict) and "pattern" in rr and "replace" in rr:
                        self.rules[str(name)] = {"pattern": str(rr["pattern"]), "replace": str(rr["replace"])}
        except Exception:
            return

    def save_graph(self) -> None:
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        serial: Dict[str, Dict[str, int]] = {}
        for a, nbrs in self.graph.items():
            serial[a] = dict(nbrs)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(serial, f, ensure_ascii=False, indent=2)

    def save_rules(self) -> None:
        os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)

    def append_event(self, event: MemEvent, autosave: bool = True) -> None:
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        self._index_event(event)
        if autosave:
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")

    # -------------------- Indexing --------------------

    def extract_symbols(self, text: str) -> List[str]:
        return [s.strip() for s in self.SYMBOL_RE.findall(text) if s.strip()]

    def _index_event(self, event: MemEvent) -> None:
        syms = event.meta.get("symbols")
        if not isinstance(syms, list):
            syms = self.extract_symbols(event.text)
        syms = [str(s) for s in syms]

        for s in syms:
            self.symbol_counts[s] += 1

        # strengthen adjacency for co-occurring symbols
        uniq = list(dict.fromkeys(syms))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                a, b = uniq[i], uniq[j]
                self.graph[a][b] += 1
                self.graph[b][a] += 1

    def _reindex(self) -> None:
        self.symbol_counts = Counter()
        # keep existing graph weights; still count symbols fresh
        for ev in self.events:
            syms = ev.meta.get("symbols")
            if not isinstance(syms, list):
                syms = self.extract_symbols(ev.text)
            for s in syms:
                self.symbol_counts[str(s)] += 1

        log(f"🧩 Memory loaded: {len(self.events)} events", "green")

    # -------------------- Graph Ops --------------------

    def link(self, a: str, b: str, w: int = 1) -> None:
        if not a or not b or a == b:
            return
        self.graph[a][b] += int(w)
        self.graph[b][a] += int(w)

    def neighbors(self, a: str, top_n: int = 8) -> List[Tuple[str, int]]:
        if a not in self.graph:
            return []
        return self.graph[a].most_common(top_n)

    def top_symbols(self, n: int = 10) -> List[Tuple[str, int]]:
        return self.symbol_counts.most_common(n)

    # -------------------- Rule Ops --------------------

    def set_rule(self, name: str, pattern: str, replace: str) -> None:
        self.rules[name] = {"pattern": pattern, "replace": replace}

    def del_rule(self, name: str) -> bool:
        if name in self.rules:
            del self.rules[name]
            return True
        return False
