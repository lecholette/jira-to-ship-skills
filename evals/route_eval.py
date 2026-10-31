#!/usr/bin/env python3
"""Routing eval: which skill (if any) does `claude -p` invoke first for each query?
Adapted from skill-creator's run_eval.py detection. Run from a project root whose
.claude/skills/ holds the skills under test. Usage: route_eval.py evalset.json [--model M] [--workers N]
"""
import argparse, json, os, select, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

def first_skill(query, model, timeout, cwd):
    cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    if model:
        cmd += ["--model", model]
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd, env=env)
    buf, pending, acc, start, first = "", None, "", time.time(), None
    try:
        while time.time() - start < timeout:
            if p.poll() is not None and not select.select([p.stdout], [], [], 0)[0]:
                break
            if not select.select([p.stdout], [], [], 1.0)[0]:
                continue
            chunk = os.read(p.stdout.fileno(), 8192)
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "stream_event":
                    se = ev.get("event", {})
                    t = se.get("type")
                    if t == "content_block_start":
                        cb = se.get("content_block", {})
                        if cb.get("type") == "tool_use":
                            pending, acc = cb.get("name", "?"), ""
                    elif t == "content_block_delta" and pending:
                        acc += se.get("delta", {}).get("partial_json", "")
                    elif t == "content_block_stop" and pending:
                        try:
                            inp = json.loads(acc or "{}")
                        except json.JSONDecodeError:
                            inp = {}
                        name, pending = pending, None
                        if name == "Skill":
                            return inp.get("skill", "?") + ("" if not first else f" (after {first})")
                        # Ignore the environment's mandatory `date` preamble; otherwise remember the
                        # first real tool and keep watching: a skill used after a quick look still counts.
                        if name == "Bash" and inp.get("command", "").strip().startswith("date"):
                            continue
                        first = first or name
                elif ev.get("type") == "result":
                    return "none" + (f":{first}" if first else "")
        return "timeout"
    finally:
        if p.poll() is None:
            p.kill(); p.wait()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evalset"); ap.add_argument("--model"); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=90); ap.add_argument("--out", default="routing-results.json")
    a = ap.parse_args()
    items = json.load(open(a.evalset))
    with ThreadPoolExecutor(a.workers) as ex:
        got = list(ex.map(lambda it: first_skill(it["q"], a.model, a.timeout, os.getcwd()), items))
    rows, ok = [], 0
    for it, g in zip(items, got):
        name = g.split(" (after")[0]
        name = name.split(":")[-1] if name.startswith(("project:", "user:")) else name
        hit = (it["expect"] == "none" and name.startswith("none")) or name == it["expect"]
        ok += hit
        rows.append({"expect": it["expect"], "got": g, "pass": hit, "q": it["q"]})
        print(f"{'PASS' if hit else 'FAIL'}  expect={it['expect']:<22} got={g:<28} {it['q'][:60]}")
    print(f"\n{ok}/{len(items)} routed as expected")
    json.dump(rows, open(a.out, "w"), indent=1)

if __name__ == "__main__":
    main()
