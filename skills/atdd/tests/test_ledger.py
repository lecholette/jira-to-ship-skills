"""Tests for scripts/acceptance_ledger.py, run against throwaway git repos.

ACCEPTANCE_LEDGER may point at another copy of the script (used for mutation testing).
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

LEDGER = os.environ.get("ACCEPTANCE_LEDGER") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "acceptance_ledger.py")
SID = "ABC-1"
TEST_ID = "tests/test_calc.py::test_ac1_total_ignores_negatives"
CMD = f"{sys.executable} -m pytest -q -p no:cacheprovider {TEST_ID}"

BUGGY = "def total(xs):\n    return sum(xs)\n"
FIXED = "def total(xs):\n    return sum(x for x in xs if x > 0)\n"
REGRESSED = "def total(xs):\n    return sum(xs) + 0\n"
TEST_SRC = textwrap.dedent("""\
    from calc import total


    def test_other():
        assert total([]) == 0


    def test_ac1_total_ignores_negatives():
        assert total([5, -2, 3]) == 8
    """)
FORCE_PASS_CONFTEST = textwrap.dedent("""\
    import pytest


    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        outcome = yield
        rep = outcome.get_result()
        if rep.failed:
            rep.outcome = "passed"
    """)


def git(repo, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=repo,
                   check=True, capture_output=True, timeout=30)


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p) or repo, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def commit(repo, msg="c"):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)


def L(repo, *args):
    r = subprocess.run([sys.executable, LEDGER, "--root", str(repo), *args],
                       capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout + r.stderr


def ledger(repo):
    with open(os.path.join(repo, "docs", "specs", SID, "acceptance.json"), encoding="utf-8") as f:
        return json.load(f)


def run_ac(repo, cmd=CMD, ac="AC-1"):
    code, out = L(repo, "run", SID, ac, "--cmd", cmd)
    assert code == 0, out
    return ledger(repo)["criteria"][[c["id"] for c in ledger(repo)["criteria"]].index(ac)]["runs"][-1]


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    write(r, ".gitignore", "__pycache__/\n.pytest_cache/\n")
    write(r, "pytest.ini", "[pytest]\n")
    write(r, "calc.py", BUGGY)
    write(r, "tests/test_calc.py", TEST_SRC)
    commit(r, "init")
    assert L(r, "init", SID)[0] == 0
    assert L(r, "add", SID, "AC-1", "Given [5,-2,3] When total() Then 8", "--test", TEST_ID)[0] == 0
    return r


def red_then_green(repo):
    assert run_ac(repo)["status"] == "red"
    write(repo, "calc.py", FIXED)
    assert run_ac(repo)["status"] == "green"


def test_happy_path_red_then_green_passes(repo):
    red_then_green(repo)
    code, out = L(repo, "check", SID)
    assert code == 0, out
    assert "GATE: PASS" in out
    run = ledger(repo)["criteria"][0]["runs"][-1]
    assert run["test_scope"] == "function" and run["harness_files"] == ["pytest.ini"]


def test_editing_another_test_in_the_same_file_is_allowed(repo):
    assert run_ac(repo)["status"] == "red"
    write(repo, "tests/test_calc.py", TEST_SRC.replace("total([]) == 0", "total([1]) == 1"))
    write(repo, "calc.py", FIXED)
    run_ac(repo)
    assert L(repo, "check", SID)[0] == 0


def test_weakened_assertion_after_red_fails_check(repo):
    assert run_ac(repo)["status"] == "red"
    write(repo, "tests/test_calc.py", TEST_SRC.replace("== 8", "is not None"))
    assert run_ac(repo)["status"] == "green"  # code still buggy
    code, out = L(repo, "check", SID)
    assert code == 1
    assert "test changed between RED and GREEN" in out


def test_new_red_with_changed_test_is_the_legitimate_path(repo):
    assert run_ac(repo)["status"] == "red"
    write(repo, "tests/test_calc.py", TEST_SRC.replace("[5, -2, 3]) == 8", "[5, -2, 3, -1]) == 8"))
    assert run_ac(repo)["status"] == "red"
    write(repo, "calc.py", FIXED)
    run_ac(repo)
    assert L(repo, "check", SID)[0] == 0


def test_conftest_forcing_pass_after_red_fails_check(repo):
    assert run_ac(repo)["status"] == "red"
    write(repo, "tests/conftest.py", FORCE_PASS_CONFTEST)
    assert run_ac(repo)["status"] == "green"  # code still buggy
    code, out = L(repo, "check", SID)
    assert code == 1
    assert "test harness changed between RED and GREEN" in out


def test_changed_command_between_red_and_green_fails_check(repo):
    assert run_ac(repo)["status"] == "red"
    assert run_ac(repo, cmd=CMD + " || true")["status"] == "green"
    code, out = L(repo, "check", SID)
    assert code == 1 and "test command changed between RED and GREEN" in out


def test_revise_after_green_fails_until_new_red_and_green(repo):
    red_then_green(repo)
    assert L(repo, "revise", SID, "AC-1", "Given [5,-2,3] When total() Then 8, ignoring negatives")[0] == 0
    c = ledger(repo)["criteria"][0]
    assert c["revisions"][0]["old_text"] == "Given [5,-2,3] When total() Then 8"
    code, out = L(repo, "check", SID)
    assert code == 1 and "criterion revised after evidence: needs new RED then GREEN" in out
    run_ac(repo)  # GREEN alone for the new text is not enough
    code, out = L(repo, "check", SID)
    assert code == 1 and "criterion revised after evidence" in out  # only stale REDs exist
    write(repo, "calc.py", BUGGY)
    assert run_ac(repo)["status"] == "red"
    write(repo, "calc.py", FIXED)
    run_ac(repo)
    assert L(repo, "check", SID)[0] == 0


def test_verify_reexecutes_at_head_and_fails_on_regression(repo):
    red_then_green(repo)
    commit(repo, "fix")
    code, out = L(repo, "verify", SID)
    assert code == 0, out
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True,
                          timeout=10).stdout.strip()
    assert f"commit: {head}" in out and "VERIFY: PASS" in out
    data = ledger(repo)
    assert data["criteria"][0]["runs"][-1]["via"] == "verify"
    assert data["verifications"][-1] == dict(data["verifications"][-1], commit=head, result="pass")

    write(repo, "calc.py", REGRESSED)
    commit(repo, "regress")
    assert L(repo, "check", SID)[0] == 0  # check alone reads old evidence
    code, out = L(repo, "verify", SID)
    assert code == 1 and "VERIFY: FAIL" in out
    assert ledger(repo)["criteria"][0]["runs"][-1]["status"] == "red"


def test_verify_refuses_dirty_tree(repo):
    red_then_green(repo)  # calc.py fix is uncommitted
    code, out = L(repo, "verify", SID)
    assert code == 1 and "calc.py" in out and "commit or stash" in out
    assert all(r["via"] == "run" for r in ledger(repo)["criteria"][0]["runs"])


def test_verify_fails_when_test_changed_since_red(repo):
    red_then_green(repo)
    write(repo, "tests/test_calc.py", TEST_SRC.replace("== 8", ">= 0"))
    commit(repo, "fix and weaken")
    code, out = L(repo, "verify", SID)
    assert code == 1 and "test changed between RED and GREEN" in out


def test_outcome_acs_excluded_from_check_and_listed_when_due(repo):
    red_then_green(repo)
    assert L(repo, "add", SID, "AC-2", "activation rises", "--kind", "outcome",
             "--metric", "activation_rate", "--verify-after", "2000-01-01")[0] == 0
    assert L(repo, "add", SID, "AC-3", "retention rises", "--kind", "outcome",
             "--metric", "retention", "--verify-after", "2999-01-01")[0] == 0
    code, out = L(repo, "check", SID)
    assert code == 0, out
    assert out.count("post-release") == 2
    code, out = L(repo, "outcomes-due", SID)
    assert code == 0 and "AC-2" in out and "AC-3" not in out and "1 outcome criteria due" in out
    code, out = L(repo, "outcomes-due", "--all")
    assert f"{SID}\tAC-2" in out
    assert L(repo, "run", SID, "AC-2", "--cmd", "true")[0] != 0
    assert L(repo, "record-outcome", SID, "AC-2", "--result", "met", "--evidence", "dash: 38%->44%")[0] == 0
    code, out = L(repo, "outcomes-due", "--all")
    assert "AC-2" not in out and "0 outcome criteria due" in out
    assert L(repo, "add", SID, "AC-4", "x", "--kind", "outcome")[0] != 0
    assert L(repo, "add", SID, "AC-5", "x", "--metric", "m")[0] != 0


def test_only_outcome_acs_in_scope_fails_check(tmp_path):
    assert L(tmp_path, "init", SID)[0] == 0
    L(tmp_path, "add", SID, "AC-1", "x", "--kind", "outcome", "--metric", "m", "--verify-after", "2000-01-01")
    code, out = L(tmp_path, "check", SID)
    assert code == 1 and "no in-scope blocking criteria" in out


def test_init_from_bug_enrichment_marks_first_regression(tmp_path):
    enr = tmp_path / "enr.json"
    enr.write_text(json.dumps({"key": "ABC-1", "type": {"value": "BUG"},
                               "acceptance_criteria": ["Given repro When run Then fixed", "Given b Then c"]}))
    code, out = L(tmp_path, "init", SID, "--from", str(enr))
    assert code == 0, out
    kinds = [c["kind"] for c in ledger(tmp_path)["criteria"]]
    assert kinds == ["regression", "behavior"]


def test_init_bug_reproduction_synthesized_only_without_criteria(tmp_path):
    enr = tmp_path / "enr.json"
    enr.write_text(json.dumps({"type": {"value": "BUG"},
                               "reproduction": {"steps": ["open", "click"], "expected": "saved"}}))
    assert L(tmp_path, "init", SID, "--from", str(enr))[0] == 0
    c = ledger(tmp_path)["criteria"]
    assert len(c) == 1 and c[0]["kind"] == "regression" and c[0]["text"].startswith("Given open; click")


def test_init_feature_and_value_score_outcomes(tmp_path):
    enr = tmp_path / "enr.json"
    enr.write_text(json.dumps({"type": {"value": "STORY"}, "acceptance_criteria": ["Given a Then b"]}))
    vs = tmp_path / "vs.json"
    vs.write_text(json.dumps({"outcome_criteria": [{
        "text": "activation 38% -> 50% within 30 days", "metric": "activation_rate",
        "verify_after": "2026-12-01", "instrumentation_text": "Given step 3 When skip Then event fires"}]}))
    assert L(tmp_path, "init", SID, "--from", str(enr), "--from", str(vs))[0] == 0
    c = ledger(tmp_path)["criteria"]
    assert [x["kind"] for x in c] == ["behavior", "instrumentation", "outcome"]
    assert c[2]["metric"] == "activation_rate" and c[2]["verify_after"] == "2026-12-01"
    assert c[2]["instrumented_by"] == "AC-2"
    assert all(x["text_sha"] for x in c)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"outcome_criteria": [{"text": "t", "metric": "m", "verify_after": "2026-12-01"}]}))
    code, out = L(tmp_path / "other", "init", SID, "--from", str(bad))
    assert code != 0 and "instrumentation_text" in out


def test_legacy_runs_without_digests_do_not_satisfy_gate(tmp_path):
    p = tmp_path / "docs" / "specs" / SID
    p.mkdir(parents=True)
    old = {"at": "2026-01-01T00:00:00Z", "cmd": "pytest t.py::test_a", "exit": 1, "status": "red",
           "git": None, "output_sha256": "x", "tail": []}
    (p / "acceptance.json").write_text(json.dumps({"id": SID, "criteria": [{
        "id": "AC-1", "text": "t", "phase": None, "test": "t.py::test_a",
        "runs": [old, dict(old, exit=0, status="green", at="2026-01-02T00:00:00Z")]}]}))
    code, out = L(tmp_path, "check", SID)
    assert code == 1 and "legacy run without digests: re-run" in out
    assert L(tmp_path, "render", SID)[0] == 0


def test_error_is_not_red_and_unlinked_cmd_refused(repo):
    write(repo, "tests/test_calc.py", "import nope\n" + TEST_SRC)
    assert run_ac(repo)["status"] == "error"
    code, out = L(repo, "run", SID, "AC-1", "--cmd", "true")
    assert code != 0 and "does not reference the linked test" in out
    run = run_ac(repo, cmd="exit 3 # test_ac1_total_ignores_negatives")
    assert run["status"] == "error"
    code, _ = L(repo, "run", SID, "AC-1", "--cmd", "exit 3", "--allow-unlinked-cmd", "--red-exit", "3")
    assert code == 0 and ledger(repo)["criteria"][0]["runs"][-1]["status"] == "red"
