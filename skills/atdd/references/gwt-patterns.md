# Given/When/Then patterns

## Contents
- Shape
- Observable Then
- Patterns by requirement type
- Gap detection
- Gherkin (optional)
- Test mapping

## Shape
One behavior per criterion. Given = state, When = one action, Then = observable outcome.

```
AC-1: Given a registered user with 3 invoices in March
      When they request the CSV export for March
      Then the response is a CSV with a header row and 3 data rows
```

Use concrete values. "Some invoices" is untestable; "3 invoices" is.

## Observable Then
Acceptable: HTTP status and body, a row in a table, a file's contents, a rendered text, an emitted message, an exit code, stdout. Not acceptable: "works", "is handled", "is fast", "user is happy". Convert vague quality words into thresholds ("p95 under 300 ms with 10k rows") or log them as gaps.

## Patterns by requirement type
| Type | Criteria to derive |
|------|--------------------|
| Happy path | The primary success case with real data |
| Validation | One criterion per rule: invalid input, expected error message or code |
| Boundary | Empty, one, max, max+1; zero; null/missing |
| Permission | Allowed role succeeds; disallowed role is rejected and nothing changes |
| State change | Before state, action, after state, and what did not change |
| Idempotency | Same request twice yields one effect |
| Bug fix | Reproduction steps as Given/When; Then is the correct behavior; must be RED before the fix |
| Non-functional | Threshold, load, and measurement method, or defer as a question |

## Gap detection
Raise a question when:
- the Then has no observable form ("the system should handle it")
- two sources disagree (ticket vs. comment vs. code)
- a value is unspecified (limit, format, currency, timezone, sort order)
- an actor or role is unnamed
- the error behavior is missing
Question format: `Q1 (AC-3): What should the export return when there are zero invoices: empty file with header, or 204?`

## Gherkin (optional)
Use only if the repo already has `.feature` files.
```gherkin
Scenario: Export March invoices
  Given a user with 3 invoices in March
  When they request the CSV export for March
  Then the CSV has a header and 3 rows
```
Scenario Outline with Examples tables for multiple data rows of one rule. Keep steps declarative (what, not UI clicks).

## Test mapping
Name tests `test_ac<n>_<behavior>` (or `it('AC-1: ...')`). Arrange = Given, act = When, assert = Then. One When per test; several asserts on the same outcome are fine.
