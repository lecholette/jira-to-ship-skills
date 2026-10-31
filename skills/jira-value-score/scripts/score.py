#!/usr/bin/env python3
"""Score and rank Jira tickets against team-defined success metrics.

Usage:
  score.py judgments.json [--metrics success-metrics.json] [--format md|json|both]

Judgments are a JSON list (see references/metrics-config.md for the metrics file;
SKILL.md for the judgment shape). Metrics file precedence: --metrics, then
.jira-enrich/success-metrics.json in the cwd, then the bundled defaults.

  value         = sum(weight * magnitude * confidence) over metrics moved
                  - sum(weight * severity * confidence) over guardrail risks
  cost_of_delay = value + time_criticality + risk_reduction
  priority      = cost_of_delay / size   (S=1 M=2 L=3 XL=5)

Size only divides. It never adds to value. Exit 2 on invalid input.
Stdlib only, python3 >= 3.9.
"""
import argparse
import json
import os
import sys

SIZES = {"S": 1, "M": 2, "L": 3, "XL": 5}
REPO_METRICS = ".jira-enrich/success-metrics.json"
BUNDLED_METRICS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "success-metrics.json")
LOW_CONF = 0.5


class InputError(Exception):
    pass


def load(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise InputError(f"cannot read {what} {path}: {e.strerror}")
    except json.JSONDecodeError as e:
        raise InputError(f"{what} {path} is not valid JSON: {e}")


def num(v, lo, hi, where):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise InputError(f"{where}: expected a number, got {v!r}")
    if not lo <= v <= hi:
        raise InputError(f"{where}: {v} out of range {lo}-{hi}")
    return float(v)


def check_config(cfg):
    if not isinstance(cfg, dict) or not isinstance(cfg.get("metrics"), list) or not cfg["metrics"]:
        raise InputError("metrics config needs a non-empty 'metrics' list")
    weights = {}
    for kind in ("metrics", "guardrails"):
        for m in cfg.get(kind, []):
            if not isinstance(m, dict) or "id" not in m or "weight" not in m:
                raise InputError(f"{kind} entry needs 'id' and 'weight': {m!r}")
            if m["id"] in weights:
                raise InputError(f"duplicate id in config: {m['id']}")
            weights[m["id"]] = (kind, num(m["weight"], 0, 100, f"{kind}.{m['id']}.weight"))
    return weights


def score_one(j, weights, idx):
    if not isinstance(j, dict) or "key" not in j:
        raise InputError(f"judgment #{idx}: missing 'key'")
    key = j["key"]
    w = f"{key}"
    size = j.get("size")
    if size not in SIZES:
        raise InputError(f"{w}: size must be one of {sorted(SIZES)}, got {size!r}")
    conf = num(j.get("confidence", 1), 0, 1, f"{w}.confidence")
    tc = num(j.get("time_criticality", 0), 0, 3, f"{w}.time_criticality")
    rr = num(j.get("risk_reduction", 0), 0, 3, f"{w}.risk_reduction")
    value = 0.0
    moved = []
    for m in j.get("metrics", []):
        mid = m.get("id")
        if mid not in weights or weights[mid][0] != "metrics":
            raise InputError(f"{w}: unknown metric id {mid!r}")
        mag = num(m.get("magnitude"), 0, 3, f"{w}.{mid}.magnitude")
        mc = num(m.get("confidence"), 0, 1, f"{w}.{mid}.confidence")
        eff = m.get("effect", "improves")
        if eff not in ("improves", "worsens"):
            raise InputError(f"{w}.{mid}.effect must be 'improves' or 'worsens'")
        if mag > 0 and not m.get("evidence"):
            raise InputError(f"{w}.{mid}: magnitude > 0 needs quoted 'evidence'")
        contrib = weights[mid][1] * mag * mc * (1 if eff == "improves" else -1)
        value += contrib
        if mag > 0:
            moved.append(mid)
    penalty = 0.0
    for g in j.get("guardrail_risks", []):
        gid = g.get("id")
        if gid not in weights or weights[gid][0] != "guardrails":
            raise InputError(f"{w}: unknown guardrail id {gid!r}")
        sev = num(g.get("severity"), 0, 3, f"{w}.{gid}.severity")
        gc = num(g.get("confidence"), 0, 1, f"{w}.{gid}.confidence")
        penalty += weights[gid][1] * sev * gc
    value -= penalty
    cod = value + tc + rr
    flags = []
    if not moved:
        flags.append("no measurable outcome: clarify or deprioritize")
    if conf < LOW_CONF:
        flags.append("low confidence (<0.5): gather evidence before acting")
    if penalty > 0:
        flags.append("guardrail risk")
    return {
        "key": key, "summary": j.get("summary", ""), "size": size,
        "value": round(value, 2), "time_criticality": tc, "risk_reduction": rr,
        "cost_of_delay": round(cod, 2), "priority": round(cod / SIZES[size], 2),
        "confidence": conf, "metrics_moved": moved, "flags": flags,
    }


def markdown(rows):
    out = ["| Rank | Key | Size | Value | CoD | Priority | Flags |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        out.append(f"| {i} | {r['key']} | {r['size']} | {r['value']} | {r['cost_of_delay']} "
                   f"| {r['priority']} | {'; '.join(r['flags']) or '-'} |")
    return "\n".join(out)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("judgments")
    ap.add_argument("--metrics", default=None)
    ap.add_argument("--format", choices=("md", "json", "both"), default="md")
    a = ap.parse_args(argv)
    mpath = a.metrics or (REPO_METRICS if os.path.exists(REPO_METRICS) else os.path.normpath(BUNDLED_METRICS))
    try:
        weights = check_config(load(mpath, "metrics config"))
        js = load(a.judgments, "judgments")
        if not isinstance(js, list) or not js:
            raise InputError("judgments must be a non-empty JSON list")
        rows = [score_one(j, weights, i) for i, j in enumerate(js, 1)]
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    rows.sort(key=lambda r: (-r["priority"], -r["cost_of_delay"], r["key"]))
    print(f"Metrics file: {mpath}" + (" (bundled defaults)" if mpath == os.path.normpath(BUNDLED_METRICS) else ""))
    if a.format in ("md", "both"):
        print(markdown(rows))
    if a.format in ("json", "both"):
        print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
