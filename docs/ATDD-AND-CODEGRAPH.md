# ATDD and the codegraph gate

What you get here: why every skill in the chain is built around acceptance criteria, exactly what the acceptance ledger records and refuses, why it now digests the test and harness and re-executes at release, how the codegraph delta gate adds a second check on Python repos, and what none of it can see. Read this once; it explains every `GATE: FAIL` and `VERIFY: FAIL` you'll meet later.

## Why acceptance criteria are the contract

The skills pass one artifact down the chain: a list of Given/When/Then criteria, `AC-1`, `AC-2`, and so on, stored in `docs/specs/<id>/acceptance.json`. `jira-ticket-enrich` drafts them. `jira-rca` and `root-cause-trace` add their confirming test as one. `atdd` turns each into a failing test. `spec-plan` assigns each to a phase and won't approve a plan with an AC left over. `spec-implement` drives each to green inside its phase. `spec-validate`, `commit-gate`, `release-readiness`, `fix-and-ship`, and `error-tracker-resolve` all read the same file and refuse to proceed if it isn't satisfied. `pr-describe` prints it as the traceability matrix in the PR. `jira-value-score` adds the post-release outcome criteria that get reviewed weeks later.

That's the whole mechanism. One file, written only by the script that ran the tests, read by every gate. The per-skill read/write map is in [SKILLS.md](../SKILLS.md#how-the-weld-works).

## Two rules

### Discovery: no observable Then means a question, not a guess

A criterion must have a Then you can observe from outside the code: a response body, a stored row, a rendered string, an emitted event. "The discount is handled correctly" has no observable Then, so it isn't a criterion yet. The skill writes it down as a numbered question for the reporter and stops before writing tests.

This is where most of the value shows up, and it shows up before any code exists. In the PAY-482 example the reporter wrote "save10 does nothing." The enrichment turned that into "Given a cart total of 100.00 When the code save10 is applied in lower case Then the total is 90.00" and surfaced the question it couldn't answer: should mixed case like `Save10` work too? Whoever answers that decides what the test asserts. Guessing it into the test would have shipped an assumption with a green checkmark on it.

`atdd` marks each criterion `confirmed` (from the ticket) or `proposed` (it added the error or boundary case the ticket implied), so the reviewer can tell which assertions came from the requester. When the answer arrives and changes the text, `revise <id> AC-n "new text"` records the old text under `revisions` and invalidates the old evidence; the gate then asks for a new RED and GREEN against the new text.

### Enforcement: red before green, executed, not asserted, and not edited in between

A test that passes before the change tests nothing. A test that was weakened after it failed proves even less. The ledger exists to make both statements checkable by someone who wasn't in the session.

`acceptance_ledger.py run <id> AC-n --cmd "<test command>"` runs your command through the shell and records, per run: timestamp, `via` (`run` or `verify`), the command, exit code, derived status, short and full git SHA, `--red-exit` and `--timeout` used, a SHA-256 of the full output, and the last 20 lines. Nobody writes the status field. The script derives it:

| Exit code | Output | Status |
|---|---|---|
| 0 | anything | `green` |
| in `--red-exit` (default `1`) | no pytest collection/import error pattern | `red` |
| in `--red-exit` | matches `N errors in Ns` or a line starting `ERROR` | `error` |
| anything else, or timeout (recorded as 124) | anything | `error` |

`error` never satisfies the gate. An import typo, a missing fixture, a wrong selector, or a hung test all land there, and the printed message says so: `ERROR is not RED: the test did not run to an assertion`. A test that can't be collected proves nothing about the behavior.

Each run also records four digests, taken just before the command executes:

| Digest | What it hashes |
|---|---|
| `criterion_sha` | the AC text, whitespace-normalized |
| `test_sha` | the source of the linked test function, decorators included (`test_scope: function`); the whole file if the name can't be found (`file`); `null` if the file is missing (`unresolved`, which fails the gate) |
| `harness_sha` | path plus content hash of every `conftest.py` from the root down to the test's directory, and root-level `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `package.json`, `jest.config.*`, `vitest.config.*`, `playwright.config.*` |
| `cmd` | the command, whitespace-normalized |

`check <id> [--phase N]` applies the gate to every in-scope AC whose kind isn't `outcome`: the latest run is GREEN, its `criterion_sha` matches the current text, and it pairs with the most recent earlier RED that has the same criterion, test, harness, and command digests. Each miss prints a literal reason:

| Message | Cause | Fix |
|---|---|---|
| `no linked test` / `no RED run recorded` | nothing ran yet | `link`, then `run` |
| `criterion revised after evidence: needs new RED then GREEN` | text changed via `revise` or by hand | new RED, then GREEN |
| `test changed between RED and GREEN` | `test_sha` differs | restore the test, or record a new RED with the new test |
| `test harness changed between RED and GREEN` | `harness_sha` differs | revert, or record a new RED under the new harness |
| `test command changed between RED and GREEN` | `cmd` differs | re-run GREEN with the RED command |
| `legacy run without digests: re-run` | run predates digests | new RED, then GREEN |
| `test digest unresolved` | linked test file doesn't exist | link a `path::name` whose file exists |

Two more refusals at `run` time: a command that doesn't contain the linked test's name is rejected (`--cmd "true"` against `test_ac1_lowercase_code_applies` exits with an error instead of recording GREEN; `--allow-unlinked-cmd` exists for runners whose selector syntax lacks the name, and is recorded), and an AC with no linked test can't be run.

Verified on 2026-10-31 on a scratch repo: RED on exit 1, then the assertion weakened from `== 90.0` to `== 100.0` with no code change, then GREEN. `check` printed `test changed between RED and GREEN` and exited 1. Restoring the test and fixing the code gave a GREEN that paired with the original RED, and `check` passed. `revise` on the same AC then produced `criterion revised after evidence: needs new RED then GREEN`.

### Why the digests exist

Agents under pressure to go green edit tests more often than they fix code. ImpossibleBench (arXiv 2510.20270) measured this on tasks whose tests were deliberately unsatisfiable: for Claude-family agents, more than 79% of the shortcuts taken were direct assertion edits, with the rest split between overriding comparison operators, special-casing the test input, and recording state. The usual countermeasure, a read-only test directory, doesn't help, because a `conftest.py` hook or a runner config edit can force a pass without touching the test file. That's why `harness_sha` covers the conftest chain and runner configs, not just the test. Two more observations shaped `verify`: Jira test-management tools let a "passed" mark be set with no link to a commit, and Sentry resolves an issue on release rather than on merge. So the release gate re-executes at a named commit, and `error-tracker-resolve` demands that commit's `verify` before it closes anything.

### verify: the release gate

`check` reads evidence that was recorded earlier; a GREEN from this morning says nothing about the commit being shipped this afternoon. `verify <id> [--phase N]` re-executes each blocking AC's latest GREEN command at HEAD with its recorded `--red-exit` and `--timeout`, stores those runs with `via: verify`, applies the same gate, appends an entry to `verifications` (commit, phase, dirty flag, result), and prints the full commit sha:

```
commit: 1cdd2cac0b9d60d95d5ceaaa2c24e90eb627fdae
AC-1: re-ran `pytest -q tests/test_discounts.py::test_ac1_lowercase_code_applies` -> GREEN (exit 0)
AC      kind            phase  result        detail
AC-1    regression      1      ok
GATE: PASS
VERIFY: PASS at 1cdd2cac0b9d60d95d5ceaaa2c24e90eb627fdae
```

It refuses a working tree that differs from HEAD (tracked changes, or an untracked linked test or harness file; the ledger files themselves are exempt) with `commit or stash first`. `--allow-dirty` runs anyway and records `dirty: true`. `release-readiness`, `spec-validate`, `fix-and-ship`, and `error-tracker-resolve` call `verify`; `commit-gate` and `spec-implement` call `check`, because during development the tree is supposed to be dirty.

### Kinds

A kind is set when an AC is created and never changes, so a failing criterion can't be relabeled out of the gate.

| Kind | Set by | Blocks `check`/`verify` |
|---|---|---|
| `behavior` | default for `add` and for enrichment criteria | yes |
| `regression` | `init --from` on an enrichment whose `type.value` is BUG (first criterion); `jira-rca` and `root-cause-trace` via `add --kind regression` | yes, and must be RED on the unfixed code |
| `instrumentation` | `init --from` on a value-score file (from each `outcome_criteria[].instrumentation_text`); `add --kind instrumentation` | yes |
| `outcome` | `init --from` on a value-score file; `add --kind outcome --metric <id> --verify-after YYYY-MM-DD` | no; shown as `post-release` |

Outcome ACs have no test. They're the metric movement the value score promised, checked on the dashboard after release: `outcomes-due <id>` (or `--all` across `docs/specs/*`) lists the ones past `verify_after` with no result; `record-outcome <id> AC-n --result met|not-met|inconclusive --evidence "<reading>"` closes one. An outcome AC records which instrumentation AC feeds it (`instrumented_by`).

### What the eval showed

The `atdd` skill was run against the same bug with and without the skill loaded (Sonnet, 2026-10-31). With the skill: 6 of 6 checks passed. Without it: 4 of 6. The two misses without the skill: there was no persisted red/green evidence, only a claim in the chat that tests had failed and then passed, and the model created a branch nobody asked for. The skill's value isn't that the model can't do TDD; it's that the evidence survives the session, carries digests, and the gate can read it.

## The codegraph gate

The ledger proves that the tests you chose ran red and then green on the same test and harness. It can't tell you whether the change touched code none of those tests reach. On Python repos the `codegraph` skill adds that second check statically.

### What it does

`codegraph-slicer sync` parses the repo with `ast` into a SQLite snapshot: functions, classes, methods, and the import, call, inheritance, type-use, and `TESTS` edges between them. `delta` compares two snapshots (base and head revisions) and reports, among other things, `test_coverage`: for every changed symbol, which test symbols can reach it and which of those were themselves updated in the diff or passed in with `--selected-test`.

`scripts/delta_gate.py` reads that JSON from stdin and applies two rules: (1) every changed non-module symbol needs at least one piece of evidence that is a real test function symbol, not a test module, and (2) any pre-existing test function that was removed or modified fails the gate unless explicitly approved with `--allow-test-change SYMBOL` (because retiring or rewriting an existing test is a requirement decision for a person). Module-level ids (ending in `:`) print as `WARN` and never fail. It exits 1 on any `GAP`, any unapproved `existing-test change`, any `boundary_violations` entry, or any `new_cycles` entry; 0 otherwise; 2 if the input isn't unbudgeted `--full` delta JSON.

### Why the gate script exists instead of the raw field

`delta` also reports `untested_modified_symbols`. Don't gate on it. Whenever any test in a file changes, the test module symbol counts as "updated", and because that module imports the module under change, every symbol there looks covered. In the scratch run the fix commit added an untested helper `describe()` next to the fixed function; `untested_modified_symbols` was `[]`, and the gate printed:

```
app.discounts:describe        GAP   no updated or selected test symbol (module-only: tests.test_discounts:)
RESULT: FAIL (1 gap(s), 0 existing-test change(s), 0 violation(s), 0 cycle(s))
```

The parenthetical shows the masking: the only evidence was the module `tests.test_discounts:`, which the gate discards.

### Why selected tests are symbol ids

`--selected-test` accepts a file path, a module name, or a symbol id. Use symbol ids only (`tests.test_discounts:test_ac1_lowercase_code_applies`). Reachability flows through module `IMPORTS` and `DEFINES` edges, so selecting a file or module credits every changed symbol in any module the test file imports; selecting the one test function credits only what that function reaches. A pytest node id (`tests/x.py::test_y`) exits 2 with `unobserved test selection`, as does any selection that doesn't exist in the head snapshot.

`acceptance_ledger.py codegraph-args <id>` converts each linked pytest id in the ledger to the right flag and prints them on one line, so the gate command is:

```bash
codegraph-slicer delta --base-db B --head-db H --full --max-tokens 200000 $(python3 <atdd>/scripts/acceptance_ledger.py codegraph-args <id>) \
  | python3 <codegraph>/scripts/delta_gate.py
```

A leading `src/` is stripped only for pure src layouts; non-pytest ids are skipped with a note on stderr. Sync the project root, not a package directory, or module ids lose their prefix and won't match.

### Boundaries and cycles

`--forbid-import SOURCE_PREFIX TARGET_PREFIX`, repeatable, turns an architecture rule into a gate failure (`app.domain app.web`, for example). There are no default rules. New import or call cycles between base and head fail the gate on their own. Both print as `FAIL boundary_violations:` or `FAIL new_cycles:` with the JSON.

## How the two fit together

| | Acceptance ledger | Codegraph gate |
|---|---|---|
| Evidence | Executed test runs with exit code, output hash, and digests of criterion, test, harness, command | Static reachability in the parsed graph |
| Proves | The chosen tests failed before and passed after, unchanged in between, and still pass at the release commit | Every changed symbol is reachable from some updated or selected test function |
| Can't prove | That the chosen tests cover everything that changed | That any test ran or passed |
| Languages | Any; `--red-exit` per runner; harness list covers pytest and the JS runners | Python only |
| Development gate | `check` (`atdd`, `spec-implement`, `commit-gate` as WARN) | none |
| Release gate | `verify` (`spec-validate`, `release-readiness`, `fix-and-ship`, `error-tracker-resolve`) | `delta_gate.py` (`spec-validate`, `release-readiness`, `fix-and-ship`) |

Together: the ledger answers "did the acceptance tests mean something, and do they still pass on what we're shipping", the gate answers "did the change sneak past them". Both are inputs to a human decision. `release-readiness` and `fix-and-ship` accept a written, user-approved exception for a codegraph gap. A hotfix exception to the ledger gates exists too, but only with explicit user approval in the conversation, and `pr-describe` records it in the PR description so the reviewer sees it.

## Limits, stated plainly

- `test_sha` covers the linked test function only. A helper or fixture edited elsewhere in the same test file, or in a module the test imports that isn't on the harness list, changes behavior without changing the digest. Review the test diff anyway.
- The ledger trusts the command you give it within limits. It checks that the command names the linked test and classifies the exit code; a shell `--cmd` can still swap files mid-run or point at a different interpreter. `verify` re-executing the recorded command at HEAD narrows this; it doesn't close it.
- The ledger is a JSON file in the repo. Anyone can hand-edit it. The defenses are `verify` (which re-runs rather than trusting stored runs) and the ledger's git history in the PR, where a rewritten run stands out. Treat the file as evidence to review, not as proof.
- Any `pyproject.toml` or `package.json` change between RED and GREEN trips the harness check, including a legitimate new dependency. Record RED again under the new harness: stash the implementation, `run`, unstash, `run`. `skills/atdd/references/ledger-format.md` has the sequence.
- The error detection is pytest-shaped. For other runners, an exit code in `--red-exit` is RED even if the output describes a harness error. Pick `--red-exit` carefully and read the tail.
- Flaky tests record whatever happened. A RED that was a flake and a GREEN that was luck both carry matching digests. Re-run once; if they differ, fix the flake first.
- `init --from` imports `acceptance_criteria` as-is and synthesizes a criterion from the reproduction only when none were supplied. There's no `remove`; a wrong criterion is `revise`d (its evidence resets) or superseded by a new AC with a note in the plan.
- Outcome ACs are promises, not gates. `outcomes-due` tells you they're overdue; nothing blocks a later release because a metric didn't move.
- Codegraph is static syntax analysis. Dynamic dispatch, `setattr`, star imports, `globals()`, runtime registration, and `self.method()` resolved to an override are not modelled. "No callers" means "no static callers".
- Codegraph reachability is import-level. A test that imports a module can appear to reach a function it never calls; symbol-id selection narrows this but doesn't remove it. A `GAP` is a real signal; an `ok` is weaker evidence than a `GAP`.
- Selected tests are never executed by `delta`. Run them through the ledger.
- Entrypoint discovery (`__main__`, paths containing `cli`, `scripts`, `mcp`, symbols named `main`) is heuristic; framework-decorated handlers aren't found.
- Token budgets in `map`, `slice`, and `flow` are `chars / 4` estimates. `flow` models `try`/`except`/`finally`, `with`, `async with`, and comprehensions conservatively, and refuses `await`, `yield`, lambdas, nested definitions, or imports with a source location.
- Non-Python repos get the ledger only. That's still red-before-green per AC with digests and a re-executed release gate, which is the part that catches most of the problems; the missing piece is the untested-change check, and the reviewer has to do it by reading the diff.
