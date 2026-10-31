---
name: release-readiness
description: Checks whether a change is ready to release. Runs the type checker and tests, reviews configuration and feature-flag differences against production, scans for error-tracker regressions, and returns a verdict with blocking issues separated from warnings. Use before deploying or merging, after significant changes, or when asked is this ready to deploy, release check, pre-release validation, or go/no-go. Judges the change against production; to check work against its plan use spec-validate, and for quick pre-commit checks use commit-gate. Use it for any ship or don't-ship question about a branch, release, or deploy tonight.
license: Apache-2.0
---

# Release Readiness

Produce a go/no-go verdict with evidence. A green result means the checks passed, not that anything shipped; releasing is a separate step that needs user approval.

## Severity

| Level | Meaning | Examples |
|---|---|---|
| BLOCKING | Do not release | Build fails, type errors in changed code, failing tests caused by this change, missing migration, secrets in diff, flag or config mismatch that changes production behavior |
| WARNING | Release possible with user acknowledgement | Pre-existing test failures (with proof), new lint warnings, untested edge, large diff, dependency bumps |
| INFO | Note only | Style, docs gaps |

## Checklist

```
- [ ] 1. Detect project commands
- [ ] 2. Working tree and build
- [ ] 3. Type check
- [ ] 4. Tests
- [ ] 5. Config and flags review
- [ ] 6. Error-tracker check
- [ ] 7. Acceptance ledger and test gaps
- [ ] 8. Verdict
```

1. **Detect commands** from README, CLAUDE.md/AGENTS.md, package.json, Makefile, pyproject, CI config. Ask once if unclear. The `commit-gate` skill can run steps 2-4's fast subset.
2. **Working tree and build.** `git status --short` (no unintended or untracked-but-needed files), then the production build. Failure is BLOCKING.
3. **Type check.** Run the repo's checker (tsc, pyright, mypy, etc.). Errors in changed files are BLOCKING. Errors elsewhere: compare against the deploy branch; pre-existing is a WARNING.
4. **Tests.** Run the full suite or CI's equivalent. For each failure, decide whether this change caused it (rerun on the deploy branch). Caused by this change: BLOCKING. Pre-existing or flaky: WARNING with evidence.
5. **Config and flags.** List environment variables, feature flags, and config files changed in the diff. Compare each against the production values the project documents or the user supplies. New required variables missing from production are BLOCKING. Do not print secret values.
6. **Error tracker.** If configured, list unresolved issues first seen in the last 24 hours or since the last release. New error groups touching changed code are BLOCKING; others WARNING.
7. **Acceptance ledger and test gaps.** A change with no acceptance criteria at all is itself a warning: say which behavior is unverified. If `docs/specs/*/acceptance.json` exists, run `python3 <atdd skill dir>/scripts/acceptance_ledger.py verify <id>` at the release candidate commit (`atdd` skill); `check` alone reads old evidence. Non-zero exit is BLOCKING, including stale criteria and a test or harness changed between its RED and GREEN. Separately, and whether or not a ledger exists, on any Python repo run `codegraph delta --full --max-tokens 200000` (`codegraph` skill) between the release base and the candidate, adding AC tests by symbol id via `acceptance_ledger.py codegraph-args <id>` when a ledger exists (never by file path), piped into `<codegraph skill dir>/scripts/delta_gate.py`; any gap it reports for a changed symbol, forbidden import pair, or new import cycle is BLOCKING unless the user accepts a written explanation.
8. **Verdict.**

```
Verdict: READY | READY WITH WARNINGS | NOT READY
Blocking: <n>  Warnings: <n>
| # | Severity | Check | Finding | Evidence | Suggested fix |
Not covered: <what this check cannot see, e.g. production-only infrastructure>
```

Always state what was not checked. Then stop and ask the user how to proceed; never deploy from this skill.
