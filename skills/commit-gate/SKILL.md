---
name: commit-gate
description: Pre-commit quality gate that detects the repo's linters, formatters, type checkers, and tests from its config files, runs the fast subset against changed files, and reports pass or fail with a fix list. Use before committing, when asked to run pre-commit checks, type check, lint, validate before commit, check my changes, or when setting up a git hook. Fast and limited to changed files; for a full go/no-go before deploy use release-readiness.
license: Apache-2.0
---

# Commit Gate

Run the quick checks the repo already defines, on what changed, and report. Fast feedback before commit; the full suite belongs to `release-readiness`.

## Workflow

```
- [ ] 1. Detect tools
- [ ] 2. Select changed files
- [ ] 3. Run fast checks
- [ ] 4. Report
```

### 1. Detect tools
Run `python3 scripts/detect_tools.py` from the repo root. It prints JSON listing the checks found in config files and a runnable command for each. Prefer what CI or a pre-commit config runs. If it finds nothing, read README/CLAUDE.md or ask once; do not install tools without asking.

### 2. Changed files
`git diff --name-only --diff-filter=ACM HEAD` plus `git ls-files --others --exclude-standard`. Pass changed files to tools that accept paths. Type checkers usually need whole-project scope; run them project-wide.

### 3. Run fast checks
Order: formatter check, linter, type checker, then unit tests related to changed files (or the fast unit target). Skip slow suites (e2e, integration) and say so. Never auto-fix unless the user asked; if a formatter would change files, report it and offer `--fix`.

Bound each command: `perl -e 'alarm 240; exec @ARGV' <cmd>` (macOS has no `timeout`).

### 3b. Acceptance ledger
If `docs/specs/*/acceptance.json` exists for this branch's spec, run `python3 <atdd skill dir>/scripts/acceptance_ledger.py check <id>` (`scripts/acceptance_ledger.py` in the `atdd` skill). On commit: a non-zero exit (including stale criteria or a test changed between RED and GREEN) is a WARN. On push or release: it BLOCKS. Do not reimplement or edit the ledger.

### 4. Report

```
Commit gate: PASS | FAIL
| Check | Command | Result | Errors |
Failures: file:line, message, suggested fix
Skipped: <slow suites, tools not found>
```

Classify: errors in changed code FAIL the gate. Pre-existing errors in untouched files are listed as WARN with proof (they fail on the base branch too). Also flag: files over 1 MB, binaries, secret-looking strings, conflict markers.

## Hook setup

Only when asked. Prefer the repo's existing hook manager (`pre-commit`, husky, lefthook). Otherwise write `.git/hooks/pre-commit` that runs the detected commands and exits non-zero on failure, and show it to the user first. Hooks must stay under about 30 seconds.
