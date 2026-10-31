#!/usr/bin/env python3
"""Validate an enrichment JSON and render it as a Jira comment body (markdown).

Usage:
  render_enrichment.py enrichment.json            # render to stdout
  render_enrichment.py --has-marker comments.json KEY   # exit 0 if an identical
                                                  # enrichment comment already exists, 3 if
                                                  # one exists with different content, 1 if none
Stdlib only.
"""
import hashlib
import json
import re
import sys

MARKER_RE = re.compile(r"<!-- jira-enrich:v1 key=(\S+) hash=([0-9a-f]{12}) -->")
VALID_TYPES = {"BUG", "FEATURE", "TASK", "UNCLEAR"}


def validate(d):
    errs = []
    for f in ("key", "type", "readiness", "impact"):
        if f not in d:
            errs.append(f"missing required field: {f}")
    t = d.get("type", {}).get("value")
    if t and t not in VALID_TYPES:
        errs.append(f"type.value must be one of {sorted(VALID_TYPES)}")
    if t == "BUG" and not d.get("reproduction"):
        errs.append("BUG requires reproduction")
    if t in ("FEATURE", "TASK") and not d.get("acceptance_criteria"):
        errs.append("FEATURE/TASK requires acceptance_criteria")
    for k in ("confidence",):
        c = d.get("type", {}).get(k)
        if c is not None and not 0 <= c <= 100:
            errs.append("type.confidence must be 0-100")
    return errs


def content_hash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]


def bullets(items):
    return "\n".join(f"- {i}" for i in items) if items else "- none"


def render(d):
    t, r, i = d["type"], d["readiness"], d["impact"]
    out = [f"*Enrichment for {d['key']}*", ""]
    out.append(f"*Type:* {t['value']} ({t.get('confidence', '?')}%)")
    out.append(f"*Readiness:* {r['percent']}%")
    out.append(
        f"*Impact:* severity {i['severity']}; urgency {i['urgency']}; "
        f"suggested priority {i['suggested_priority']} (current {i.get('current_priority', '?')})"
    )
    out.append(f"_Basis: {i.get('path', '')}_")
    out += ["", "*Missing / questions for reporter*", bullets(r.get("questions_for_reporter") or r.get("missing"))]
    rep = d.get("reproduction")
    if rep:
        out += ["", f"*Reproduction ({rep.get('approach', '?')})*"]
        out += [f"{n}. {s}" for n, s in enumerate(rep.get("steps", []), 1)] or ["- steps needed"]
        if rep.get("expected"):
            out.append(f"Expected: {rep['expected']}")
        if rep.get("actual"):
            out.append(f"Actual: {rep['actual']}")
        if rep.get("blockers"):
            out += ["Blockers:", bullets(rep["blockers"])]
    if d.get("acceptance_criteria"):
        out += ["", "*Acceptance criteria*", bullets(d["acceptance_criteria"])]
    if d.get("code_areas"):
        out += ["", "*Likely code areas*"]
        out += [f"- {c['path']}:{c.get('lines', '')} {c.get('note', '')}".rstrip() for c in d["code_areas"]]
    if d.get("linked_work"):
        out += ["", "*Linked work*"]
        out += [f"- {w['type']} {w['ref']} ({w.get('state', '?')}, {w.get('date', '')}) {w.get('note', '')}".rstrip() for w in d["linked_work"]]
    if d.get("duplicates"):
        out += ["", "*Possible duplicates*"]
        out += [f"- {x['key']}: {x.get('reason', '')}" for x in d["duplicates"]]
    rt = d.get("routing")
    if rt:
        out += ["", f"*Suggested routing:* {rt.get('team', '?')} ({rt.get('confidence', '?')}%) {rt.get('reasoning', '')}".rstrip()]
    if d.get("size_signals"):
        out += ["", "*Size signals*", bullets(d["size_signals"])]
    out += ["", f"<!-- jira-enrich:v1 key={d['key']} hash={content_hash(d)} -->"]
    return "\n".join(out)


def has_marker(path, key, new_hash=None):
    comments = json.load(open(path))
    if isinstance(comments, dict):
        comments = comments.get("comments", [])
    found = None
    for c in comments:
        body = c.get("body", c) if isinstance(c, dict) else c
        if not isinstance(body, str):
            body = json.dumps(body)
        for k, h in MARKER_RE.findall(body):
            if k == key:
                found = h
    if found is None:
        return 1
    return 0 if new_hash is None or found == new_hash else 3


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if len(argv) >= 4 and argv[1] == "--has-marker":
        h = argv[4] if len(argv) > 4 else None
        sys.exit(has_marker(argv[2], argv[3], h))
    if len(argv) != 2:
        sys.exit(__doc__)
    d = json.load(open(argv[1]))
    errs = validate(d)
    if errs:
        sys.exit("INVALID:\n" + "\n".join(f"- {e}" for e in errs))
    print(render(d))


if __name__ == "__main__":
    main(sys.argv)
