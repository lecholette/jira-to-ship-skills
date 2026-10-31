# Gate Decision Tree

## Contents
- Principle
- Failure by phase
- Rollback
- Deploy-target notes

## Principle

On any failure: stop, show the failing command and the last lines of output, say what you think the cause is, and propose a next step. Ask before taking any step that changes shared state (push, merge, deploy, rollback). Two failed attempts at the same fix means the approach is wrong: re-read the research and plan, or ask the user.

## Failure by phase

| Phase | Failure | Action |
|---|---|---|
| Config | Deploy target unknown | Ask. Do not continue |
| Research | Task already done, or cannot reproduce | Report and stop; ask whether to close or reframe |
| Research | Findings contradict the ticket | Show the contradiction; ask which source to trust |
| Plan | Plan touches areas the user did not mention | Flag scope growth at the checkpoint |
| Approval | `revise` | Return to Plan with the edits as constraints |
| Approval | `abort` | Leave the branch, summarize, stop |
| Implement | New test passes before the fix | The test does not capture the bug; rewrite it |
| Implement | Unrelated tests break | Find the coupling; fix the cause, never delete the test |
| Ship gate | `acceptance_ledger.py verify <id>` fails (stale AC, digest mismatch, RED/GREEN test changed) | Stop; fix, `revise` the criterion if the requirement changed, record a new RED then GREEN; do not advance |
| Review | Critical security finding | Fix, re-run the check, re-review; do not advance |
| Pre-deploy | Test or type failure | Investigate. If caused by your change, fix; if pre-existing, show proof (same failure on the deploy branch) and ask |
| Pre-deploy | CI red but local green | Treat CI as truth; diff the environments |
| Merge | Conflicts | Rebase onto the deploy branch, rerun all gates, then ask again |
| Merge | Branch protection or required review blocks | Report; wait for the reviewer |
| Deploy | Pipeline fails | Stop; read logs; do not retrigger blindly |
| Smoke | Health check fails or new errors appear | Present rollback options; ask |

## Rollback

Always ask first. Prefer the smallest reversible action:

1. **Provider rollback**: redeploy the last known-good release using the project's documented command. Fastest; leaves the bad commit on the branch.
2. **Revert commit**: `git revert <sha>` on a branch, PR it, merge on approval, deploy. Keeps history; takes a full cycle.
3. **Feature flag off**: when the change is flagged, disable it. No deploy needed.

After rollback, repeat the smoke check and report. Open a follow-up issue with the failure evidence.

## Deploy-target notes

Resolve per project in Phase 0 and record:

- Does merging deploy, or is the release a separate manual step? If separate, merging ships nothing; do not report "deployed" after merge.
- Which components deploy (web, workers, jobs)? Each needs its own smoke check.
- Where is the running version visible (header, health endpoint, release tag)? Use it to confirm the new build is serving.
- Is there a staging environment? If so, deploy there first when the project defines one.
