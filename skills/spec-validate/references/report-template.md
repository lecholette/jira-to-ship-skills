# Validation report template

```markdown
# Validation Report: <plan name>

**Date**: <date>  **Plan**: <path>  **Range**: <base..head>
**Verdict**: PASS | PASS WITH NOTES | FAIL

## Phase Status
| Phase | Status | Evidence |
|-------|--------|----------|
| 1 <name> | Done / Partial / Missing | <files, commits> |

## Automated Verification
| Command | Result | Notes |
|---------|--------|-------|
| `<cmd>` | PASS / FAIL / NOT RUN | <key output line> |

## Acceptance Traceability
<output of acceptance_ledger.py render, plus check result>

## Test Gaps
<changed symbols without coverage, from codegraph delta or manual search>

## Matches Plan
- <item> (`path:line`)

## Deviations
| Item | Class (improvement / neutral / risk) | Evidence | Decision needed? |
|------|------|------|------|

## Gaps and Risks
- <missing test, unhandled error path, out-of-scope change>

## Manual Verification Remaining
- [ ] <concrete step and expected result>

## Recommendations
- <ordered, actionable>
```
