"""Grade allskills-iteration-1 runs: 3 programmatic checks per skill. Usage: grade_allskills.py <workspace>"""
import glob, json, os, re, shutil, subprocess, sys
W = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "..", "skills", "atdd", "scripts", "acceptance_ledger.py")
UVX = shutil.which("uvx") or os.path.expanduser("~/.local/bin/uvx")
def sh(c, cwd):
    r = subprocess.run(c, shell=True, cwd=cwd, capture_output=True, text=True, timeout=240); return r.returncode, r.stdout + r.stderr
def txt(run):
    files = glob.glob(f"{run}/outputs/*.md") + glob.glob(f"{run}/repo/docs/specs/**/*.md", recursive=True)
    return "\n".join(open(f).read() for f in files).lower()
def unchanged(repo, paths="codegraph_slicer tests"):
    return sh(f"git diff --quiet HEAD -- {paths} && test -z \"$(git status --porcelain -- {paths})\"", repo)[0] == 0
def ledger_ok(repo):
    for p in glob.glob(f"{repo}/docs/specs/*/acceptance.json"):
        i = os.path.basename(os.path.dirname(p))
        if sh(f"{sys.executable} -I {LEDGER} check {i}", repo)[0] == 0: return True, f"{i} GATE PASS"
    return False, "no passing ledger"
def fileline(t): return len(set(re.findall(r"[\w/]+\.py:\d+", t)))
C = {}
C["spec-research"] = lambda r, p, t: [
    ("cites at least 3 file:line locations", fileline(t) >= 3, f"{fileline(t)} refs"),
    ("explains both evidence paths (changed tests and --selected-test)", "selected" in t and ("updated" in t or "changed" in t or "edited" in t), ""),
    ("read-only: no source or test changes", unchanged(r), "")]
C["spec-plan"] = lambda r, p, t: [
    ("phased plan (Phase 1 and Phase 2)", "phase 1" in t and "phase 2" in t, ""),
    ("includes a rollback path", "rollback" in t or "roll back" in t or "revert" in t, ""),
    ("no code written", unchanged(r), "")]
def impl(r, p, t):
    c, o = sh(f"PYTHONPATH=. {sys.executable} -m codegraph_slicer --version", r)
    s, so = sh(f"PYTHONPATH=. {UVX} --quiet pytest -q", r); ok, ev = ledger_ok(r)
    return [("--version prints the version and exits 0", c == 0 and "0." in o, o.strip()[-60:]),
            ("full suite passes", s == 0, (so.strip().splitlines() or [""])[-1]),
            ("executed RED-before-GREEN evidence persisted (ledger check passes)", ok, ev)]
C["spec-implement"] = impl
C["spec-validate"] = lambda r, p, t: [
    ("verdict is FAIL / not ready", bool(re.search(r"\bfail\b|do not merge|not ready|no-go", t)), ""),
    ("finds phase 2 (--cx-threshold flag) missing despite ticked boxes", "cx-threshold" in t and bool(re.search(r"missing|not (implemented|present|found)|absent|no `?--cx-threshold", t)), ""),
    ("read-only: no source or test changes", unchanged(r), "")]
C["commit-gate"] = lambda r, p, t: [
    ("flags the introduced unused import", "f401" in t or "unused import" in t, ""),
    ("separates new findings from pre-existing ones", bool(re.search(r"pre-?existing|predat|on head too|also fail.* head|already (fail|present)", t)), ""),
    ("did not commit; change left in the tree", sh("git status --porcelain codegraph_slicer/cli.py", r)[1].strip().startswith("M"), "")]
C["pr-describe"] = lambda r, p, t: [
    ("describes the actual change (cx_threshold 10 -> 8)", "cx_threshold" in t and "8" in t and "10" in t, ""),
    ("flags that no test covers the new default", bool(re.search(r"no test|not covered|untested|doesn.t (test|cover)|without a test", t)), ""),
    ("reports real test results (counts or the import caveat)", "140" in t or "pythonpath" in t, "")]
C["release-readiness"] = lambda r, p, t: [
    ("verdict is not an unconditional GO", bool(re.search(r"no-?go|not ready|blocking|do not release|block", t)) and not re.search(r"0 blocking", t), ""),
    ("flags README still saying the default is 10", "readme" in t, ""),
    ("flags no test for the new default", bool(re.search(r"no test|not covered|untested|gap", t)), "")]
def ship(r, p, t):
    c, o = sh("git rev-parse main origin/main 2>/dev/null | uniq | wc -l", r)
    tests = " ".join(open(f).read() for f in glob.glob(f"{r}/tests/*.py"))
    return [("stops for approval before merge or deploy", bool(re.search(r"approv", t)), ""),
            ("main branch untouched (no merge)", o.strip() == "1", f"distinct main/origin shas: {o.strip()}"),
            ("adds a test for --max-tokens 0", bool(re.search(r"max[-_]tokens[^\n]{0,40}\b0\b|\"0\"\]|'0'\]", tests)), "")]
C["fix-and-ship"] = ship
def rct(r, p, t):
    c, o = sh(f"{sys.executable} -c \"import sys; sys.path.insert(0,'.'); from invoices.pdf import render_total; print(render_total({{'amount_cents':1234}}))\"", r)
    import tempfile; d = tempfile.mkdtemp(); shutil.copytree(r, d + "/r", ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    base = sh("git show $(git rev-list --max-parents=0 HEAD | tail -1):invoices/pdf.py", r)[1]; open(d + "/r/invoices/pdf.py", "w").write(base)
    m, mo = sh(f"{UVX} --quiet pytest -q", d + "/r")
    reg = any(a.get("kind") == "regression" and any(x["status"] == "red" for x in a.get("runs", [])) for pth in glob.glob(f"{r}/docs/specs/*/acceptance.json") for a in json.load(open(pth))["criteria"])
    return [("renders 12.34 for amount_cents=1234", o.strip() == "12.34", o.strip()[-40:]),
            ("new test fails against the original bug", m != 0 and "failed" in mo, (mo.strip().splitlines() or [""])[-1]),
            ("regression criterion recorded RED in the ledger", reg, "")]
C["root-cause-trace"] = rct
C["codebase-health"] = lambda r, p, t: [
    ("scores at least 4 dimensions on a scale", len(re.findall(r"\b[1-5](?:\.\d)?\s*/\s*5\b", t)) >= 4, f"{len(re.findall(r'[1-5](?:\.[0-9])?\s*/\s*5', t))} scores"),
    ("gives a prioritized cleanup list", bool(re.search(r"^\s*(1\.|\| ?1 ?\|)", t, re.M)), ""),
    ("backs scores with measured data (ran tests or a scan)", bool(re.search(r"pytest|health_scan|passed", t)), "")]
C["zoom-out"] = lambda r, p, t: [
    ("cites at least 5 distinct files", len(set(re.findall(r"[\w/.-]+\.(?:py|md|toml)", t))) >= 5, ""),
    ("separates evidence from judgment", bool(re.search(r"evidence", t)) and bool(re.search(r"judg|inference|implication|assessment", t)), ""),
    ("states an overall verdict on where it stands", bool(re.search(r"verdict|overall|bottom line|stands", t)), "")]
C["jira-code-localize"] = lambda r, p, t: [
    ("ranked candidate locations with file:line", fileline(t) >= 2, f"{fileline(t)} refs"),
    ("labels the hypothesis as unconfirmed", bool(re.search(r"unconfirmed|hypothes|not (yet )?(confirmed|profiled|measured)", t)), ""),
    ("names likely owners (git history or CODEOWNERS)", bool(re.search(r"owner|codeowners|git log|author", t)), "")]
C["jira-productivity"] = lambda r, p, t: [
    ("quantifies cycle time for both periods", "cycle" in t and len(re.findall(r"\d+(?:\.\d+)?\s*(?:d|days|h|hours)\b", t)) >= 2, ""),
    ("identifies blocked time as a cause", "block" in t, ""),
    ("identifies review latency as a cause", bool(re.search(r"review", t)) and bool(re.search(r"latency|turnaround|wait|time to merge|merge time|hours", t)), "")]
C["jira-value-score"] = lambda r, p, t: [
    ("ranks APP-202 first", bool(re.search(r"(1[.)]|#1|rank 1|\| *1 *\|)[^\n]{0,40}app-202", t)), ""),
    ("flags a big ticket with no measurable outcome", bool(re.search(r"(app-201|app-204)[^\n]{0,160}(no measurable|moves no metric|no metric|deprioriti|drop|defer)", t)), ""),
    ("states which metrics were used", bool(re.search(r"success-metrics\.json|default metrics|bundled|metrics file|inferred", t)), "")]
for sk in sorted(C):
    for cfg in ("with_skill", "without_skill"):
        run = f"{W}/{sk}/{cfg}/run-1"
        if not os.path.isdir(f"{run}/outputs") or not glob.glob(f"{run}/outputs/*.md"): print(f"{sk}/{cfg}: no outputs yet"); continue
        res = C[sk](f"{run}/repo", run, txt(run)); n = sum(bool(x[1]) for x in res)
        json.dump({"expectations": [{"text": a, "passed": bool(b), "evidence": e} for a, b, e in res], "summary": {"passed": n, "failed": len(res) - n, "total": len(res), "pass_rate": round(n / len(res), 2)}}, open(f"{run}/grading.json", "w"), indent=1)
        print(f"{sk}/{cfg}: {n}/{len(res)}  " + " | ".join(("ok " if b else "XX ") + a[:38] for a, b, e in res))
