# Evals

## Routing (`route_eval.py`)

Checks which skill `claude -p` invokes for realistic prompts when all skills are installed together. Run from a project whose `.claude/skills/` holds the skills, ideally a real repo the prompts make sense in:

```sh
cp -R ../skills/. <repo>/.claude/skills/
cd <repo> && python3.13 /path/to/evals/route_eval.py /path/to/evals/routing-eval.json --model <model> --workers 6
```

A skill counts if it is invoked at any point before the session ends. An environment preamble (`date`) is ignored.

Results on 2026-10-31 (claude-opus-5-5, 2 runs): 16 of 24 skill prompts routed to the intended skill; all 5 no-skill prompts stayed clean apart from a personal skill outside this repo. The 8 misses were tasks a toy fixture repo made trivial (8-line files, one caller), where the model answered directly. Rerun on a real repo before tuning descriptions further; for any skill that still misses, use skill-creator's description optimizer (`scripts.run_loop`).

## Behavior (`workspace/iteration-1/`)

With-skill vs no-skill runs, graded by `grade_iter1.py` (two regex false negatives corrected by hand, noted in `grading.json`). `review-iteration-1.html` is the viewer.

| Eval | With skill | Without | What the skill added |
|---|---|---|---|
| atdd: total() ignores negatives | 6/6 | 4/6 | executed, persisted red-before-green evidence; stayed in scope (baseline made an unasked branch) |
| jira-ticket-enrich: ticket with prompt injection | 6/6 | 5/6 | machine-readable enrichment with idempotency marker; explicit priority decision path. Both resisted the injection. |

## Iteration 2 (2026-10-31): requirement welds

`grade_iter2.py`; viewer `review-iteration-2.html`. With skill 93% vs without 59% (+35 points).

| Eval | With | Without | Finding |
|---|---|---|---|
| atdd-negatives (rerun on new ledger) | 3/3 | - | no regression |
| atdd-conflict | 2/3 | 2/3 | both silently deleted a contradicting existing test |
| requirement-change | 3/3 | 1/3 | baseline left the ledger PASS on the old requirement (phantom green) |
| resolve-no-ledger | 3/3 | 2/3 | baseline planned a resolve with no regression evidence |
| rca-regression | 3/3 | 2/3 | only the skill left a RED regression AC for the fix |

Fix for atdd-conflict: a conflict rule in `atdd` plus `delta_gate.py` failing on removed/changed pre-existing tests (`--allow-test-change` after user approval; mutation-tested). Iteration 3 rerun: the agent kept the old test, recorded the new test RED, and reported the conflict as blocked.

## Routing on a real repo (codegraph-slicer clone)

5/10. Hits: codegraph (branch vs main), pr-describe, jira-ticket-enrich (pasted ticket), both no-skill prompts. Misses (answered directly with Bash): spec-research, codegraph (callers), zoom-out, root-cause-trace; spec-plan timed out. Next: skill-creator `scripts.run_loop` description optimization on those five against this repo.

Description retune (Sonnet, 2 wordings including a "MUST invoke" variant): 0/5 both times, while a control prompt naming the skill routed 1/1. Sonnet answers these quick-looking questions directly regardless of wording, so the pre-retune descriptions were restored. In practice, name the skill for those five ("use spec-research to...", "/zoom-out") or let `fix-and-ship` call them.

## All skills (2026-10-31, `allskills-iteration-1`, Sonnet, 3 checks each)

`grade_allskills.py`; viewer `review-allskills.html`. With skill 97.6% vs without 81.1% (+17 points). codegraph was run separately (`codegraph-iteration-1`): same verdict both ways, the skill backs it with the delta gate's exit code.

| Skill | With | Without | What the skill added |
|---|---|---|---|
| spec-plan | 3/3 | 1/3 | phased plan with rollback and ACs per phase; baseline wrote an unphased sketch |
| spec-implement | 3/3 | 2/3 | executed RED-before-GREEN ledger evidence |
| root-cause-trace | 3/3 | 2/3 | regression criterion RED in the ledger |
| fix-and-ship | 3/3 | 2/3 | stopped for approval; both found CG-7 already fixed |
| jira-code-localize | 3/3 | 2/3 | hypothesis labeled unconfirmed, measured timings |
| codebase-health | 3/3 | 2/3 | 1-5 scorecard per dimension |
| zoom-out | 3/3 | 2/3 | evidence kept separate from judgment |
| commit-gate, pr-describe, spec-research, spec-validate, jira-productivity, jira-value-score | 3/3 | 3/3 | ties: Sonnet does these well unaided; the skills add consistency (scripts, defaults, formats) |
| release-readiness | 3/3 (was 2/3) | 3/3 | first run skipped the codegraph gate without a ledger and said GO with warnings; after the fix the rerun ran `delta_gate.py` (exit 1) and returned NOT READY with the gap as blocking |

Fixture note: the slicer repo needs `PYTHONPATH=.` for pytest; the first spec-implement run correctly stopped on the broken test command and was rerun.
