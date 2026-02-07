# mirror0.py
# -*- coding: utf-8 -*-
"""
Symbolic Recursion Engine — Mirror-0 (real symbolic state updates)
Author: Lloyd Christopher Smith

This is a symbolic recursion core:
- symbolic graph memory (state)
- parsing + evaluation of symbolic actions
- rewrite rules (term rewriting-lite via regex rules)
- abstraction (frequent pair -> new symbol)
- loop mode + chat mode

"""

from __future__ import annotations

import os
import sys
import time
import yaml
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from memory import Memory, MemEvent
from observer import Observer
from io_handler import log, divider, show_summary


sys.stdout.reconfigure(encoding="utf-8")

# -------------------- Config --------------------

DEFAULT_CFG: Dict[str, Any] = {
    "engine": {
        "seed_path": "data/seed.txt",
        "memory_events": "data/memory.jsonl",
        "memory_graph": "data/graph.json",
        "memory_rules": "data/rules.json",
        "observer_label": "Mirror-1",
        "max_events": 5000,
    },
    "runtime": {
        "mode": "loop",                # loop | chat
        "recursion_delay": 0.2,
        "cycle_pause": 1.0,
        "auto_save_graph_every": 2,    # cycles
        "auto_save_rules_every": 5,    # cycles
        "thoughts_min": 2,
        "thoughts_max": 6,
        "insight_chance": 0.45,
        "abstraction_every": 3,
    },
    "symbolic": {
        "seed_fallback": ["symbolic", "recursion", "origin", "mirror", "self", "loop"],
        "max_symbol_len": 32,
        "min_pair_support": 4,
    },
}


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        return DEFAULT_CFG
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # shallow merge
    merged = {**DEFAULT_CFG}
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


# -------------------- Symbol Helpers --------------------

TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{1,64}")
BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")


def now_ts() -> float:
    return time.time()


def norm_symbol(s: str, max_len: int = 32) -> str:
    s = (s or "").strip()
    s = s.replace(" ", "_")
    s = re.sub(r"[^A-Za-z0-9_\-\(\):]", "", s)
    if not s:
        return "void"
    return s[:max_len]


def bracket(s: str) -> str:
    return f"[{s}]"


def extract_symbols(text: str, max_len: int = 32) -> List[str]:
    # Prefer explicit [symbols]
    syms = [norm_symbol(x, max_len) for x in BRACKET_RE.findall(text)]
    syms = [s for s in syms if s]
    if syms:
        return syms
    # Otherwise mine tokens
    toks = TOKEN_RE.findall(text)
    return [norm_symbol(t, max_len) for t in toks if t.strip()]


# -------------------- Expression Language (tiny + strict) --------------------
# Supported commands (typed by user in chat):
#   link a b [w]
#   rule set <name> /pattern/ -> replace
#   rule del <name>
#   show top
#   show nbr <sym>
#   abstract
#
# Engine also auto-generates actions internally.

@dataclass
class Action:
    op: str
    args: List[str]


def parse_command(text: str) -> Optional[Action]:
    t = text.strip()
    if not t:
        return None

    parts = t.split()
    head = parts[0].lower()

    if head == "link" and len(parts) >= 3:
        op = "link"
        a = parts[1]
        b = parts[2]
        w = parts[3] if len(parts) >= 4 else "1"
        return Action(op, [a, b, w])

    if head == "show" and len(parts) >= 2:
        sub = parts[1].lower()
        if sub == "top":
            return Action("show_top", [])
        if sub == "nbr" and len(parts) >= 3:
            return Action("show_nbr", [parts[2]])

    if head == "rule" and len(parts) >= 2:
        sub = parts[1].lower()
        if sub == "del" and len(parts) >= 3:
            return Action("rule_del", [parts[2]])
        if sub == "set":
            # Expect: rule set NAME /pattern/ -> replacement...
            raw = t[len("rule set "):].strip()
            # name first token
            if not raw:
                return None
            name = raw.split()[0]
            rest = raw[len(name):].strip()
            # /pattern/ -> replace
            m = re.search(r"/(.+?)/\s*->\s*(.+)$", rest)
            if not m:
                return None
            pattern = m.group(1)
            replace = m.group(2)
            return Action("rule_set", [name, pattern, replace])

    if head == "abstract":
        return Action("abstract", [])

    return None


# -------------------- Mirror-0 Engine --------------------

class Mirror0:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        eng = cfg["engine"]
        sym = cfg["symbolic"]

        self.seed_path = eng["seed_path"]
        os.makedirs(os.path.dirname(self.seed_path), exist_ok=True)

        self.max_symbol_len = int(sym["max_symbol_len"])
        self.min_pair_support = int(sym["min_pair_support"])

        self.memory = Memory(
            events_path=eng["memory_events"],
            graph_path=eng["memory_graph"],
            rules_path=eng["memory_rules"],
            max_events=int(eng["max_events"]),
        )
        self.observer = Observer(eng.get("observer_label", "Mirror-1"))

        if not os.path.exists(self.seed_path):
            with open(self.seed_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sym["seed_fallback"]) + "\n")

    # ---------- Seeds / Selection ----------

    def load_seed(self) -> List[str]:
        try:
            with open(self.seed_path, "r", encoding="utf-8", errors="ignore") as f:
                out = [line.strip() for line in f if line.strip()]
                return [norm_symbol(x, self.max_symbol_len) for x in out]
        except FileNotFoundError:
            return []

    def pick_symbol(self) -> Tuple[str, str]:
        # Prefer memory top symbols
        if self.memory.symbol_counts and random.random() < 0.75:
            top = self.memory.top_symbols(12)
            if top:
                population: List[str] = []
                for s, c in top:
                    population.extend([s] * min(c, 10))
                base = random.choice(population) if population else top[0][0]
                # Sometimes walk the graph
                if random.random() < 0.55:
                    nbrs = self.memory.neighbors(base, 10)
                    if nbrs:
                        population2: List[str] = []
                        for n, w in nbrs:
                            population2.extend([n] * min(w, 10))
                        nxt = random.choice(population2) if population2 else nbrs[0][0]
                        return norm_symbol(nxt, self.max_symbol_len), "memory.graph"
                return norm_symbol(base, self.max_symbol_len), "memory.top"
        # Fallback seed
        seeds = self.load_seed()
        if seeds:
            return random.choice(seeds), "seed"
        return "origin", "default"

    # ---------- Rewrite Application ----------

    def apply_rules(self, text: str) -> str:
        out = text
        for _, rr in self.memory.rules.items():
            try:
                out2 = re.sub(rr["pattern"], rr["replace"], out, flags=re.IGNORECASE)
                out = out2
            except Exception:
                continue
        return out

    # ---------- Core: Interpret -> Act -> Store ----------

    def act_link(self, a: str, b: str, w: int = 1) -> str:
        a = norm_symbol(a, self.max_symbol_len)
        b = norm_symbol(b, self.max_symbol_len)
        self.memory.link(a, b, w)
        return f"🔗 link {bracket(a)} ↔ {bracket(b)} (+{w})"

    def act_rule_set(self, name: str, pattern: str, replace: str) -> str:
        self.memory.set_rule(name, pattern, replace)
        return f"🧾 rule set '{name}': /{pattern}/ -> {replace}"

    def act_rule_del(self, name: str) -> str:
        ok = self.memory.del_rule(name)
        return f"🧾 rule del '{name}': {'ok' if ok else 'not found'}"

    def act_show_top(self) -> str:
        tops = self.memory.top_symbols(10)
        if not tops:
            return "📌 top: (empty)"
        return "📌 top: " + ", ".join([f"{bracket(s)}:{c}" for s, c in tops])

    def act_show_nbr(self, sym: str) -> str:
        s = norm_symbol(sym, self.max_symbol_len)
        nbrs = self.memory.neighbors(s, 10)
        if not nbrs:
            return f"📎 nbr {bracket(s)}: (none)"
        return "📎 nbr " + bracket(s) + ": " + ", ".join([f"{bracket(n)}:{w}" for n, w in nbrs])

    def act_abstract(self) -> Optional[str]:
        # Find a strong pair by scanning adjacency (cheap)
        # Choose among top symbols to limit search
        tops = [s for s, _ in self.memory.top_symbols(10)]
        if len(tops) < 2:
            return None

        # pick candidate pair with highest edge weight
        best: Optional[Tuple[str, str, int]] = None
        for a in tops:
            for b, w in self.memory.neighbors(a, 10):
                if a == b:
                    continue
                if best is None or w > best[2]:
                    best = (a, b, w)

        if not best:
            return None

        a, b, w = best
        if w < self.min_pair_support:
            return None

        # Create new abstraction symbol and reinforce links
        abs_sym = norm_symbol(f"abs({a}_{b})", self.max_symbol_len)
        self.memory.link(abs_sym, a, max(2, w // 2))
        self.memory.link(abs_sym, b, max(2, w // 2))

        return f"Δ abstract {bracket(abs_sym)} := {bracket(a)} ⊗ {bracket(b)} (support:{w})"

    def interpret(self, raw: Optional[str] = None) -> List[MemEvent]:
        """
        Returns list of events produced this step (reflection + optional action/insight).
        """
        ctx = self.observer.context(self.memory)

        if raw and raw.strip():
            raw2 = self.apply_rules(raw.strip())
            cmd = parse_command(raw2)
            if cmd:
                # execute explicit command
                action_text = self.execute(cmd)
                ev_action = MemEvent(
                    ts=now_ts(),
                    kind="action",
                    text=action_text,
                    meta={"symbols": extract_symbols(action_text, self.max_symbol_len), "ctx": ctx},
                )
                return [ev_action]

            # otherwise treat as symbolic input
            syms = extract_symbols(raw2, self.max_symbol_len)
            chosen = syms[0] if syms else self.pick_symbol()[0]
            chosen = norm_symbol(chosen, self.max_symbol_len)
            source = "user"
        else:
            chosen, source = self.pick_symbol()

        # Reflection templates (short, symbolic, state-aware)
        # Reflection is ALWAYS bracketed, so the memory indexes it.
        templates = [
            f"{bracket(chosen)} :: {ctx}",
            f"observe({ctx} <- {bracket(chosen)})",
            f"bind({bracket(chosen)}, {ctx})",
            f"trace({bracket(chosen)} -> {ctx})",
        ]
        text = random.choice(templates)

        ev_ref = MemEvent(
            ts=now_ts(),
            kind="reflection" if source != "user" else "user",
            text=text,
            meta={"source": source, "symbols": extract_symbols(text, self.max_symbol_len), "ctx": ctx},
        )

        # Update symbolic state with a small action (link to a neighbor) to make it REAL
        extra: List[MemEvent] = []
        if random.random() < 0.55:
            # Link chosen symbol to a context-derived token
            ctx_sym = norm_symbol(ctx.split("::")[0], self.max_symbol_len)
            action_text = self.act_link(chosen, ctx_sym, 1)
            extra.append(
                MemEvent(
                    ts=now_ts(),
                    kind="action",
                    text=action_text,
                    meta={"symbols": extract_symbols(action_text, self.max_symbol_len), "ctx": ctx},
                )
            )

        return [ev_ref] + extra

    def execute(self, action: Action) -> str:
        op = action.op
        args = action.args

        if op == "link":
            a = args[0]; b = args[1]
            w = 1
            try:
                w = int(args[2]) if len(args) >= 3 else 1
            except Exception:
                w = 1
            return self.act_link(a, b, w)

        if op == "rule_set":
            return self.act_rule_set(args[0], args[1], args[2])

        if op == "rule_del":
            return self.act_rule_del(args[0])

        if op == "show_top":
            return self.act_show_top()

        if op == "show_nbr":
            return self.act_show_nbr(args[0])

        if op == "abstract":
            out = self.act_abstract()
            return out if out else "Δ abstract: insufficient support"

        return "unknown action"

    # ---------- Loop ----------

    def cycle(self, cycle_no: int) -> None:
        rt = self.cfg["runtime"]
        delay = float(rt["recursion_delay"])
        thoughts = random.randint(int(rt["thoughts_min"]), int(rt["thoughts_max"]))
        insight_chance = float(rt["insight_chance"])

        log(f"🧠 Cycle {cycle_no} — thoughts:{thoughts}", "green")

        for _ in range(thoughts):
            events = self.interpret()
            for ev in events:
                if self.observer.allow(ev.text):
                    self.memory.append_event(ev, autosave=True)
                    log(ev.text)
            time.sleep(delay)

        # occasional insight: abstraction
        insight_text: Optional[str] = None
        if random.random() < insight_chance:
            insight_text = self.act_abstract()

        if insight_text:
            ev_ins = MemEvent(
                ts=now_ts(),
                kind="insight",
                text=insight_text,
                meta={"symbols": extract_symbols(insight_text, self.max_symbol_len)},
            )
            self.memory.append_event(ev_ins, autosave=True)
            log(f"✨ {insight_text}", "magenta")

        # autosave graph/rules
        if cycle_no % int(rt["auto_save_graph_every"]) == 0:
            self.memory.save_graph()
        if cycle_no % int(rt["auto_save_rules_every"]) == 0:
            self.memory.save_rules()

        summary = {
            "events": self.memory.events.__len__(),
            "top_symbols": self.memory.top_symbols(8),
        }
        show_summary(summary)
        divider("=")
        log("🔁 Re-looping...\n")

    # ---------- Chat ----------

    def chat(self) -> None:
        log("\n💬 Interactive Mode — commands: link/show/rule/abstract | 'exit'\n", "yellow")
        while True:
            user = input("You: ").strip()
            if user.lower() == "exit":
                log("🌀 Exiting.", "yellow")
                break

            events = self.interpret(user)
            for ev in events:
                self.memory.append_event(ev, autosave=True)
                log(f"Mirror-0: {ev.text}", "cyan")

            # always show a quick neighbor peek if user gave a symbol
            syms = extract_symbols(user, self.max_symbol_len)
            if syms:
                log(self.act_show_nbr(syms[0]), "magenta")


# -------------------- Main --------------------

if __name__ == "__main__":
    cfg = load_config()
    mirror = Mirror0(cfg)

    mode = str(cfg["runtime"].get("mode", "loop")).lower().strip()
    cycle_no = 1

    try:
        if mode == "chat":
            mirror.chat()
        else:
            while True:
                mirror.cycle(cycle_no)
                time.sleep(float(cfg["runtime"]["cycle_pause"]))
                cycle_no += 1
    except KeyboardInterrupt:
        log("\n🛑 Interrupted. Saving graph/rules + exiting cleanly.", "red")
        mirror.memory.save_graph()
        mirror.memory.save_rules()
