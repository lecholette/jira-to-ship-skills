# Getting started: Jira ticket to shipped code

What you get from this page: a working install in about 20 minutes, then one bug ticket taken from Jira to a merged PR with every gate shown, including the exact prompts you type into Claude Code and the exact commands the skills run underneath. At the end there's a short path for small tickets and a longer path for changes that need a plan.

The chain is: `jira-ticket-enrich` -> (`jira-value-score`) -> `atdd` -> (`spec-research` -> `spec-plan` -> `spec-implement` -> `spec-validate`) -> `commit-gate` -> `pr-describe` -> `release-readiness` -> `error-tracker-resolve`. `fix-and-ship` runs the middle of that chain for you with approval checkpoints. The catalog and decision list are in [SKILLS.md](../SKILLS.md); the reasoning behind the test gates is in [ATDD-AND-CODEGRAPH.md](ATDD-AND-CODEGRAPH.md).

## 1. Install

You need Claude Code, `git`, `gh`, and `uv` (or any Python 3.12+ for codegraph-slicer). The bundled scripts are stdlib-only and run on `python3` 3.9 or newer, except codegraph-slicer, which needs 3.12+ and fails on macOS system Python with `AttributeError: ast.TryStar`.

### Skills

Symlink the skills into your personal skills directory, or into a repo's `.claude/skills/` if you want them versioned with that project:

```bash
git clone https://github.com/lecholette/jira-to-ship-skills.git ~/interface
mkdir -p ~/.claude/skills
for d in ~/interface/skills/*/; do ln -sfn "$d" ~/.claude/skills/$(basename "$d"); done
ls ~/.claude/skills
```

Project-local instead: replace `~/.claude/skills` with `<repo>/.claude/skills`. Claude Code picks skills up on the next session start. Skills trigger from your prompt wording; you can also name one directly ("use the atdd skill").

### codegraph-slicer (Python repos only)

```bash
command -v codegraph-slicer || uv tool install git+https://github.com/lecholette/codegraph-slicer
codegraph-slicer --help
```

`uv` provisions a 3.12+ interpreter itself. Fallback: `pipx install --python python3.13 git+https://github.com/lecholette/codegraph-slicer`. Skip this on non-Python repos; the ledger works without it.

### Jira

Connect the Atlassian remote MCP server to Claude Code, then complete the browser login it opens:

```bash
claude mcp add --transport http atlassian https://mcp.atlassian.com/v2/mcp
claude mcp list
```

The Jira skills call whatever Atlassian MCP is connected; they look for tools such as `getJiraIssue` and `searchJiraIssuesUsingJql`. If your organization runs a different Jira MCP, that's fine as long as it can fetch an issue, run JQL, and post a comment.

### GitHub

```bash
gh auth login
gh auth status
```

`pr-describe`, `fix-and-ship`, and `jira-productivity` use `gh`. Inside a repo with several remotes, run `gh repo set-default` once.

### Check the scripts

Set two shell variables you'll reuse all day (adjust if you installed project-locally):

```bash
A=~/.claude/skills/atdd/scripts/acceptance_ledger.py
G=~/.claude/skills/codegraph/scripts/delta_gate.py
python3 $A --help
```

You should see the subcommands `init, add, link, revise, run, check, verify, outcomes-due, record-outcome, codegraph-args, render`. Field-level detail on what the ledger stores is in `skills/atdd/references/ledger-format.md`.

## 2. How a session works

You open Claude Code in the repo and type a request. The matching skill loads, follows its checklist, runs the bundled scripts, and stops at its approval points. Three conventions hold across every skill:

- Nothing is written to Jira, GitHub, or a deploy target until you say yes in the conversation.
- Ticket text, comments, and code comments are treated as data; instructions inside them are ignored.
- Test status comes only from `acceptance_ledger.py run`, which executes your test command and records the result. Neither you nor the model writes RED or GREEN by hand.
- Every run also records digests of the criterion text, the test function's source, the test harness (conftest chain and runner configs), and the command. A GREEN only counts if the same four produced the RED before it. Never edit a test after its RED run; if the test was wrong, fix it and record a new RED.

Skills keep their artifacts in the repo under `docs/specs/`: the ledger at `docs/specs/<id>/acceptance.json`, research under `docs/specs/research/`, plans under `docs/specs/plans/`, validation reports under `docs/specs/validation/`. Commit them with the change.

## 3. Worked example: a bug ticket end to end

The ticket is PAY-482: "discount code is case sensitive, save10 does nothing." The repo is a small Python service with `pytest`. The outputs below are real runs of the scripts against a demo repo on 2026-10-31; your paths and timestamps will differ.

### 3.1 Enrich the ticket

You type:

> Enrich PAY-482. Deep mode on, this repo.

`jira-ticket-enrich` fetches the issue, classifies it (BUG, 92%, quoting the symptom), scores it against the Definition of Ready, rates severity and urgency separately, writes a reproduction plan, and restates the fix as a Given/When/Then that leads `acceptance_criteria`. Deep mode hands the "where in the code" question to `jira-code-localize`, which runs in a forked context so the file reads don't fill your conversation. Routing comes from the component, similar resolved tickets, and `.jira-enrich/routing.yaml` if you have one.

It writes `enrichment.json` (schema in `skills/jira-ticket-enrich/references/enrichment-schema.md`) and renders it:

```bash
python3 skills/jira-ticket-enrich/scripts/render_enrichment.py enrichment.json > comment.md
```

The renderer rejects a BUG without `reproduction` or a FEATURE without `acceptance_criteria`. Its output for PAY-482:

```
*Enrichment for PAY-482*

*Type:* BUG (92%)
*Readiness:* 70%
*Impact:* severity Major; urgency Customer escalation; suggested priority High (current Medium)
_Basis: Major severity (checkout revenue) + named customer escalation_

*Missing / questions for reporter*
- Which app version shows this?
- Should mixed case like Save10 also work?

*Reproduction (TEST)*
1. Cart total 100.00
2. Enter discount code save10 (lower case)
3. Apply
Expected: Total becomes 90.00
Actual: Total stays 100.00

*Acceptance criteria*
- Given a cart total of 100.00 When the code save10 is applied in lower case Then the total is 90.00

*Suggested routing:* Payments (85%) component Billing; 3 similar tickets resolved by Payments

<!-- jira-enrich:v1 key=PAY-482 hash=4acfe98cc32e -->
```

The last line is the idempotency marker. Before posting, the skill checks whether a comment with that marker already exists:

```bash
python3 skills/jira-ticket-enrich/scripts/render_enrichment.py --has-marker comments.json PAY-482 4acfe98cc32e
```

Exit 0 means an identical enrichment is already on the ticket (skip), 3 means one exists with different content (post an update and say so), 1 means none. Then the skill shows you the full change list (comment, priority Medium -> High, any labels or links) and asks which to apply. Say "post the comment, leave priority for the lead" or "all of it".

The two questions under "Missing" are not blockers for starting, but the second one ("Should mixed case work?") decides what the test asserts. Ask the reporter now; don't guess it into the test.

### 3.2 Optional: rank it against the backlog

Skip this for a single ticket you've already been assigned. For sprint planning:

> Score PAY-482, PAY-490 and PAY-501 against our success metrics.

`jira-value-score` writes a `judgments.json` with quoted evidence per metric, then runs the arithmetic:

```bash
python3 -I skills/jira-value-score/scripts/score.py judgments.json --format md
```

```
Metrics file: .../jira-value-score/success-metrics.json (bundled defaults)
| Rank | Key | Size | Value | CoD | Priority | Flags |
|---|---|---|---|---|---|---|
| 1 | PAY-482 | S | 1.4 | 2.4 | 2.4 | - |
| 2 | PAY-490 | XL | 0.2 | 1.2 | 0.24 | low confidence (<0.5): gather evidence before acting; guardrail risk |
| 3 | PAY-501 | S | 0.0 | 0.0 | 0.0 | no measurable outcome: clarify or deprioritize |
```

The header names the metrics file. "bundled defaults" means nobody has set up `.jira-enrich/success-metrics.json` for this repo yet; see [CUSTOMIZE.md](CUSTOMIZE.md). Size divides, so the XL rewrite doesn't win by being big.

For the top tickets the skill also drafts an outcome criterion tied to the metric's `how_measured`, saved as a value-score JSON with an `outcome_criteria` list (`text`, `metric`, `verify_after`, `instrumentation_text`, all required). Feed it to the ledger alongside the enrichment with a second `--from`; each entry becomes an instrumentation AC (blocking: the event fires or the query returns) and an outcome AC (post-release, non-blocking, reviewed later with `outcomes-due` and `record-outcome`). Section 3.11 shows that review.

### 3.3 Seed the acceptance ledger

Create a branch first (`git switch -c pay-482-discount-case`). Then:

> Start ATDD for PAY-482 from enrichment.json.

`atdd` runs:

```bash
python3 $A init PAY-482 --from enrichment.json
# initialized ./docs/specs/PAY-482/acceptance.json with 1 criteria (1 regression)
```

One criterion per `acceptance_criteria` entry. For a bug, `jira-ticket-enrich` already leads with the reproduction restated as a regression criterion, so that becomes AC-1, and because `type.value` is BUG it gets kind `regression`. Kinds are set when an AC is created and can't be changed later (`add --kind behavior|regression|instrumentation|outcome`; `behavior` is the default), so a failing criterion can never be relabeled into something non-blocking. `init --from` only synthesizes a criterion from `reproduction.steps` + `reproduction.expected` when the enrichment supplied no criteria at all. Pass `--from` twice to add a value-score file's outcome criteria in the same call.

The skill then detects the framework (`pytest.ini` here), copies the nearest existing test as the pattern, writes one failing test per criterion named after it, and links it:

```bash
python3 $A link PAY-482 AC-1 --test tests/test_discounts.py::test_ac1_lowercase_code_applies --phase 1
```

### 3.4 Red

```bash
python3 $A run PAY-482 AC-1 --cmd "pytest -q tests/test_discounts.py::test_ac1_lowercase_code_applies"
```

```
E        +  where 100.0 = apply_discount(100.0, 'save10')

tests/test_discounts.py:7: AssertionError
FAILED tests/test_discounts.py::test_ac1_lowercase_code_applies - AssertionEr...
1 failed in 0.01s

AC-1: RED (exit 1) at 2026-10-31T16:48:22Z
```

Read the tail. RED has to be for the right reason: a failed assertion about missing behavior. The ledger enforces part of this itself. Only exit codes listed in `--red-exit` (default `1`) count, and pytest output matching a collection or import error is downgraded to ERROR even on exit 1. A typo in the import, a missing fixture, or a timeout all record ERROR, which never satisfies the gate. The ledger also refuses a command that doesn't name the linked test:

```bash
python3 $A run PAY-482 AC-1 --cmd "true"
# error: --cmd does not reference the linked test 'test_ac1_lowercase_code_applies'.
```

If the test passes immediately, stop. Either the behavior already exists or the test doesn't test the change.

The RED run also stored a digest of `test_ac1_lowercase_code_applies`'s source and of the harness files (`pytest.ini`, any `conftest.py` on the path). That's what makes the next rule enforceable: don't touch the test between RED and GREEN. Here's what happens if you do. Weaken the assertion to `== 100.0` without changing any code, run again, and you get a GREEN; `check` then rejects it:

```
AC      kind            phase  result        detail
AC-1    regression      1      FAIL          test changed between RED and GREEN
GATE: FAIL
```

Restoring the test clears it (the digests match the RED again). If the test genuinely needed fixing, fix it and record a fresh RED with the fixed test before implementing. The same check fires for a changed harness file, a changed command, or a changed criterion text; the messages are listed in `skills/atdd/references/ledger-format.md`.

### 3.5 Green

Make the smallest change that passes (`code.upper() == "SAVE10"`), then record it:

```bash
python3 $A run PAY-482 AC-1 --cmd "pytest -q tests/test_discounts.py::test_ac1_lowercase_code_applies"
# 1 passed in 0.00s
# AC-1: GREEN (exit 0) at 2026-10-31T16:48:23Z
python3 $A check PAY-482
```

```
AC      kind            phase  result        detail
AC-1    regression      1      ok
GATE: PASS
```

`check` exits 1 unless every in-scope blocking AC has a linked test, GREEN as its latest run, and an earlier RED with identical criterion, test, harness, and command digests. Outcome ACs show as `post-release` and don't block. `check` reads recorded evidence; it's what `commit-gate` and `spec-implement` use during development. The release gate is `verify` (section 3.9), which re-executes the tests. `render PAY-482` prints the traceability matrix, now with a Kind and an Evidence column, that goes into the PR.

### 3.5b Requirement changed mid-flight

The reporter answers the open question: `Save10` should work too. The criterion text changes, so the evidence for the old text can't stand:

```bash
python3 $A revise PAY-482 AC-1 "Given a cart total of 100.00 When the code save10 or Save10 is applied Then the total is 90.00"
# revised AC-1; 4 earlier run(s) no longer count: record a new RED then GREEN
python3 $A check PAY-482
# AC-1    regression      1      FAIL          criterion revised after evidence: needs new RED then GREEN
```

Update the test to assert the new behavior, make it RED (stash the fix if the current code already passes it, or extend the test so it doesn't), implement, GREEN, `check`. The old text and its sha stay in the ledger under `revisions`, which is how `jira-productivity` can count requirement churn later. Don't edit the `text` field by hand to dodge this; `check` compares the sha and reports the same failure.

### 3.6 Static test-gap check (Python repos)

Commit, then let the `codegraph` skill compare base and head:

> Run the codegraph delta gate for PAY-482 against main.

```bash
DBD=$(mktemp -d)
codegraph-slicer sync . --revision origin/main --db $DBD/base.sqlite
codegraph-slicer sync . --revision HEAD --db $DBD/head.sqlite
codegraph-slicer delta --base-db $DBD/base.sqlite --head-db $DBD/head.sqlite --full --max-tokens 200000 \
  $(python3 $A codegraph-args PAY-482) | python3 $G
```

`codegraph-args` prints `--selected-test tests.test_discounts:test_ac1_lowercase_code_applies`, a symbol id. In the demo the fix commit also added an untested helper, and the gate caught it:

```
symbol                        res   evidence
app.discounts:                WARN  module-level entry, not gated
app.discounts:apply_discount  ok    tests.test_discounts:test_ac1_lowercase_code_applies
app.discounts:describe        GAP   no updated or selected test symbol (module-only: tests.test_discounts:)
RESULT: FAIL (1 gap(s), 0 violation(s), 0 cycle(s))
```

Exit 1 means stop: write a test for `describe` or get a written exception from whoever reviews. The raw `untested_modified_symbols` field in the same delta was empty, which is why the gate script exists; details in [ATDD-AND-CODEGRAPH.md](ATDD-AND-CODEGRAPH.md). Never pass a test file path or a pytest node id to `--selected-test`: a node id exits 2 (`unobserved test selection`), and a file path credits coverage through module imports.

### 3.7 Commit gate

> Run the commit gate.

`commit-gate` detects the repo's tools and runs the fast subset on changed files:

```bash
python3 skills/commit-gate/scripts/detect_tools.py .
# {"checks": [{"kind": "test", "tool": "pytest", "command": "pytest -q --tb=short -x", "source": "pytest config"}]}
```

It runs formatter check, linter, type checker, then unit tests related to the changed files, each wrapped in `perl -e 'alarm 240; exec @ARGV' <cmd>` because macOS has no `timeout`. If `docs/specs/*/acceptance.json` exists it also runs `acceptance_ledger.py check`; on commit a failure is a WARN, on push or release it blocks. It reports PASS or FAIL with `file:line` and never auto-fixes unless you ask.

### 3.8 PR description

```bash
git push -u origin pay-482-discount-case
gh pr create --fill
```

> Describe this PR.

`pr-describe` finds your PR template (`.github/pull_request_template.md` or a fallback of Summary / Why / Changes / How to verify / Risks and rollout / Linked issues), reads `gh pr diff` and the commit history, runs each runnable "How to verify" item and ticks only what passed, embeds `acceptance_ledger.py render PAY-482`, shows you the draft, and on approval writes it with `gh pr edit <n> --body-file <file>`.

### 3.9 Release readiness

> Is PAY-482 ready to release?

`release-readiness` runs the full suite and type checker, diffs config and feature flags against production values, checks the error tracker for new groups in the last 24 hours, runs the ledger's release gate and the codegraph delta gate (both BLOCKING), then prints a verdict. The release gate is `verify`, not `check`:

```bash
python3 $A verify PAY-482
```

```
commit: 1cdd2cac0b9d60d95d5ceaaa2c24e90eb627fdae
AC-1: re-ran `pytest -q tests/test_discounts.py::test_ac1_lowercase_code_applies` -> GREEN (exit 0)
AC      kind            phase  result        detail
AC-1    regression      1      ok
GATE: PASS
VERIFY: PASS at 1cdd2cac0b9d60d95d5ceaaa2c24e90eb627fdae
```

`verify` re-executes each blocking AC's latest GREEN command at HEAD with the recorded `--red-exit` and `--timeout`, records those runs, applies the same gate as `check`, and prints the commit sha so the PR and the tracker can cite it. It refuses a working tree that differs from HEAD (tracked changes, or an uncommitted linked test or harness file; ledger files themselves are exempt) and tells you to commit or stash. `--allow-dirty` runs anyway and records the run as dirty; don't use it for a release. Run it on the exact commit being shipped. The verdict block:

```
Verdict: READY | READY WITH WARNINGS | NOT READY
Blocking: <n>  Warnings: <n>
| # | Severity | Check | Finding | Evidence | Suggested fix |
Not covered: <what this check cannot see>
```

It never deploys. Merge and release are your call, with the project's documented command.

### 3.10 Close the tracker issue

After the deploy is serving:

> Resolve the Sentry issue for the discount case bug, linked to PR #<n>.

`error-tracker-resolve` reads `.error-tracker.json` (or asks), finds the issue by ID or by the error message, confirms the PR touches the code in the stack trace, and requires the bug's regression AC to pass `acceptance_ledger.py verify PAY-482` at the released commit (or the release containing it). If the ticket has no ledger it says so and asks before resolving. It shows a table of issue / current status / proposed status / linked commit, and only then runs:

```bash
python3 skills/error-tracker-resolve/scripts/resolve.py --action resolved --org <org> --base-url <url> <ISSUE-ID> --yes
```

Without `--yes` it's a dry run. The token comes from `ERROR_TRACKER_TOKEN` (or `SENTRY_AUTH_TOKEN`) and is never printed. The skill prefers `resolvedInNextRelease` over resolving at merge, and `resolved` only once the smoke check shows the fix live; `resolvedInNextRelease` only works if your deploys create Sentry releases, otherwise the issue sits open.

### 3.11 Outcome review, weeks later

If the ledger carries outcome ACs (from a value-score file, or added with `add ... --kind outcome --metric <id> --verify-after YYYY-MM-DD`), they come due after release:

```bash
python3 $A outcomes-due --all
# PAY-482	AC-2	metric=support_volume	verify-after=2026-11-14	Given the fix is live When 14 days pass Then ...
# 1 outcome criteria due (as of 2026-11-15)
python3 $A record-outcome PAY-482 AC-2 --result met --evidence "helpdesk export 2026-11-15: 37 per 1k"
```

`outcomes-due <id>` scopes to one ledger; `--all` scans `docs/specs/*/acceptance.json`. `--result` is `met`, `not-met`, or `inconclusive`, and `--evidence` is the dashboard reading, not an opinion. `codebase-health` reports the overdue count across the repo.

## 4. Small ticket fast path

For a one-module bug or a contained change with no design decision:

1. `Enrich PAY-482` -> approve the comment -> `enrichment.json`
2. Branch, then `Start ATDD for PAY-482 from enrichment.json` -> `init`, `link`, `run` (RED), fix, `run` (GREEN), `check` PASS
3. `Run the commit gate` -> commit, push, `gh pr create`
4. `Describe this PR` -> review
5. `Is PAY-482 ready to release?` -> `verify` PASS at the merge commit -> merge

Five prompts. The ledger file goes in the PR so the reviewer sees red-before-green evidence, and the digests, without asking.

## 5. Big change path

Use this when the ticket touches more than a couple of modules, needs a design choice, or you don't know the area.

1. **Enrich** as above. Features and tasks must have `acceptance_criteria`; a criterion without an observable Then goes back to the reporter as a question.
2. **Seed the ledger**: `python3 $A init <KEY> --from enrichment.json`. Don't link tests yet.
3. **Research**: `Research how discount validation works, for PAY-490.` `spec-research` writes `docs/specs/research/YYYY-MM-DD-<slug>.md` with `path:line` for every claim, maps each AC to the code that must change and the tests that already cover nearby behavior, and lists unobservable ACs under Open Questions. On a Python repo it uses `codegraph-slicer slice` to find callers and `TESTS` edges instead of reading files one by one.
4. **Plan**: `Plan PAY-490 from that research.` `spec-plan` presents what it found and the mismatches with the ticket, offers 2-3 approaches, agrees a phase outline with you, then assigns every AC to a phase:
   ```bash
   python3 $A link PAY-490 AC-1 --phase 1
   python3 $A add  PAY-490 AC-4 "Given ... When ... Then ..." --phase 2 --kind behavior   # criteria planning uncovered
   python3 $A add  PAY-490 AC-5 "Given ... Then the 'Discount usage' dashboard ..." --kind outcome --metric support_volume --verify-after 2026-12-15
   python3 $A render PAY-490                                               # no blocking row may show phase -
   ```
   Kinds are fixed at creation; if a kind turns out wrong, the plan adds a new AC and says why rather than relabeling. Outcome ACs go in the plan's post-release section. It writes `docs/specs/plans/YYYY-MM-DD-<slug>.md` and stops. Nothing is implemented until you say `approve`, and the plan header gets `status: approved`.
5. **Implement, one phase at a time**: `Implement phase 1 of docs/specs/plans/....md`. `spec-implement` establishes a green baseline, writes the phase's acceptance tests, `link`s and `run`s each AC to RED, implements the minimum, `run`s to GREEN, refactors, then gates:
   ```bash
   python3 $A check PAY-490 --phase 1     # must print GATE: PASS before phase 2
   ```
   plus every automated criterion in the plan and the full suite once per phase. If the code doesn't match the plan it stops with Expected / Found / Why it matters / Options instead of improvising. It doesn't commit unless you ask.
6. **Validate**: `Validate the PAY-490 plan.` `spec-validate` re-runs everything from scratch: `plan_status.py` on the plan, every criterion command, every AC through `run`, then `verify` at the candidate commit, then the codegraph delta gate. A stale criterion or a test changed between RED and GREEN is a FAIL. Verdict PASS / PASS WITH NOTES / FAIL, report in `docs/specs/validation/`. It reports problems; fixing them is `spec-implement` work.
7. **Commit gate, PR, release readiness, tracker** as in the fast path.

### Letting fix-and-ship drive

> Ship PAY-490 to production.

`fix-and-ship` runs steps 3 to 7 for you with hard stops. Phase 0 resolves and shows a table you confirm with one word:

| Key | How it's found |
|---|---|
| `DEPLOY_BRANCH` | `git symbolic-ref refs/remotes/origin/HEAD` |
| `DEPLOY_TARGET` | CI deploy workflow, docs, or it asks |
| `TEST_CMD` / `PREDEPLOY_CMD` | CI config, Makefile, package scripts |
| `ERROR_TRACKER` | project slug in config or docs |
| `HEALTH_URL` | health or version endpoint |

Then it creates a branch, runs `spec-research`, `spec-plan`, waits for `approve` / `revise` / `abort`, runs `spec-implement` with the ledger, and enforces these gates in order, each a stop on failure:

- `acceptance_ledger.py check <id>` exits 0 before review (an AC without RED-then-GREEN, a stale criterion, or a test changed between RED and GREEN all stop it)
- `spec-validate` plus its own security pass on the diff (injection, authn/authz, secrets, deserialization, new dependencies, leaky error paths)
- `PREDEPLOY_CMD` plus conditional suites from `references/pre-deploy-gates.md` (migrations up and down, contract tests on public APIs, audit on lockfile changes, flag comparison), then `release-readiness`
- Ledger `verify <id>` at the merge candidate commit, then the codegraph delta gate; a hotfix exception needs your explicit approval and is recorded in the PR description
- `pr-describe`, CI green, then the question "Gates are green. Merge PR #N into `DEPLOY_BRANCH`?"
- Deploy only with the project's documented command and a second yes
- Smoke check: `curl --max-time 15` against `HEALTH_URL` until the new version serves or 10 minutes pass, then the changed path, then new error groups since deploy time

Two failed attempts at the same fix means it stops and asks rather than trying a third. Rollback options come from `references/gate-decision-tree.md` and are never taken unprompted.

## 6. Things that bite on day one

- **ERROR is not RED.** If `run` prints `ERROR is not RED: the test did not run to an assertion`, fix the import, fixture, or selector and rerun. The ledger stores the run either way, so the history shows what happened.
- **A selector that matches nothing** exits 5 on pytest and 0 on jest `-t`. Confirm the test actually ran in the tail.
- **Non-pytest runners**: set `--red-exit` to the exit code that means "ran and failed" for your runner (jest and pytest are both 1). `codegraph-args` skips non-pytest ids with a note on stderr; non-Python repos rely on the executed runs alone.
- **`codegraph-slicer` exits 2 and prints a message** for a stale index (re-run `sync`), a bad anchor, unsupported syntax in `flow`, or a budget too small (raise `--max-tokens`). It never returns an empty result for an unknown anchor.
- **Sync the project root, not a package directory**, or module ids lose their package prefix and `codegraph-args` output won't match.
- **Flaky tests poison the ledger.** Re-run once; if results differ, fix the flake before trusting either run.
- **A legitimate harness change trips the gate.** Adding a dependency to `pyproject.toml` or `package.json` between RED and GREEN changes `harness_sha`, and `check` reports `test harness changed between RED and GREEN`. Record RED again under the new harness: stash the implementation, `run`, unstash, `run`.
- **`verify` refuses a dirty tree.** Commit or stash first. It lists the differing files. The ledger JSON itself doesn't count as dirty.
- **Older ledgers**: runs recorded before digests existed show `legacy run without digests: re-run`. New RED, then GREEN.
- **The ledger is per spec id and lives in the repo.** One `docs/specs/<id>/` per ticket. `init` refuses to overwrite an existing ledger, and there's no `remove`; a wrong criterion gets `revise`d or superseded by a new AC.
