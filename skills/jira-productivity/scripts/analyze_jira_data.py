#!/usr/bin/env python3
"""Team throughput and cycle-time analysis from exported Jira issues.

Stdlib only, Python 3.8+. Input is JSON saved from a Jira search: a list of
issues or {"issues": [...]}. Include the changelog (expand=changelog) to get
true cycle time and blocked duration; without it only lead time is computed.

Usage:
  analyze_jira_data.py issues.json [--period LABEL] [--group-by none|assignee|type]
      [--points-field customfield_10016] [--epic-field customfield_10014]
      [--start-status "In Progress"] [--blocked-status Blocked]
      [--blocked-label-substr block] [--format text|json] [--output FILE]

Field ids vary by Jira instance; set --points-field and --epic-field to yours.
Reports are for planning conversations, not individual ranking.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone


def parse_ts(value):
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    if len(v) > 5 and (v[-5] in "+-") and v[-3] != ":":  # +0000 -> +00:00
        v = v[:-2] + ":" + v[-2:]
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "issues" in data:
        return data["issues"]
    return [data]


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def summarize(values):
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": round(sum(values) / len(values), 1),
            "median": pct(values, 50), "p90": pct(values, 90), "max": round(max(values), 1)}


def transitions(issue):
    """Yield (timestamp, from_status, to_status) from the changelog, oldest first."""
    out = []
    for h in (issue.get("changelog") or {}).get("histories", []) or []:
        ts = parse_ts(h.get("created"))
        for item in h.get("items", []) or []:
            if item.get("field") == "status" and ts:
                out.append((ts, item.get("fromString"), item.get("toString")))
    return sorted(out, key=lambda t: t[0])


def blocked_days(issue, blocked_status):
    total, since = 0.0, None
    for ts, frm, to in transitions(issue):
        if to and to.lower() == blocked_status.lower():
            since = ts
        elif since is not None and frm and frm.lower() == blocked_status.lower():
            total += (ts - since).total_seconds() / 86400
            since = None
    return total


def analyze_issue(issue, a):
    f = issue.get("fields", {}) or {}
    created, resolved = parse_ts(f.get("created")), parse_ts(f.get("resolutiondate"))
    row = {
        "key": issue.get("key", "?"),
        "type": (f.get("issuetype") or {}).get("name", "Unknown"),
        "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
        "points": f.get(a.points_field) or 0,
        "epic": (f.get("parent") or {}).get("key") or f.get(a.epic_field) or "No epic",
        "resolved": resolved,
        "lead_days": None, "cycle_days": None, "blocked_days": 0.0,
    }
    if created and resolved:
        row["lead_days"] = (resolved - created).total_seconds() / 86400
        start = next((ts for ts, _, to in transitions(issue)
                      if to and to.lower() == a.start_status.lower()), None)
        if start and start <= resolved:
            row["cycle_days"] = (resolved - start).total_seconds() / 86400
    row["blocked_days"] = blocked_days(issue, a.blocked_status)
    status = ((f.get("status") or {}).get("name") or "")
    labels = f.get("labels") or []
    row["blocked_now"] = status.lower() == a.blocked_status.lower() or any(
        a.blocked_label_substr.lower() in str(l).lower() for l in labels)
    return row


def weekly_throughput(rows):
    weeks = Counter()
    for r in rows:
        if r["resolved"]:
            y, w, _ = r["resolved"].isocalendar()
            weeks["%04d-W%02d" % (y, w)] += 1
    return dict(sorted(weeks.items()))


def block_metrics(rows):
    total = len(rows)
    n = sum(1 for r in rows if r["blocked_now"] or r["blocked_days"] > 0)
    return {"blocked_or_was_blocked": n, "percent": round(100.0 * n / total, 1) if total else 0,
            "blocked_days_total": round(sum(r["blocked_days"] for r in rows), 1)}


def analyze(rows):
    done = [r for r in rows if r["resolved"]]
    types = Counter(r["type"] for r in rows)
    epics = Counter(r["epic"] for r in rows)
    pts = [r["points"] for r in rows if r["points"]]
    return {
        "issues": len(rows), "resolved": len(done),
        "work_type_mix": {t: {"count": c, "percent": round(100.0 * c / len(rows), 1)} for t, c in types.most_common()} if rows else {},
        "throughput_per_week": weekly_throughput(rows),
        "lead_time_days": summarize([r["lead_days"] for r in rows if r["lead_days"] is not None]),
        "cycle_time_days": summarize([r["cycle_days"] for r in rows if r["cycle_days"] is not None]),
        "blocked": block_metrics(rows),
        "story_points": {"total": sum(pts), "with_points": len(pts), "without_points": len(rows) - len(pts)},
        "epics": {"distinct": len(epics), "top": dict(epics.most_common(5))},
    }


def findings(rep):
    out = []
    if rep["blocked"]["percent"] > 20:
        out.append("High blocked share: %s%% of issues blocked or previously blocked" % rep["blocked"]["percent"])
    bug = rep["work_type_mix"].get("Bug", {}).get("percent", 0)
    if bug > 50:
        out.append("Bug-heavy mix: %s%% of issues are bugs" % bug)
    cyc = rep["cycle_time_days"]
    if cyc.get("n") and cyc["p90"] and cyc["median"] and cyc["p90"] > 3 * cyc["median"]:
        out.append("Long tail: p90 cycle time %s days vs median %s" % (cyc["p90"], cyc["median"]))
    if rep["epics"]["distinct"] > 5:
        out.append("Spread across %d epics (possible context switching)" % rep["epics"]["distinct"])
    if rep["issues"] and rep["resolved"] / rep["issues"] < 0.5:
        out.append("Under half of issues resolved in this window (%d of %d)" % (rep["resolved"], rep["issues"]))
    if not cyc.get("n"):
        out.append("No changelog data: cycle time unavailable, showing lead time only")
    return out


def render(title, rep):
    L = ["=" * 70, title, "=" * 70,
         "Issues: %d  Resolved: %d" % (rep["issues"], rep["resolved"]), "", "Work type mix"]
    for t, s in rep["work_type_mix"].items():
        L.append("  %s: %d (%s%%)" % (t, s["count"], s["percent"]))
    L += ["", "Throughput per week (resolved)"]
    L += ["  %s: %d" % kv for kv in rep["throughput_per_week"].items()] or ["  none"]
    for name, key in (("Lead time (created to resolved), days", "lead_time_days"),
                      ("Cycle time (start status to resolved), days", "cycle_time_days")):
        s = rep[key]
        L += ["", name, "  " + ("no samples" if not s["n"] else
              "n=%d mean=%s median=%s p90=%s max=%s" % (s["n"], s["mean"], s["median"], s["p90"], s["max"]))]
    b = rep["blocked"]
    L += ["", "Blocked: %d issues (%s%%), %s blocked days total" % (
        b["blocked_or_was_blocked"], b["percent"], b["blocked_days_total"])]
    sp = rep["story_points"]
    L += ["Story points: total %s, %d issues with points, %d without" % (sp["total"], sp["with_points"], sp["without_points"])]
    L += ["Epics: %d distinct; top %s" % (rep["epics"]["distinct"], rep["epics"]["top"]), "", "Findings"]
    L += ["  - " + f for f in rep.get("findings", [])] or ["  none"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--period", default="all issues in file")
    ap.add_argument("--group-by", choices=("none", "assignee", "type"), default="none")
    ap.add_argument("--points-field", default="customfield_10016")
    ap.add_argument("--epic-field", default="customfield_10014")
    ap.add_argument("--start-status", default="In Progress")
    ap.add_argument("--blocked-status", default="Blocked")
    ap.add_argument("--blocked-label-substr", default="block")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--output")
    a = ap.parse_args()
    try:
        issues = load(a.file)
    except (OSError, ValueError) as exc:
        print("cannot read %s: %s" % (a.file, exc), file=sys.stderr)
        return 2
    rows = [analyze_issue(i, a) for i in issues if isinstance(i, dict)]
    groups = {"all": rows}
    if a.group_by != "none":
        groups = defaultdict(list)
        for r in rows:
            groups[r[a.group_by]].append(r)
    result = {}
    for name, grp in groups.items():
        rep = analyze(grp)
        rep["findings"] = findings(rep)
        result[name] = rep
    if a.format == "json":
        text = json.dumps(result, indent=2, default=str)
    else:
        text = "\n\n".join(render("Jira throughput: %s - %s" % (n, a.period), r) for n, r in result.items())
    if a.output:
        with open(a.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print("saved %s" % a.output)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
