# Ledger format: docs/specs/<id>/acceptance.json

Written only by `scripts/acceptance_ledger.py`. Never edit it by hand: evidence is derived from executed runs.

```json
{
  "id": "ABC-123", "created": "2026-10-31T17:00:00Z",
  "criteria": [{
    "id": "AC-1", "kind": "regression", "phase": 1,
    "text": "Given ... When ... Then ...",
    "text_sha": "<sha256 of whitespace-normalized text>",
    "test": "tests/test_calc.py::test_ac1_total",
    "revisions": [{"at": "...", "old_text": "...", "old_sha": "..."}],
    "runs": [{
      "at": "...", "via": "run|verify", "cmd": "pytest -q tests/test_calc.py::test_ac1_total",
      "exit": 1, "status": "red|green|error", "git": "abc1234", "commit": "<full sha>",
      "criterion_sha": "<text_sha when the run happened>",
      "test_sha": "<sha256>", "test_scope": "function|file|unresolved",
      "harness_sha": "<sha256>", "harness_files": ["pytest.ini", "tests/conftest.py"],
      "red_exit": "1", "timeout": 300, "allow_unlinked": false,
      "output_sha256": "...", "tail": ["last 20 lines"]
    }]
  }, {
    "id": "AC-3", "kind": "outcome", "text": "...", "text_sha": "...",
    "metric": "activation_rate", "verify_after": "2026-12-01", "instrumented_by": "AC-2",
    "results": [{"at": "...", "result": "met|not-met|inconclusive", "evidence": "...", "git": "..."}],
    "runs": [], "revisions": []
  }],
  "verifications": [{"at": "...", "commit": "<full sha>", "phase": null, "dirty": false, "result": "pass|fail"}]
}
```

## Digests

- `test_sha`: for `path.py::[Class::]func` (parametrize suffix `[...]` ignored), sha256 of that definition's source including decorators (`test_scope: function`). If the name cannot be found, the whole file (`file`). Other ids hash the file before `::`. Missing file: `null` (`unresolved`), which fails the gate.
- `harness_sha`: sha256 over `path + sha256(content)` of each existing file, sorted: every `conftest.py` from `--root` down to the test's directory, and root-level `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `package.json`, `jest.config.*`, `vitest.config.*`, `playwright.config.*`.
- Digests are taken just before the command runs.

## Gate (check and verify)

For each in-scope AC whose kind is not `outcome`: the latest run must be GREEN with `criterion_sha` equal to the current text's sha. It pairs with the most recent earlier RED that has the same `criterion_sha`. Failure messages:

| Message | Cause | Fix |
|---|---|---|
| `criterion revised after evidence: needs new RED then GREEN` | text changed (via `revise` or by hand) after the runs | new RED, then GREEN |
| `test changed between RED and GREEN` | `test_sha` differs | restore the test, or record a new RED with the new test |
| `test harness changed between RED and GREEN` | `harness_sha` differs (new conftest, config edit) | revert, or record a new RED under the new harness |
| `test command changed between RED and GREEN` | `cmd` differs (whitespace-normalized) | re-run GREEN with the RED command |
| `legacy run without digests: re-run` | run predates digests | new RED, then GREEN |
| `test digest unresolved` | linked test file does not exist | link a `path::name` whose file exists |

A legitimate harness change (adding a dependency to `pyproject.toml`) also trips the harness check. Record RED again under the new harness: stash the implementation, `run`, unstash, `run`.

`verify` additionally requires a git commit, a tree equal to HEAD (tracked changes excluding ledger files, plus untracked linked tests or harness files, block unless `--allow-dirty`), and re-executes the latest GREEN command with its recorded `--red-exit` and `--timeout`.

## Kinds

`behavior` (default), `regression` (bug reproduction; first enrichment criterion when `type.value` is BUG), `instrumentation` (event fires or query returns; blocking), `outcome` (metric movement after release; non-blocking, shown as `post-release`, listed by `outcomes-due` once `verify_after <= today` and `results` is empty).

## Inputs to init --from

- Enrichment: `acceptance_criteria` (strings), `reproduction.steps/expected` (used only when there are no criteria), `type.value`.
- Value score: `outcome_criteria: [{text, metric, verify_after, instrumentation_text}]`, all required. Each makes an instrumentation AC then an outcome AC.
