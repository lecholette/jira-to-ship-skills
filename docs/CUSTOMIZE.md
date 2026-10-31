# Customizing the skills for your repo

What you get here: the short list of files and values each team edits so the skills reflect your business metrics, your team routing, your test runner, and your deploy setup. Everything else is discovered from the repo at run time. None of this requires editing a `SKILL.md`.

Where a value lives in the repo, commit it; where it lives in the skill folder, it's a default for everyone who symlinks that skill, so prefer the repo override.

## Success metrics (jira-value-score)

`score.py` resolves the metrics file in this order and names the one it used in its output header:

1. `--metrics <path>` on the command line
2. `.jira-enrich/success-metrics.json` in the current working directory (the repo)
3. `skills/jira-value-score/success-metrics.json`, the bundled defaults

The bundled defaults are a generic SaaS set (activation rate, 30-day retention, net revenue expansion, support volume, one latency guardrail) with placeholder baselines. If the header says `(bundled defaults)`, the ranking reflects nobody's priorities. Put your own at `.jira-enrich/success-metrics.json`:

```json
{
  "metrics": [
    {"id": "containment_rate", "name": "Calls resolved without agent handoff", "weight": 5, "direction": "up",
     "unit": "%", "baseline": 61, "target": 70, "how_measured": "Conversation analytics: resolved_by_bot / total_conversations, weekly"},
    {"id": "onboarding_days", "name": "Days from contract to first live deployment", "weight": 4, "direction": "down",
     "unit": "days", "baseline": 45, "target": 30, "how_measured": "Implementation tracker, per account"}
  ],
  "guardrails": [
    {"id": "reliability_latency", "limit": "Availability >= 99.9% and API p95 < 400 ms", "weight": 3}
  ]
}
```

Rules: `id` is unique snake_case and judgments reference it (an unknown id makes `score.py` exit 2); `weight` is relative, 1-5 works; `direction` is the good direction; `how_measured` is required because outcome criteria must cite it. Weights are the team's call. The skill will never retune them to produce an expected ranking, and neither should you mid-sprint.

The metric `id` is also what an outcome AC carries in the ledger (`add ... --kind outcome --metric containment_rate --verify-after 2026-12-15`, or via `init --from` on a value-score file). Pick ids you're willing to see in traceability matrices for months.

Format details: `skills/jira-value-score/references/metrics-config.md`.

### Outcome criteria file

The value-score JSON that `init --from` accepts needs, per entry, all four fields:

```json
{"key": "PAY-482", "outcome_criteria": [
  {"text": "Given the fix is live When 14 days pass Then support tickets per 1k users are below 40 on the helpdesk export",
   "metric": "support_volume", "verify_after": "2026-11-14",
   "instrumentation_text": "Given a discount is applied When the request completes Then a discount_applied event is emitted with the code casing"}
]}
```

Each entry becomes an instrumentation AC (blocking, needs a test) followed by an outcome AC (post-release, `instrumented_by` points at the instrumentation AC). Set `verify_after` to the end of the measurement window the metric's `how_measured` implies, and put `outcomes-due --all` on whoever runs the sprint review.

## Routing (jira-ticket-enrich)

Optional. Without it, routing uses the Jira component field and similar-ticket history only, and the skill says so. With it, `.jira-enrich/routing.yaml` in the repo:

```yaml
teams:
  - name: Payments
    project: PAY
    components: ["Billing", "Checkout"]
    keywords: ["invoice", "refund", "card"]
    triage_assignee: null
  - name: Voice Platform
    project: VP
    components: ["IVR", "Telephony"]
    keywords: ["call drop", "SIP", "transfer"]
    triage_assignee: null
disambiguation:
  - when_all: ["policy"]
    if_any: ["invoice", "refund", "charge"]
    route_to: Billing
  - when_all: ["policy"]
    if_any: ["login", "password", "sso"]
    route_to: Identity
```

`disambiguation` runs before keyword matching; use it for words that span teams (`policy`, `control`, `config`). Leave `triage_assignee` null to route to the team's queue rather than a person. The skill suggests an individual only with strong similar-ticket history.

Signal order and the config format: `skills/jira-ticket-enrich/references/routing.md`.

## Test command, red exit codes, and the harness list (atdd and everything that calls the ledger)

The ledger never guesses the test command. `atdd` reads it from README, CLAUDE.md or AGENTS.md, Makefile, or package scripts, and asks once if it can't find it. Put a line in the repo's CLAUDE.md or AGENTS.md so nobody gets asked:

```
Test command: pytest -q --tb=short
Single test: pytest -q <path>::<name>
```

Three ledger settings depend on your runner:

- `--red-exit` (default `1`): comma-separated exit codes that mean "the test ran and an assertion failed". pytest and jest both use 1. Check your runner; some return the number of failures, some use 2 for failures. Anything outside this list is recorded as ERROR and will not satisfy the gate. `verify` re-uses the value recorded on the GREEN run, so settle it before the first `run`.
- `--timeout` (default 300 seconds): a run past it is recorded as ERROR with exit 124.
- The command itself. `check` requires the GREEN's command to equal the RED's (whitespace-normalized), so pick the single-test form once and keep using it. Changing `-q` to `-v` between runs is a gate failure.

The harness digest is not configurable. It always covers every `conftest.py` from the repo root down to the test's directory, plus root-level `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `package.json`, `jest.config.*`, `vitest.config.*`, and `playwright.config.*`. Two consequences for how you lay out a repo:

- A dependency bump in `pyproject.toml` or `package.json` between RED and GREEN trips `test harness changed between RED and GREEN`, even when it's the dependency the fix needs. Do the bump first, record RED under the new harness, then implement. If you already implemented, stash the implementation, `run` (RED), unstash, `run` (GREEN). The sequence is in `skills/atdd/references/ledger-format.md`.
- Test helpers that live outside the conftest chain (a `tests/helpers.py`, a shared fixtures package) are not digested. Prefer putting shared fixtures in `conftest.py` so the gate sees them, and review helper diffs by hand.

Also document in CLAUDE.md or AGENTS.md whichever of these the skills would otherwise ask for: lint, type-check, and build commands (`spec-plan` copies them verbatim into success criteria), the docs location if you don't want `docs/specs/`, the branch naming convention, and whether the agent may commit (`spec-implement` won't unless told; `verify` needs a commit, so the release gate implies one).

`commit-gate` detects tools from config files via `scripts/detect_tools.py`; if it finds nothing it reads the same docs. It prefers what CI or a `pre-commit` config runs, so keeping CI honest keeps the gate honest.

## Deploy configuration (fix-and-ship)

Phase 0 fills this table from README, CLAUDE.md or AGENTS.md, package.json, Makefile, pyproject, and CI config, then asks you to confirm it:

| Key | Source | What to document |
|---|---|---|
| `DEPLOY_BRANCH` | `git symbolic-ref refs/remotes/origin/HEAD` | Nothing, unless the deploy branch isn't the default branch |
| `DEPLOY_TARGET` | CI deploy workflow or docs | Where production lives, and whether merging deploys or a separate command does |
| `TEST_CMD` / `PREDEPLOY_CMD` | CI config, Makefile, package scripts | The exact pre-deploy command, ideally the same as CI's test and lint jobs |
| `ERROR_TRACKER` | config or docs | Project slug |
| `HEALTH_URL` | docs | A health or version endpoint that shows the running build |

The skill won't invent any of these. A sentence each in CLAUDE.md or AGENTS.md is enough:

```
Deploy: merging to main triggers the deploy workflow; no manual step.
Pre-deploy: make check test
Health: https://api.example.internal/health returns {"version": "<sha>"}
```

`HEALTH_URL` matters more than it looks. `verify` prints the commit sha it passed at, `error-tracker-resolve` wants `verify` at the released commit, and the smoke check needs to read the running version to know which commit that is. An endpoint that returns the git sha closes that loop; one that returns `ok` doesn't.

Conditional gates (migrations up and down, contract tests for public APIs, audit on lockfile changes, flag comparison) are chosen by the paths the diff touches; the table is in `skills/fix-and-ship/references/pre-deploy-gates.md`. Failure handling and rollback order are in `references/gate-decision-tree.md`.

### Error tracker (error-tracker-resolve, release-readiness, fix-and-ship)

`.error-tracker.json` at the repo root:

```json
{"provider": "sentry", "base_url": "https://sentry.io", "org": "your-org", "project": "your-project"}
```

Token in the `ERROR_TRACKER_TOKEN` environment variable (`SENTRY_AUTH_TOKEN` also works); `ERROR_TRACKER_ORG` and `ERROR_TRACKER_URL` can stand in for the file. It's never printed or stored. If a tracker MCP is connected, the skill prefers it over `scripts/resolve.py`.

Decide once whether your deploys create tracker releases. If they do, `resolvedInNextRelease` is the default the skill prefers and the issue closes itself when the release containing the fix ships. If they don't, say so in CLAUDE.md or AGENTS.md, because `resolvedInNextRelease` would leave the issue open forever and the skill should go straight to `resolved` after the smoke check.

## Import boundaries (codegraph gate)

No default rules. Each architecture rule is one `--forbid-import SOURCE_PREFIX TARGET_PREFIX` on the `delta` command; the pair is reported in `boundary_violations` and fails `delta_gate.py`. Prefixes match module ids, so for a repo laid out as `app/domain`, `app/web`, `app/infra`:

```bash
codegraph-slicer delta --base-db B --head-db H --full --max-tokens 200000 \
  --forbid-import app.domain app.web \
  --forbid-import app.domain app.infra \
  $(python3 <atdd>/scripts/acceptance_ledger.py codegraph-args <id>) | python3 <codegraph>/scripts/delta_gate.py
```

Write the rules once in CLAUDE.md or AGENTS.md under a heading the skills will find ("Import boundaries: domain must not import web or infra") so `spec-validate`, `release-readiness`, and `fix-and-ship` pass the same flags. Targets with no indexed module are still reported, so a rule against a package that doesn't exist yet is harmless.

## Smaller knobs

- **PR template**: `pr-describe` uses `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, or `docs/pull_request_template.md`. Put runnable commands under a "How to verify" heading and it will run and tick them. The traceability matrix it embeds now has Kind and Evidence columns; a template section named "Acceptance evidence" gives it a natural home.
- **Commit hook**: `commit-gate` writes one only when asked, prefers your existing `pre-commit`, husky, or lefthook setup, and keeps it under about 30 seconds. `check` fits in a hook; `verify` doesn't (it re-runs tests and needs a clean tree), so keep `verify` in CI or the release step.
- **Docs locations**: defaults are `docs/specs/<id>/acceptance.json`, `docs/specs/research/`, `docs/specs/plans/`, `docs/specs/validation/`. Each skill checks README and CLAUDE.md or AGENTS.md for a documented docs location first. `outcomes-due --all` and `codebase-health` scan `docs/specs/*/acceptance.json`, so moving the ledger means passing `--root` consistently.
- **Failure patterns for RCA**: `skills/jira-rca/references/failure-patterns.md` is meant to grow with your recurring causes. Add a line after each RCA; keep it short.
- **Jira field ids for productivity metrics**: story points and epic link fields differ per instance; pass `--points-field` and `--epic-field` to `analyze_jira_data.py`, and `--start-status` if "In Progress" isn't the status that starts your work clock. Requirement churn (criteria revised after GREEN) comes from the ledgers' `revisions` and needs no configuration.
- **Health scan thresholds**: `health_scan.py --max-file-lines` (500) and `--max-func-lines` (50).
- **Codegraph databases**: write them outside the repo (`mktemp -d`); one database holds one snapshot, so base and head need separate files.
