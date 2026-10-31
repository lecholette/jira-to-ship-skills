---
name: pr-describe
description: Writes or updates a pull request description from the repository's PR template, based on the full diff and commit history. Runs the template's verification commands and ticks checklist items honestly. Use when asked to describe a PR, write a PR description, fill in the PR template, prepare a PR for review, or after implementation is complete. Use it whenever a PR body or PR template needs writing, rather than drafting from the commit list alone.
license: Apache-2.0
---

# PR Describe

Produce an accurate, scannable PR description from the real diff. Updating the PR on GitHub happens only after the user sees the draft.

## Steps

```
- [ ] 1. Find the template
- [ ] 2. Identify the PR
- [ ] 3. Gather the diff and history
- [ ] 4. Run verification commands
- [ ] 5. Draft, show, get approval
- [ ] 6. Update the PR
```

### 1. Find the template
Look for `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/pull_request_template.md`, or a template referenced in CONTRIBUTING. If none exists, use: Summary, Why, Changes, How to verify, Risks and rollout, Linked issues.

### 2. Identify the PR
`gh pr view --json url,number,title,state,baseRefName 2>/dev/null`. If there is none, or you are on the default branch, run `gh pr list --limit 10 --json number,title,headRefName,author` and ask which PR. If `gh` reports no default repository, ask the user to run `gh repo set-default`.

### 3. Gather
`gh pr diff <n>`, `gh pr view <n> --json commits,body`. Read referenced files that the diff does not show when needed to understand a change. If the PR already has a description, keep any human-written context and note what changed since.

Separate user-visible changes from internal ones. Call out breaking changes, migrations, config or flag changes, and new dependencies prominently.

### 4. Verify
For each runnable item in "How to verify" (tests, lint, build), run it. Pass: `- [x]`. Fail: leave `- [ ]` and note the failure. Manual steps (UI, external services): leave unchecked and list them. Never tick a box you did not verify.

### 5. Draft
If `docs/specs/<id>/acceptance.json` exists, run `python3 <atdd skill dir>/scripts/acceptance_ledger.py render <id>` (`atdd` skill) and include the traceability matrix in the description. Call out any stale, tampered (test changed between RED and GREEN), or legacy evidence rows. If the user approved a hotfix exception to ATDD gates, record it here. Fill every template section. Explain why, then what. Be specific: name modules and behaviors, not "various fixes". Link tickets by key. Keep it short enough to scan. Show the draft.

### 6. Update
After approval: write the body to a temp file and run `gh pr edit <n> --body-file <file>`. Confirm the update. Remind the user of any unchecked verification items before merge.
