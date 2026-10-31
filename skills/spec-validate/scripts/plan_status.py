#!/usr/bin/env python3
"""Summarize checkbox progress and runnable commands per phase of a plan.

Usage: plan_status.py <plan.md> [--json]
Exit code 0 if every checkbox is ticked, 1 otherwise, 2 on usage/read error.
"""
import json
import re
import sys

PHASE = re.compile(r"^#{1,3}\s+(Phase\s+\w+.*)$", re.IGNORECASE)
BOX = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+(.*)$")
CMD = re.compile(r"`([^`]+)`")


def parse(text):
    phases, cur = [], {"name": "(before first phase)", "done": 0, "open": [], "commands": []}
    for line in text.splitlines():
        m = PHASE.match(line)
        if m:
            phases.append(cur)
            cur = {"name": m.group(1).strip(), "done": 0, "open": [], "commands": []}
            continue
        b = BOX.match(line)
        if not b:
            continue
        if b.group(1) in "xX":
            cur["done"] += 1
        else:
            cur["open"].append(b.group(2).strip())
        for c in CMD.findall(b.group(2)):
            if " " in c or "/" in c or c.startswith(("make", "npm", "pytest")):
                cur["commands"].append(c)
    phases.append(cur)
    return [p for p in phases if p["done"] or p["open"]]


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        text = open(args[0], encoding="utf-8").read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    phases = parse(text)
    if "--json" in argv:
        print(json.dumps(phases, indent=2))
    else:
        for p in phases:
            total = p["done"] + len(p["open"])
            print(f"{p['name']}: {p['done']}/{total} ticked")
            for o in p["open"]:
                print(f"  open: {o}")
            for c in p["commands"]:
                print(f"  cmd:  {c}")
    return 0 if all(not p["open"] for p in phases) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
