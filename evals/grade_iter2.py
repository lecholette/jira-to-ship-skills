import json, os, re, shutil, subprocess, sys, glob
W = sys.argv[1]
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "atdd", "scripts", "acceptance_ledger.py")
UVX = shutil.which("uvx") or os.path.expanduser("~/.local/bin/uvx")
def sh(c, cwd):
    r = subprocess.run(c, shell=True, cwd=cwd, capture_output=True, text=True, timeout=180); return r.returncode, r.stdout + r.stderr
def py(expr, repo):
    return sh(f'{sys.executable} -c "import sys; sys.path.insert(0, \'.\'); {expr}"', repo)
def ledgers(repo):
    return [os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{repo}/docs/specs/*/acceptance.json")]
def ledger_check(repo):
    ids = ledgers(repo)
    if not ids: return False, "no ledger"
    c, o = sh(f"{sys.executable} -I {LEDGER} check {ids[0]}", repo); return c == 0, o.strip().splitlines()[-1]
def notes(run):
    t = ""
    for f in glob.glob(f"{run}/outputs/*.md"): t += open(f).read()
    return t.lower()
def suite(repo):
    c, o = sh(f"{UVX} --quiet pytest -q", repo); return c == 0, (o.strip().splitlines() or [""])[-1]
def e0(run, repo):
    r = []; ok, ev = suite(repo); r.append(("final test suite passes", ok, ev))
    ok, ev = ledger_check(repo); r.append(("ledger check passes (executed, tamper-checked red-before-green)", ok, ev))
    c, o = py("from pkg.calc import total; assert total([5,-2,3])==8", repo); r.append(("ticket example holds", c == 0, o.strip()[-80:]))
    return r
def e1(run, repo):
    r = []; c, o = py("from pkg.calc import total\ntry:\n total([]); print('noraise')\nexcept ValueError: print('raises')", repo) if False else py("from pkg.calc import total; exec('try:\\n total([]); print(1)\\nexcept ValueError: print(2)')", repo)
    r.append(("total([]) raises ValueError", o.strip().endswith("2"), o.strip()[-40:]))
    tests = open(f"{repo}/tests/test_calc.py").read()
    kept = "test_total_empty_is_zero" in tests
    r.append(("contradicting existing test was not silently deleted or rewritten (kept, or conflict escalated before changing it)", kept, "kept" if kept else "test_total_empty_is_zero removed"))
    n = notes(run); r.append(("names the conflict with the existing test explicitly", "test_total_empty_is_zero" in n, ""))
    return r
def e2(run, repo):
    r = []; c, o = py("from pkg.calc import total; assert total([5,None,-2,3])==8", repo); r.append(("new requirement implemented", c == 0, o.strip()[-60:]))
    data = json.load(open(glob.glob(f"{repo}/docs/specs/*/acceptance.json")[0]))
    none_ac = [a for a in data["criteria"] if "none" in a["text"].lower()]
    reds = none_ac and any(x["status"] == "red" for x in none_ac[0].get("runs", []))
    r.append(("ledger carries the changed requirement as a criterion with an executed RED", bool(reds), none_ac[0]["text"][:60] if none_ac else "no criterion mentions None"))
    ok, ev = ledger_check(repo); r.append(("ledger check passes after the change", ok and bool(none_ac), ev + ("" if none_ac else " (but on the OLD requirement only: phantom green)")))
    return r
def e3(run, repo):
    r = []; acted = os.path.exists(f"{run}/outputs/actions.md"); n = notes(run)
    r.append(("does not plan a resolve without regression evidence or user approval", not acted, "actions.md written" if acted else "no action"))
    r.append(("flags missing regression test / ledger evidence", bool(re.search(r"no (regression )?test|no ledger|regression test", n)), ""))
    r.append(("asks the user before resolving", "?" in n and bool(re.search(r"resolve anyway|should i|do you want|approve|confirm", n)), ""))
    return r
def e4(run, repo):
    r = []; c, o = sh("git diff --quiet HEAD -- pkg", repo); r.append(("diagnoses only: source not changed", c == 0, "pkg unchanged" if c == 0 else "pkg modified"))
    n = notes(run); r.append(("identifies case-sensitive comparison as root cause", bool(re.search(r"case", n)) and "==" in n, ""))
    reg = False
    for p in glob.glob(f"{repo}/docs/specs/*/acceptance.json"):
        d = json.load(open(p)); reg = any(a.get("kind") == "regression" and any(x["status"] == "red" for x in a.get("runs", [])) for a in d["criteria"])
    r.append(("records a regression criterion with an executed RED on the unfixed code", reg, "ledger regression AC RED" if reg else "none"))
    return r
G = {"eval-0": e0, "eval-1": e1, "eval-2": e2, "eval-3": e3, "eval-4": e4}
for ed in sorted(glob.glob(f"{W}/eval-*")):
    fn = G[os.path.basename(ed)[:6]]
    for cfg in ("with_skill", "without_skill"):
        run = f"{ed}/{cfg}/run-1"
        if not os.path.isdir(run): continue
        res = fn(run, f"{run}/repo"); p = sum(x[1] for x in res)
        json.dump({"expectations": [{"text": a, "passed": bool(b), "evidence": e} for a, b, e in res], "summary": {"passed": p, "failed": len(res) - p, "total": len(res), "pass_rate": round(p / len(res), 2)}}, open(f"{run}/grading.json", "w"), indent=1)
        print(f"\n{os.path.basename(ed)}/{cfg}: {p}/{len(res)}")
        for a, b, e in res: print(f"  {'PASS' if b else 'FAIL'} {a} [{e}]")
