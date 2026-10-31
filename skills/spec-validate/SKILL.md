---
name: spec-validate
description: Verifies that an implementation plan was actually executed by checking each phase against the code and git history, re-running every success-criteria command, and writing a report of what matches, what deviates, and what is missing, ending in a PASS, PASS WITH NOTES, or FAIL verdict. Use when asked to validate, verify, audit, or check a plan or implementation, review work against a plan, or confirm a feature is done before merge. Judges the work against its plan; for a deploy go/no-go use release-readiness. Use it whenever someone suspects a plan step was skipped or wants proof the work matches the plan.
license: Apache-2.0
---

# Spec Validate

Independent check that the plan's promises were kept. Evidence over claims: a ticked checkbox is a claim; a passing command and matching code is evidence. Read-only except for the report file.

## Operating rules

- **Re-run everything.** Do not trust earlier results, ticked boxes, or a prior session's summary.
- **Report failures plainly.** Do not soften a failing gate or omit an unrun check. Mark unrun checks `NOT RUN` with the reason.
- **Do your own verification inline.** Do not delegate the checking of completed work to another agent.
- **Deviations are not automatically bad.** Classify each as improvement, neutral, or risk, with evidence.
- **Do not fix problems here.** Report them; fixing is `spec-implement` work.

## Inputs

- Plan path (if missing, look in `./docs/specs/plans/` and recent commit messages; ask if still unclear)
- Diff range (default: commits on the current branch since it diverged from the default branch, or the working tree if uncommitted)
- Ledger: `docs/specs/<id>/acceptance.json`; `L=<path to atdd>/scripts/acceptance_ledger.py`
- Report path (default `./docs/specs/validation/YYYY-MM-DD-<slug>.md`)

## Workflow

```
- [ ] 1. Load the plan and run scripts/plan_status.py on it
- [ ] 2. Gather the diff and changed-file list
- [ ] 3. Per phase: compare planned vs actual changes
- [ ] 4. Re-run every Automated criterion; record results
- [ ] 4b. Rerun every AC with `run`, then `check`
- [ ] 5. Check test quality and edge cases; test-gap report
- [ ] 6. Scan the diff for out-of-scope changes
- [ ] 7. Write the report and verdict
```

**1.** `python scripts/plan_status.py <plan.md>` prints per-phase counts of ticked and unticked criteria and the commands found in backticks. Use it to build the command list in step 4 and to spot phases claimed complete with open boxes.

**2.** `git log --oneline <base>..HEAD`, `git diff --stat <base>..HEAD`, `git status`. Without git, compare against file mtimes and ask the user what changed.

**3.** For each phase, list planned files and changes, then confirm each exists in the diff and does what the plan says. Read the code, not just the diff stat.

**4.** Run each command from the plan, plus the full test suite and the repo's lint/type-check/build commands (from README, CLAUDE.md/AGENTS.md, Makefile, package scripts). Record exit status and the key output line.

**4b.** For each AC: `python $L run <id> AC-n --cmd "<its test command>"` (take the command from the ledger's last run). Then `python $L verify <id>` at the candidate commit (`check` alone reads old evidence); a FAIL is a FAIL verdict. Stale criteria and a test changed between RED and GREEN are blocking. `render <id>` goes into the report.

**5.** If the `codegraph` skill is available and the repo is Python, run `codegraph delta` with the output of `python $L codegraph-args <id>` (symbol ids, never file paths). Pipe the report into the `codegraph` skill's gate: `codegraph-slicer delta --base-db B --head-db H --full --max-tokens 200000 $(python3 <atdd>/scripts/acceptance_ledger.py codegraph-args <id>) | python3 <codegraph>/scripts/delta_gate.py`. Do not gate on raw `untested_modified_symbols`: when any test in a file changes, the test module itself counts as updated evidence, and because it imports the module under change, every symbol there looks covered. `delta_gate.py` requires at least one test-function symbol as evidence per changed symbol, reports module-level ids (ending in `:`) as warnings, and fails on forbidden imports or new cycles. This check is static; for other languages skip it and rely on the executed runs. Do new tests assert behavior or only exercise code? Are error paths and boundaries covered? Would the tests fail if the feature were removed? When cheap, check by temporarily reverting the key line, then restore it.

**6.** Flag changes in the diff the plan did not call for.

## Verdict rules

- **FAIL**: `check` fails, any automated criterion fails, a planned phase is missing or only partial, or the full suite regresses.
- **PASS WITH NOTES**: all gates pass but deviations carry risk, or manual criteria remain.
- **PASS**: all gates pass, code matches the plan, only manual verification steps remain for the user.

## Report

Use `references/report-template.md`. Output to the user: verdict first, then a table of phases (status), failing items with the command and error, deviations worth a decision, and the manual checks the user must perform.

## Gotchas

- Tests passing on a dirty tree can hide uncommitted files the plan needs. Check `git status`.
- A flaky test is a finding. Re-run once, report both results, do not average them away.
- Plans without runnable criteria cannot be validated mechanically. Say so and validate by code reading.
