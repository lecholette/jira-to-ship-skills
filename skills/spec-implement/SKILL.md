---
name: spec-implement
description: Executes an approved implementation plan one phase at a time, test-first (red, green, refactor), running the plan's success-criteria commands as a gate before each phase is checked off, and stopping to ask when the code diverges from the plan. Use when asked to implement, execute, build, or continue a plan produced by spec-plan, or when given a plan file path and told to start or resume work. Acceptance criteria and the red/green ledger come from the atdd skill. Use it whenever told to start, continue, or resume an approved plan or a phase of one.
license: Apache-2.0
---

# Spec Implement

Carry out an approved plan faithfully. The plan states intent; your job is to deliver that intent, verify it, and surface divergence early instead of improvising silently.

## Operating rules

- **Only implement an approved plan.** If the plan header says `draft`, stop and ask for approval or run `spec-plan` review.
- **Tests first, per phase.** A phase with no new or changed tests is incomplete unless the plan states why none apply.
- **Never record status by hand.** Red and green come from the ledger's `run`, which executes the command.
- **Gate before checkbox.** Tick a success criterion only after its command ran and passed in this session.
- **Stop on divergence.** If the plan cannot be followed as written, report and ask. Do not quietly redesign.
- **No scope creep.** Respect the plan's Out of Scope list. Note nice-to-haves at the end instead of doing them.
- **Never skip or weaken a failing test** to make a gate pass. Investigate the cause.
- **Do not commit or push** unless the user asks. Work on the branch the user named, or ask which branch before the first edit if on the default branch.

## Inputs

- Plan path (required; ask if missing)
- Ledger: `docs/specs/<id>/acceptance.json` (from `atdd`/`spec-plan`); `L=<path to atdd>/scripts/acceptance_ledger.py`
- Phase to run: one phase (default: next unchecked), a range, or all with a pause between phases
- Branch convention and commit policy: read from CLAUDE.md/AGENTS.md or CONTRIBUTING; ask once if unclear

## Workflow

```
- [ ] 1. Read the plan, its ticket, and every file it names, in full
- [ ] 2. Find existing progress (checked boxes) and the first unfinished phase
- [ ] 3. Establish a green baseline: run the plan's test command now
- [ ] 4. Write the phase's acceptance test(s); link them in the ledger
- [ ] 5. `run` each AC: observe RED
- [ ] 6. Implement the minimum to pass
- [ ] 7. `run` each AC: observe GREEN
- [ ] 8. Refactor with tests as the safety net
- [ ] 9. `check --phase N` and the plan's other gate commands must pass
- [ ] 10. Tick boxes in the plan file; report; pause or continue
```

**3. Baseline.** If tests already fail before you touch anything, report it and ask whether to proceed. Otherwise you cannot tell your breakage from existing breakage.

**4-5. Red.** Write the acceptance test for each AC the phase lists, then `python $L link <id> AC-n --test <path::name>` and `python $L run <id> AC-n --cmd "<single-test command>"`. Write the other tests the phase describes too. **If an acceptance test passes immediately, stop**: the test is not testing the change (or the behavior exists). Report it and fix the test. Confirm failures are for the right reason (missing behavior, not a typo or import error). Use the repo's existing test framework and file layout; copy the nearest existing test as the pattern. **Never edit a test after its RED run to make it pass.** If the test was wrong, fix it and record a new RED. If the requirement changed, `python $L revise <id> AC-n "<new text>"` and tell the user. Run `python $L check <id> --phase N` before checking the phase off.

**6-7. Green.** Smallest change that passes. Follow patterns the plan cites. Then `run` each AC again to record GREEN. If a cycle takes more than 3 failed attempts on the same error, stop, re-read the relevant code, and state a new hypothesis before trying again.

**9. Gate.** `python $L check <id> --phase N` must print `GATE: PASS` before the next phase starts. Then run every command under the phase's Automated criteria: tests, lint, type-check, build. Also run the full test suite once per phase to catch regressions elsewhere. Manual criteria are listed for the user, not ticked by you.

**10. Report.** Edit the plan file: tick passed automated boxes, set `status: in-progress` (or `complete` after the last phase). Add a short note under the phase for deviations. Then follow the pause policy.

## Divergence protocol

When reality does not match the plan, stop and send:

```
Issue in Phase N:
Expected: <what the plan says>
Found: <what the code shows, with path:line>
Why it matters: <consequence>
Options: <1-3 ways forward, your recommendation>
```

Trivial differences (renamed file, shifted line numbers) need only a note in the phase report.

## Resuming

If the plan already has ticks, trust them but spot-check the last completed phase by re-running its gate. Continue from the first unticked item.

## Output to the user

Per phase: what changed (files), tests added, gate results (command and pass/fail), deviations, and what needs manual verification. After the final phase, suggest `spec-validate`.

## Gotchas

- Do not batch several phases before running tests. Failures compound.
- Line numbers in the plan drift as you edit; search by symbol.
- If the plan's command does not exist or fails for environmental reasons, say so rather than substituting another and calling it passed.
- With acceptance tests from `atdd` in play, they are the outer loop: they must be green at the end of the final phase.
