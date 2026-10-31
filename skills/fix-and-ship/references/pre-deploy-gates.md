# Pre-Deploy Gates

## Contents
- Resolving the suite
- Always-on gates
- Conditional gates
- Hard-gate semantics
- Examples by stack

## Resolving the suite

Find `PREDEPLOY_CMD` in this order and stop at the first hit:

1. A documented pre-deploy or release command in README, CLAUDE.md, AGENTS.md, or docs/
2. The test and lint jobs in CI config (`.github/workflows`, `.gitlab-ci.yml`, etc.). Mirror what CI runs so local results predict CI.
3. Scripts: `make check`/`make test`, `npm test`, `pytest`, `go test ./...`, `cargo test`
4. Ask the user once and record the answer in your ship-state note.

Never copy another project's command list. If nothing is found, ask.

## Always-on gates

| Gate | Pass condition |
|---|---|
| Working tree | Only intended files changed; no stray untracked files that the build needs |
| Type check / lint | Zero errors (warnings allowed if CI allows them) |
| Unit and integration tests | All pass; no newly skipped tests |
| Regression test | The new test fails without the fix and passes with it |
| Build | Production build or package step succeeds |
| CI on the PR | Green on the exact head commit |
| Secrets scan | No credentials in the diff |

## Conditional gates

Run when the diff touches the area. Detect by path, not by guessing.

| Change touches | Add |
|---|---|
| Database schema or migrations | Migration up and down on a scratch DB; check for locks on large tables; confirm app works with old and new schema during rollout |
| Payments, auth, permissions | Security review of the diff; negative tests (unauthorized access denied); explicit user sign-off |
| Public API or schema | Contract tests; check backward compatibility |
| Dependencies or lockfile | Audit command (`npm audit`, `pip-audit`); confirm lockfile committed |
| Frontend assets or templates | Build step plus a render check of changed pages |
| Config or feature flags | Compare values against production; list flags changed |
| Infrastructure or deploy config | Dry-run or plan output reviewed by the user |

## Hard-gate semantics

If `docs/specs/*/acceptance.json` exists, `acceptance_ledger.py verify <id>` (`atdd` skill) at the release candidate commit is a blocking gate. `check` alone reads old evidence. Stale criteria and a test or harness changed between RED and GREEN block.

- A gate has two outcomes: pass or stop. There is no "pass with known failure".
- A flaky test is a failure until proven flaky by a rerun on a clean tree and the user agrees to proceed.
- Do not edit a test, threshold, or CI config to make a gate pass unless the test itself is the bug and the user approves.
- Record every gate result (command, exit code, last lines) in the final report.

## Examples by stack

These are shapes, not defaults. Use what the repo defines.

```bash
# Node
npx tsc --noEmit && npm run lint && npm test && npm run build
# Python
pyright && ruff check . && pytest -q --tb=short
# Go
go vet ./... && go test ./...
# Make-based
make check test
```
