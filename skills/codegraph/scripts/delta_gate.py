#!/usr/bin/env python3
"""Gate on `codegraph-slicer delta` JSON. Stdlib only, Python 3.9+.

Usage: codegraph-slicer delta --base-db B --head-db H --full --max-tokens 200000 [--selected-test ID ...] \
         | python3 delta_gate.py            (or: delta_gate.py delta.json)

Why not use `untested_modified_symbols` directly: a test MODULE symbol (id ends
with ':') counts as "updated" whenever any test in the file changes, and it
imports the code under test, so every symbol in that module looks covered. This
gate requires, for every changed non-module symbol, at least one updated or
selected test evidence entry that is a real test symbol (id not ending in ':').

It also fails when a test that existed on the base side was removed or
changed (the usual way an agent makes a contradicting requirement "pass"):
retiring or rewriting an existing test is a requirement decision for a person.
Pass --allow-test-change SYMBOL (repeatable) only after the user approved it,
and record that approval in the PR description.

Usage flags: [delta.json] [--allow-test-change SYMBOL ...]

Exit 1 on any GAP, existing-test change, boundary violation, or new cycle; exit 0 otherwise;
exit 2 on unreadable input. Module-level entries print as WARN and never fail.
Static evidence only: it does not show a test ran or passed.
"""
import json
import sys


def is_test(sym):
    mod = sym.split(":", 1)[0].split(".")
    return "tests" in mod or mod[-1].startswith("test_")


def existing_test_changes(d):
    """Pre-existing test symbols that were removed or changed. New tests are fine."""
    def defined(key):
        return {e[1] for e in d.get(key) or [] if len(e) > 2 and e[2] == "DEFINES"}
    added, removed = defined("added_edges"), defined("removed_edges")
    out = []
    for sym in d.get("modified_symbols") or []:
        if sym.endswith(":") or not is_test(sym) or sym in added:
            continue
        out.append((sym, "removed" if sym in removed else "changed"))
    return out


def load(path):
    try:
        raw = open(path, encoding="utf-8").read() if path else sys.stdin.read()
        data = json.loads(raw)
    except (OSError, ValueError) as exc:
        sys.stderr.write("delta_gate: cannot read delta JSON: %s\n" % exc)
        return None
    return data.get("delta", data) if isinstance(data, dict) else None


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    args, allowed, path = argv[1:], set(), None
    while args:
        a = args.pop(0)
        if a == "--allow-test-change" and args:
            allowed.add(args.pop(0))
        else:
            path = a
    d = load(path)
    if d is None or "test_coverage" not in d:
        sys.stderr.write("delta_gate: input is not codegraph-slicer delta JSON (no test_coverage)\n")
        return 2
    need = ("added_edges", "removed_edges", "boundary_violations", "new_cycles", "modified_symbols")
    missing = [k for k in need if k not in d]
    omitted = d.get("omitted") or {}
    cut = [k for k, v in omitted.items() if v] if isinstance(omitted, dict) else (["omitted"] if omitted else [])
    if missing or cut:
        # Budgeted delta output (the default since codegraph-slicer 527471e) drops these
        # fields; gating on it would silently pass cycles and boundary violations.
        sys.stderr.write("delta_gate: delta output is budgeted (missing %s); rerun "
                         "`codegraph-slicer delta ... --full --max-tokens 200000`\n" % ", ".join(missing + ["%s (truncated)" % k for k in cut if k not in missing]))
        return 2
    rows, gaps = [], 0
    for entry in d.get("test_coverage", []):
        sym = entry.get("symbol", "")
        evidence = list(entry.get("updated_or_selected_tests") or [])
        if sym.endswith(":"):
            rows.append((sym, "WARN", "module-level entry, not gated"))
            continue
        real = [t for t in evidence if not t.endswith(":")]
        if real:
            rows.append((sym, "ok", ", ".join(real)))
        else:
            gaps += 1
            rows.append((sym, "GAP", "no updated or selected test symbol"
                         + (" (module-only: %s)" % ", ".join(evidence) if evidence else "")))
    width = max([len(r[0]) for r in rows] + [6])
    print("%-*s  %-4s  %s" % (width, "symbol", "res", "evidence"))
    for sym, res, ev in rows:
        print("%-*s  %-4s  %s" % (width, sym, res, ev))
    test_changes = [(t, how) for t, how in existing_test_changes(d) if t not in allowed]
    for t, how in test_changes:
        print("FAIL existing test %s: %s (a requirement decision; needs user approval via --allow-test-change)" % (how, t))
    violations = d.get("boundary_violations") or []
    cycles = d.get("new_cycles") or []
    if violations:
        print("FAIL boundary_violations: %s" % json.dumps(violations))
    if cycles:
        print("FAIL new_cycles: %s" % json.dumps(cycles))
    failed = gaps or test_changes or violations or cycles
    print("RESULT: %s (%d gap(s), %d existing-test change(s), %d violation(s), %d cycle(s))"
          % ("FAIL" if failed else "PASS", gaps, len(test_changes), len(violations), len(cycles)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
