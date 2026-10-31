#!/usr/bin/env python3
"""Acceptance ledger: tracks acceptance criteria (AC), linked tests, and
executed red/green evidence in docs/specs/<id>/acceptance.json.

Status is never self-reported: `run` executes the command and derives it.
Every run records digests of the criterion text, the linked test, and the test
harness, so a GREEN only counts if the same criterion, test, harness and command
produced the RED before it.

  init   <id> [--from FILE ...]  enrichment JSON (acceptance_criteria; type BUG makes the
                                 first one kind regression) and/or value-score JSON
                                 (outcome_criteria -> instrumentation AC + outcome AC)
  add    <id> AC-n "Given ... When ... Then ..." [--test path::name] [--phase N]
         [--kind behavior|regression|instrumentation|outcome] [--metric ID] [--verify-after YYYY-MM-DD]
  link   <id> AC-n [--test path::name] [--phase N]
  revise <id> AC-n "new text"    change a criterion; evidence for the old text stops counting
  run    <id> AC-n --cmd "<test command>" [--timeout S] [--red-exit 1] [--allow-unlinked-cmd]
         only a real test failure is RED; collection/import/usage errors are ERROR
  check  <id> [--phase N]        exit 1 unless every in-scope blocking AC is red-then-green
                                 with identical criterion, test, harness and command digests
  verify <id> [--phase N] [--allow-dirty]
                                 release gate: re-run each blocking AC's latest GREEN command
                                 at HEAD, record it, then apply check; prints the commit sha
  outcomes-due [<id> | --all]    outcome ACs whose verify-after date has passed, no result yet
  record-outcome <id> AC-n --result met|not-met|inconclusive --evidence "<text>"
  render <id>                    markdown traceability matrix
  codegraph-args <id>            print `--selected-test module:qualname` per linked pytest test

Global: --root DIR (default: current dir). Stdlib only, Python 3.9+.
"""
import argparse
import ast
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

KINDS = ("behavior", "regression", "instrumentation", "outcome")
RESULTS = ("met", "not-met", "inconclusive")
DIGEST_KEYS = ("criterion_sha", "test_sha", "harness_sha")
ROOT_HARNESS = ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", "package.json")
ROOT_HARNESS_GLOBS = ("jest.config.*", "vitest.config.*", "playwright.config.*")
LEDGER_EXCLUDE = ":(top,exclude,glob)**/docs/specs/*/acceptance.json"

MSG_LEGACY = "legacy run without digests: re-run"
MSG_REVISED = "criterion revised after evidence: needs new RED then GREEN"
MSG_TEST = "test changed between RED and GREEN"
MSG_HARNESS = "test harness changed between RED and GREEN"
MSG_CMD = "test command changed between RED and GREEN: re-run GREEN with the RED command"
MSG_UNRESOLVED = "test digest unresolved: link a test id whose file part exists"


def path_for(root, sid):
    return os.path.join(root, "docs", "specs", sid, "acceptance.json")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def text_sha(text):
    return sha(" ".join(str(text).split()).encode("utf-8"))


def normalize(data):
    for c in data.get("criteria", []):
        c.setdefault("kind", "behavior")
        c.setdefault("text_sha", text_sha(c["text"]))
        c.setdefault("runs", [])
        c.setdefault("revisions", [])
    return data


def read_ledger(p):
    with open(p, encoding="utf-8") as f:
        return normalize(json.load(f))


def load(root, sid):
    p = path_for(root, sid)
    if not os.path.exists(p):
        sys.exit(f"error: no ledger at {p}; run init first")
    return read_ledger(p)


def save(root, sid, data):
    p = path_for(root, sid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def find(data, ac):
    for c in data["criteria"]:
        if c["id"] == ac:
            return c
    sys.exit(f"error: {ac} not in ledger")


def valid_date(s):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(s or "")):
        return False
    try:
        datetime.datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def new_ac(ac, text, test=None, phase=None, kind="behavior", metric=None, verify_after=None):
    c = {"id": ac, "text": text, "text_sha": text_sha(text), "kind": kind, "phase": phase,
         "test": test, "runs": [], "revisions": []}
    if kind == "outcome":
        c.update(metric=metric, verify_after=verify_after, results=[])
    return c


def git(root, *args):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def git_head(root, short=True):
    out = git(root, "rev-parse", *(["--short"] if short else []), "HEAD")
    return (out or "").strip() or None


# ---- digests ---------------------------------------------------------------

def test_file(test):
    return (test or "").split("::")[0]


def find_def(body, names):
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == names[0]:
            if len(names) == 1:
                return node
            if isinstance(node, ast.ClassDef):
                return find_def(node.body, names[1:])
    return None


def test_digest(root, test):
    """(sha, scope): the test function's source (with decorators) for a pytest id, else
    the whole file; (None, 'unresolved') when the file part does not exist."""
    parts = (test or "").split("::")
    full = os.path.join(root, parts[0])
    if not parts[0] or not os.path.isfile(full):
        return None, "unresolved"
    with open(full, "rb") as f:
        raw = f.read()
    if parts[0].endswith(".py") and len(parts) > 1:
        names = [re.sub(r"\[.*\]$", "", p) for p in parts[1:]]
        src = raw.decode("utf-8", errors="replace")
        try:
            node = find_def(ast.parse(src).body, names)
        except SyntaxError:
            node = None
        end = getattr(node, "end_lineno", None)
        if node is not None and end:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            return sha("".join(src.splitlines(True)[start - 1:end]).encode("utf-8")), "function"
    return sha(raw), "file"


def harness_paths(root, test):
    """Existing harness files, relative to root: every conftest.py from root down to the
    test file's directory, plus root-level runner configs."""
    rel_dir = ""
    tf = test_file(test)
    if tf:
        rel = os.path.relpath(os.path.join(root, tf), root)
        if not rel.startswith(".."):
            rel_dir = os.path.dirname(rel)
    segs = [s for s in rel_dir.split(os.sep) if s and s != "."]
    cands = ["conftest.py"] + [os.path.join(*segs[:i + 1], "conftest.py") for i in range(len(segs))]
    cands += list(ROOT_HARNESS)
    for g in ROOT_HARNESS_GLOBS:
        cands += [os.path.relpath(p, root) for p in glob.glob(os.path.join(root, g))]
    return sorted({p for p in cands if os.path.isfile(os.path.join(root, p))})


def harness_digest(root, test):
    files = harness_paths(root, test)
    h = hashlib.sha256()
    for rel in files:
        with open(os.path.join(root, rel), "rb") as f:
            h.update(rel.encode("utf-8") + b"\0" + sha(f.read()).encode("ascii") + b"\n")
    return h.hexdigest(), files


# ---- commands --------------------------------------------------------------

def criteria_from(src, path):
    """[(kind, text, extra)] from an enrichment and/or value-score JSON object."""
    out = []
    items = [str(x) for x in src.get("acceptance_criteria") or []]
    rep = src.get("reproduction") or {}
    # jira-ticket-enrich already restates a bug's reproduction as the first criterion;
    # synthesize one from the raw steps only when no criteria were supplied.
    if not items and rep.get("steps") and rep.get("expected"):
        items.append("Given " + "; ".join(map(str, rep["steps"])) +
                     " When the steps are performed Then " + str(rep["expected"]))
    t = src.get("type")
    is_bug = str((t.get("value") if isinstance(t, dict) else t) or "").upper() == "BUG"
    for i, text in enumerate(items):
        out.append(("regression" if is_bug and i == 0 else "behavior", text, {}))
    for i, oc in enumerate(src.get("outcome_criteria") or []):
        missing = [k for k in ("text", "metric", "verify_after", "instrumentation_text") if not oc.get(k)]
        if missing:
            sys.exit(f"error: {path}: outcome_criteria[{i}] lacks {', '.join(missing)}")
        if not valid_date(oc["verify_after"]):
            sys.exit(f"error: {path}: outcome_criteria[{i}].verify_after must be YYYY-MM-DD")
        out.append(("instrumentation", str(oc["instrumentation_text"]), {}))
        out.append(("outcome", str(oc["text"]),
                    {"metric": str(oc["metric"]), "verify_after": oc["verify_after"]}))
    return out


def cmd_init(a):
    p = path_for(a.root, a.id)
    if os.path.exists(p):
        sys.exit(f"error: ledger exists at {p}")
    data = {"id": a.id, "created": now(), "criteria": []}
    for fp in a.from_file or []:
        with open(fp, encoding="utf-8") as f:
            src = json.load(f)
        last_instr = None
        for kind, text, extra in criteria_from(src, fp):
            c = new_ac(f"AC-{len(data['criteria']) + 1}", text, kind=kind, **extra)
            if kind == "instrumentation":
                last_instr = c["id"]
            elif kind == "outcome":
                c["instrumented_by"] = last_instr
            data["criteria"].append(c)
    save(a.root, a.id, data)
    kinds = {}
    for c in data["criteria"]:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    detail = ", ".join(f"{n} {k}" for k, n in kinds.items())
    print(f"initialized {p} with {len(data['criteria'])} criteria" + (f" ({detail})" if detail else ""))


def cmd_add(a):
    data = load(a.root, a.id)
    if any(c["id"] == a.ac for c in data["criteria"]):
        sys.exit(f"error: {a.ac} already exists")
    if a.kind == "outcome":
        if not a.metric or not a.verify_after:
            sys.exit("error: outcome ACs need --metric and --verify-after YYYY-MM-DD")
        if not valid_date(a.verify_after):
            sys.exit("error: --verify-after must be YYYY-MM-DD")
    elif a.metric or a.verify_after:
        sys.exit("error: --metric/--verify-after apply only to --kind outcome")
    data["criteria"].append(new_ac(a.ac, a.text, a.test, a.phase, a.kind, a.metric, a.verify_after))
    save(a.root, a.id, data)
    print(f"added {a.ac} ({a.kind})")


def cmd_link(a):
    data = load(a.root, a.id)
    c = find(data, a.ac)
    if a.test is None and a.phase is None:
        sys.exit("error: give --test and/or --phase")
    if a.test is not None:
        c["test"] = a.test
    if a.phase is not None:
        c["phase"] = a.phase
    save(a.root, a.id, data)
    print(f"updated {a.ac}: test={c['test']} phase={c['phase']}")


def cmd_revise(a):
    data = load(a.root, a.id)
    c = find(data, a.ac)
    if not a.text.strip():
        sys.exit("error: new text is empty")
    if text_sha(a.text) == text_sha(c["text"]):
        sys.exit("error: text unchanged (after whitespace normalization)")
    c["revisions"].append({"at": now(), "old_text": c["text"], "old_sha": text_sha(c["text"])})
    c["text"], c["text_sha"] = a.text, text_sha(a.text)
    save(a.root, a.id, data)
    stale = len(c["runs"])
    print(f"revised {a.ac}" + (f"; {stale} earlier run(s) no longer count: record a new RED then GREEN"
                               if stale else ""))


PYTEST_ERROR_RE = re.compile(r"\b\d+ errors? in [\d.]+s|^ERROR (collecting )?\S", re.M)


def classify(code, out, red_codes):
    """green / red / error. Only a genuine test failure counts as RED: a test that
    cannot be collected, imported, or found proves nothing about the behavior."""
    if code == 0:
        return "green"
    if code in red_codes and not PYTEST_ERROR_RE.search(out):
        return "red"
    return "error"


def parse_red(s):
    return {int(x) for x in str(s).split(",") if x.strip()}


def execute(root, c, cmd, timeout, red_exit, allow_unlinked, via):
    """Run cmd and return the run record. Digests are taken before execution."""
    t_sha, t_scope = test_digest(root, c.get("test"))
    h_sha, h_files = harness_digest(root, c.get("test"))
    try:
        r = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True, timeout=timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = 124, f"TIMEOUT after {timeout}s"
    return {
        "at": now(), "via": via, "cmd": cmd, "exit": code,
        "status": classify(code, out, parse_red(red_exit)),
        "git": git_head(root), "commit": git_head(root, short=False),
        "criterion_sha": text_sha(c["text"]),
        "test_sha": t_sha, "test_scope": t_scope,
        "harness_sha": h_sha, "harness_files": h_files,
        "red_exit": str(red_exit), "timeout": timeout, "allow_unlinked": bool(allow_unlinked),
        "output_sha256": sha(out.encode()),
        "tail": out.splitlines()[-20:],
    }


def names_test(c, cmd):
    return c["test"].split("::")[-1] in cmd


def cmd_run(a):
    data = load(a.root, a.id)
    c = find(data, a.ac)
    if c["kind"] == "outcome":
        sys.exit(f"error: {a.ac} is an outcome AC (post-release); use record-outcome")
    if not c.get("test"):
        sys.exit(f"error: {a.ac} has no linked test; run `link` first")
    if not names_test(c, a.cmd) and not a.allow_unlinked_cmd:
        sys.exit(f"error: --cmd does not reference the linked test '{c['test'].split('::')[-1]}'. "
                 "Run the linked test itself (or pass --allow-unlinked-cmd and say why).")
    run = execute(a.root, c, a.cmd, a.timeout, a.red_exit, a.allow_unlinked_cmd, "run")
    c["runs"].append(run)
    save(a.root, a.id, data)
    print("\n".join(run["tail"]))
    print(f"\n{a.ac}: {run['status'].upper()} (exit {run['exit']}) at {run['at']}")
    if run["status"] == "error":
        print("ERROR is not RED: the test did not run to an assertion (collection/import/usage "
              "error, timeout, or an exit code outside --red-exit). Fix the harness and rerun.")
    if run["test_sha"] is None:
        print(f"warning: {MSG_UNRESOLVED}")
    return 0


def evaluate(c):
    """Return (problems, red_run, green_run) for one blocking criterion. The gating GREEN
    is the latest run; it pairs with the most recent preceding RED for the same criterion."""
    problems = []
    if not c.get("test"):
        problems.append("no linked test")
    runs = c.get("runs", [])
    cur = text_sha(c["text"])

    def legacy(r):
        return any(k not in r for k in DIGEST_KEYS)

    def valid(r):
        return not legacy(r) and r["criterion_sha"] == cur

    def why_invalid(rs):
        if any(legacy(r) for r in rs):
            return MSG_LEGACY
        if any(not valid(r) for r in rs):
            return MSG_REVISED
        return None

    if not runs:
        return problems + ["no RED run recorded"], None, None
    last = runs[-1]
    if not valid(last):
        return problems + [why_invalid([last])], None, None
    if last["status"] != "green":
        prev_green = any(valid(r) and r["status"] == "green" for r in runs)
        msg = "no GREEN run after RED" if last["status"] == "red" and not prev_green else "latest run is not GREEN"
        return problems + [msg], None, None
    red = next((r for r in reversed(runs[:-1]) if valid(r) and r["status"] == "red"), None)
    if red is None:
        reds = [r for r in runs[:-1] if r["status"] == "red"]
        return problems + [why_invalid(reds) or "no RED run recorded"], None, last
    if red["test_sha"] is None or last["test_sha"] is None:
        problems.append(MSG_UNRESOLVED)
    elif red["test_sha"] != last["test_sha"]:
        problems.append(MSG_TEST)
    if red["harness_sha"] != last["harness_sha"]:
        problems.append(MSG_HARNESS)
    if " ".join(red["cmd"].split()) != " ".join(last["cmd"].split()):
        problems.append(MSG_CMD)
    return problems, red, last


def outcome_detail(c):
    res = c.get("results") or []
    r = res[-1]["result"] if res else "pending"
    return f"metric={c.get('metric')} verify-after={c.get('verify_after')} result={r}"


def in_scope(data, phase):
    return [c for c in data["criteria"] if phase is None or c.get("phase") == phase]


def gate(data, phase, extra=None):
    scope = in_scope(data, phase)
    if not [c for c in scope if c["kind"] != "outcome"]:
        print("FAIL: no in-scope blocking criteria" + (f" for phase {phase}" if phase is not None else ""))
        return 1
    bad = 0
    print(f"{'AC':<8}{'kind':<16}{'phase':<7}{'result':<14}detail")
    for c in scope:
        phase_s = str(c.get("phase") or "-")
        if c["kind"] == "outcome":
            print(f"{c['id']:<8}{c['kind']:<16}{phase_s:<7}{'post-release':<14}{outcome_detail(c)}")
            continue
        problems = (extra or {}).get(c["id"], []) + evaluate(c)[0]
        bad += bool(problems)
        print(f"{c['id']:<8}{c['kind']:<16}{phase_s:<7}{'FAIL' if problems else 'ok':<14}{'; '.join(problems)}")
    print("GATE:", "FAIL" if bad else "PASS")
    return 1 if bad else 0


def cmd_check(a):
    return gate(load(a.root, a.id), a.phase)


def dirty_state(root, paths):
    """Tracked changes vs HEAD (ledger files excluded), plus any of `paths` (linked tests,
    harness files) that are not tracked, i.e. would not ship with the commit."""
    out = git(root, "status", "--porcelain", "--untracked-files=no", "--", ":(top)", LEDGER_EXCLUDE)
    dirty = [ln for ln in (out or "").splitlines() if ln.strip()]
    paths = sorted({p for p in paths if p and os.path.isfile(os.path.join(root, p))})
    if paths:
        tracked = set((git(root, "ls-files", "--", *paths) or "").splitlines())
        dirty += [f"?? {p} (not committed)" for p in paths
                  if os.path.relpath(os.path.join(root, p), root) not in tracked]
    return dirty


def cmd_verify(a):
    data = load(a.root, a.id)
    commit = git_head(a.root, short=False)
    if not commit:
        print("VERIFY: FAIL: not a git repository with a commit; verify binds evidence to HEAD")
        return 1
    blocking = [c for c in in_scope(data, a.phase) if c["kind"] != "outcome"]
    paths = []
    for c in blocking:
        paths.append(test_file(c.get("test")))
        paths += harness_paths(a.root, c.get("test"))
    dirty = dirty_state(a.root, paths)
    print(f"commit: {commit}")
    if dirty:
        print("working tree differs from HEAD:\n  " + "\n  ".join(dirty))
        if not a.allow_dirty:
            print(f"VERIFY: FAIL at {commit}: commit or stash first (or --allow-dirty to run anyway)")
            return 1
    extra = {}
    for c in blocking:
        greens = [r for r in c["runs"] if r["status"] == "green"]
        if not c.get("test"):
            continue
        if not greens:
            extra[c["id"]] = ["no GREEN command to re-execute"]
            continue
        g = greens[-1]
        if not names_test(c, g["cmd"]) and not g.get("allow_unlinked"):
            extra[c["id"]] = ["latest GREEN command does not name the linked test"]
            continue
        run = execute(a.root, c, g["cmd"], g.get("timeout", 300), g.get("red_exit", "1"),
                      g.get("allow_unlinked", False), "verify")
        c["runs"].append(run)
        print(f"{c['id']}: re-ran `{g['cmd']}` -> {run['status'].upper()} (exit {run['exit']})")
    result = gate(data, a.phase, extra)
    data.setdefault("verifications", []).append(
        {"at": now(), "commit": commit, "phase": a.phase, "dirty": bool(dirty),
         "result": "fail" if result else "pass"})
    save(a.root, a.id, data)
    print(f"VERIFY: {'FAIL' if result else 'PASS'} at {commit}" + (" (dirty tree)" if dirty else ""))
    return result


def cmd_outcomes_due(a):
    if bool(a.id) == bool(a.all):
        sys.exit("error: give a spec <id> or --all")
    if a.all:
        files = sorted(glob.glob(os.path.join(a.root, "docs", "specs", "*", "acceptance.json")))
    else:
        files = [path_for(a.root, a.id)]
        load(a.root, a.id)
    today = datetime.date.today().isoformat()
    due = 0
    for p in files:
        try:
            data = read_ledger(p)
        except (OSError, ValueError, KeyError) as e:
            print(f"skip {p}: {e}", file=sys.stderr)
            continue
        sid = data.get("id") or os.path.basename(os.path.dirname(p))
        for c in data["criteria"]:
            va = c.get("verify_after")
            if c["kind"] == "outcome" and va and va <= today and not c.get("results"):
                due += 1
                print(f"{sid}\t{c['id']}\tmetric={c.get('metric')}\tverify-after={va}\t{c['text']}")
    print(f"{due} outcome criteria due (as of {today})")
    return 0


def cmd_record_outcome(a):
    data = load(a.root, a.id)
    c = find(data, a.ac)
    if c["kind"] != "outcome":
        sys.exit(f"error: {a.ac} is kind {c['kind']}, not outcome")
    if not a.evidence.strip():
        sys.exit("error: --evidence is empty")
    today = datetime.date.today().isoformat()
    c.setdefault("results", []).append(
        {"at": now(), "result": a.result, "evidence": a.evidence, "git": git_head(a.root)})
    save(a.root, a.id, data)
    early = c.get("verify_after") and today < c["verify_after"]
    print(f"recorded {a.ac}: {a.result}" + (f" (before verify-after {c['verify_after']})" if early else ""))
    return 0


def cmd_render(a):
    data = load(a.root, a.id)
    print(f"# Traceability: {a.id}\n")
    print("| AC | Kind | Criterion | Phase | Test | Red at | Green at | Latest | Evidence |")
    print("|----|------|-----------|-------|------|--------|----------|--------|----------|")
    for c in data["criteria"]:
        text = c["text"].replace("|", "\\|")
        if c["kind"] == "outcome":
            red = green = None
            ev = "post-release: " + outcome_detail(c)
        else:
            problems, red, green = evaluate(c)
            ev = "; ".join(problems) or "ok"
        last = c["runs"][-1]["status"] if c["runs"] else "-"
        if c["revisions"]:
            ev += f" (revised {len(c['revisions'])}x)"
        print(f"| {c['id']} | {c['kind']} | {text} | {c.get('phase') or '-'} | {c.get('test') or '-'} "
              f"| {red['at'] if red else '-'} | {green['at'] if green else '-'} | {last} | {ev} |")
    return 0


def to_symbol(test, root):
    """pytest id (path/test_x.py::Class::test_y) -> module:qualname, or None."""
    parts = test.split("::")
    path = parts[0]
    if len(parts) < 2 or not path.endswith(".py"):
        return None
    mod = path[:-3].replace(os.sep, "/")
    # Strip a leading src/ only for pure src layouts (src/ is not itself a package).
    if mod.startswith("src/") and not os.path.exists(os.path.join(root, "src", "__init__.py")):
        mod = mod[4:]
    return mod.replace("/", ".") + ":" + ".".join(parts[1:])


def cmd_codegraph_args(a):
    data = load(a.root, a.id)
    out = []
    for c in data["criteria"]:
        if not c.get("test"):
            continue
        sym = to_symbol(c["test"], a.root)
        if sym is None:
            print(f"skip {c['id']}: '{c['test']}' is not a pytest node id", file=sys.stderr)
        elif f"--selected-test {sym}" not in out:
            out.append(f"--selected-test {sym}")
    print(" ".join(out))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="sub", required=True)
    s = sub.add_parser("init"); s.add_argument("id")
    s.add_argument("--from", dest="from_file", action="append",
                   help="enrichment or value-score JSON; repeatable")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("add"); s.add_argument("id"); s.add_argument("ac"); s.add_argument("text")
    s.add_argument("--test"); s.add_argument("--phase", type=int)
    s.add_argument("--kind", choices=KINDS, default="behavior",
                   help="outcome ACs are post-release and non-blocking")
    s.add_argument("--metric", help="outcome only: metric id")
    s.add_argument("--verify-after", help="outcome only: YYYY-MM-DD")
    s.set_defaults(fn=cmd_add)
    s = sub.add_parser("link"); s.add_argument("id"); s.add_argument("ac")
    s.add_argument("--test"); s.add_argument("--phase", type=int); s.set_defaults(fn=cmd_link)
    s = sub.add_parser("revise"); s.add_argument("id"); s.add_argument("ac"); s.add_argument("text")
    s.set_defaults(fn=cmd_revise)
    s = sub.add_parser("run"); s.add_argument("id"); s.add_argument("ac")
    s.add_argument("--cmd", required=True, help="the developer's own test command; run via the shell")
    s.add_argument("--timeout", type=int, default=300)
    s.add_argument("--red-exit", default="1",
                   help="comma list of exit codes meaning 'test ran and failed' (pytest/jest: 1)")
    s.add_argument("--allow-unlinked-cmd", action="store_true",
                   help="permit a command that does not name the linked test")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("check"); s.add_argument("id"); s.add_argument("--phase", type=int)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("verify"); s.add_argument("id"); s.add_argument("--phase", type=int)
    s.add_argument("--allow-dirty", action="store_true",
                   help="run even if the tree differs from HEAD (recorded as dirty)")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("outcomes-due"); s.add_argument("id", nargs="?")
    s.add_argument("--all", action="store_true", help="scan docs/specs/*/acceptance.json")
    s.set_defaults(fn=cmd_outcomes_due)
    s = sub.add_parser("record-outcome"); s.add_argument("id"); s.add_argument("ac")
    s.add_argument("--result", required=True, choices=RESULTS)
    s.add_argument("--evidence", required=True); s.set_defaults(fn=cmd_record_outcome)
    s = sub.add_parser("codegraph-args"); s.add_argument("id"); s.set_defaults(fn=cmd_codegraph_args)
    s = sub.add_parser("render"); s.add_argument("id"); s.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
