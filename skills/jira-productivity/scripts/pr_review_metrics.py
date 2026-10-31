#!/usr/bin/env python3
"""Pull request review-time metrics from `gh pr list --json` output.

Stdlib only, Python 3.8+. Produce the input with:
  gh pr list --repo OWNER/REPO --state merged --limit 200 \
    --json number,title,author,createdAt,mergedAt,additions,deletions,reviews,comments > prs.json

Usage: pr_review_metrics.py prs.json [--format text|json] [--bots dependabot,renovate]

Reports time to first review, time to merge, review rounds, reviewer load,
and size buckets, as medians and p90 in hours. Bot-authored PRs are excluded.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone


def ts(v):
    if not v:
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def stat(vals):
    return {"n": len(vals), "median": pct(vals, 50), "p90": pct(vals, 90)} if vals else {"n": 0}


def bucket(size):
    return "small (<100)" if size < 100 else "medium (100-499)" if size < 500 else "large (500+)"


def analyze(prs, bots):
    first_review, to_merge, rounds = [], [], []
    reviewers = Counter()
    by_size = {}
    skipped = 0
    for pr in prs:
        author = ((pr.get("author") or {}).get("login") or "").lower()
        if any(b in author for b in bots) or author.endswith("[bot]") or (pr.get("author") or {}).get("is_bot"):
            skipped += 1
            continue
        created, merged = ts(pr.get("createdAt")), ts(pr.get("mergedAt"))
        reviews = [r for r in (pr.get("reviews") or []) if ts(r.get("submittedAt"))]
        others = [r for r in reviews if ((r.get("author") or {}).get("login") or "").lower() != author]
        if created and others:
            fr = min(ts(r["submittedAt"]) for r in others)
            first_review.append(max((fr - created).total_seconds() / 3600, 0))
        if created and merged:
            h = (merged - created).total_seconds() / 3600
            to_merge.append(h)
            by_size.setdefault(bucket((pr.get("additions") or 0) + (pr.get("deletions") or 0)), []).append(h)
        rounds.append(sum(1 for r in others if r.get("state") == "CHANGES_REQUESTED"))
        for r in others:
            reviewers[(r.get("author") or {}).get("login", "unknown")] += 1
    total_reviews = sum(reviewers.values())
    top = reviewers.most_common(1)
    return {
        "prs_analyzed": len(prs) - skipped, "bot_prs_excluded": skipped,
        "hours_to_first_review": stat(first_review),
        "hours_to_merge": stat(to_merge),
        "change_request_rounds_median": pct(rounds, 50),
        "merge_hours_by_size": {k: stat(v) for k, v in sorted(by_size.items())},
        "review_load": {"reviewers": len(reviewers), "top_reviewer_share_percent":
                        round(100.0 * top[0][1] / total_reviews, 1) if top else 0},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--bots", default="dependabot,renovate,github-actions")
    a = ap.parse_args()
    try:
        with open(a.file, encoding="utf-8") as fh:
            prs = json.load(fh)
    except (OSError, ValueError) as exc:
        print("cannot read %s: %s" % (a.file, exc), file=sys.stderr)
        return 2
    rep = analyze(prs, [b.strip().lower() for b in a.bots.split(",") if b.strip()])
    if a.format == "json":
        print(json.dumps(rep, indent=2))
        return 0
    print("PRs analyzed: %d (bots excluded: %d)" % (rep["prs_analyzed"], rep["bot_prs_excluded"]))
    for k in ("hours_to_first_review", "hours_to_merge"):
        s = rep[k]
        print("%s: %s" % (k, "no samples" if not s["n"] else "n=%d median=%s p90=%s" % (s["n"], s["median"], s["p90"])))
    print("median change-request rounds: %s" % rep["change_request_rounds_median"])
    for k, s in rep["merge_hours_by_size"].items():
        print("  merge hours, %s: n=%d median=%s p90=%s" % (k, s["n"], s["median"], s["p90"]))
    print("review load: %(reviewers)d reviewers, top reviewer %(top_reviewer_share_percent)s%% of reviews" % rep["review_load"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
