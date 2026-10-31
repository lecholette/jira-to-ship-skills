# Linked work (PRs and commits)

Goal: tell the reader whether work already exists for this ticket, and who did it.

## Find

Use the `gh` CLI (read-only). Repo list comes from the ticket's Development panel, links, or the user.

```bash
gh search prs "ABC-123" --repo org/repo --json number,title,state,mergedAt,author,url --limit 10
gh search commits "ABC-123" --repo org/repo --json sha,commit,author --limit 10
gh pr view <n> --repo org/repo --json files,mergedAt,state,reviews
```

Also match PR titles and branch names containing the key, and keys in commit messages. Set explicit time limits on network calls.

## Interpret

- **Open PR:** fix in flight; report author and review state. Suggest linking, not duplicating effort.
- **Merged PR:** compare merge date to the ticket's first-seen date and the changed files to the symptom. If it plausibly fixes it, flag "possibly already fixed in <release>" and ask the user to verify. If the bug is reported after the merge, flag a possible regression.
- **Reverted PR:** note the revert and its reason.
- **None found:** say so; do not infer absence of work.

## Report

One line per item: type, ref, state, date, one-line relevance. Also use the authors of linked PRs as a routing signal. Skip review-time and throughput metrics; those belong to a separate productivity analysis.
