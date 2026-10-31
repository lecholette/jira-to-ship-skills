#!/usr/bin/env python3
"""Change the status of Sentry-compatible issues. Stdlib only.

Dry run by default; pass --yes to apply.
Env: ERROR_TRACKER_TOKEN (or SENTRY_AUTH_TOKEN), optional ERROR_TRACKER_ORG, ERROR_TRACKER_URL.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PAYLOADS = {
    "resolved": {"status": "resolved"},
    "resolvedInNextRelease": {"status": "resolved", "statusDetails": {"inNextRelease": True}},
    "ignored": {"status": "ignored"},
    "unresolved": {"status": "unresolved"},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("issues", nargs="+")
    ap.add_argument("--action", default="resolved", choices=PAYLOADS)
    ap.add_argument("--org", default=os.getenv("ERROR_TRACKER_ORG"))
    ap.add_argument("--base-url", default=os.getenv("ERROR_TRACKER_URL", "https://sentry.io"))
    ap.add_argument("--yes", action="store_true", help="apply changes (otherwise dry run)")
    a = ap.parse_args()
    token = os.getenv("ERROR_TRACKER_TOKEN") or os.getenv("SENTRY_AUTH_TOKEN")
    if not a.org:
        sys.exit("error: --org or ERROR_TRACKER_ORG required")
    if a.yes and not token:
        sys.exit("error: ERROR_TRACKER_TOKEN not set")
    failed = 0
    for issue in a.issues:
        url = f"{a.base_url.rstrip('/')}/api/0/organizations/{a.org}/issues/{issue}/"
        if not a.yes:
            print(f"DRY RUN {issue}: PUT {url} {json.dumps(PAYLOADS[a.action])}")
            continue
        req = urllib.request.Request(
            url, data=json.dumps(PAYLOADS[a.action]).encode(), method="PUT",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f"OK {issue}: {json.load(r).get('status')}")
        except urllib.error.HTTPError as e:
            failed += 1
            print(f"FAIL {issue}: HTTP {e.code} {e.read()[:200].decode(errors='replace')}")
        except OSError as e:
            failed += 1
            print(f"FAIL {issue}: {e}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
