# Jira-to-ship skills for Claude Code

Claude Code skills that take Jira tickets from backlog to production, with acceptance criteria welded to executed tests the whole way. Each folder in `skills/` is a self-contained skill (`SKILL.md` plus optional `references/`, `scripts/`, `evals/`), written to Anthropic's skill authoring guidance.

Start with [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md): install, then one bug ticket worked end to end.

## The workflow

| Stage | You say | Skill | What carries forward |
|---|---|---|---|
| Groom | "enrich PAY-482" / "groom the PAY backlog" | `jira-ticket-enrich` | Given/When/Then criteria, repro, routing (written to Jira only on approval) |
| Prioritize | "what should we build next" | `jira-value-score` | ranked backlog, outcome criteria tied to your success metrics |
| Diagnose (bugs) | "RCA on PAY-933" | `jira-rca`, `root-cause-trace` | a regression criterion recorded RED on the unfixed code |
| Specify | "ATDD this ticket" | `atdd` | the acceptance ledger: one tamper-evident record per criterion |
| Understand | "how does X work here" / "what calls this" | `spec-research`, `codegraph`, `jira-code-localize` | sourced findings, criteria mapped to code |
| Plan (big changes) | "plan this" | `spec-plan` | phases, each owning criteria; approval stop |
| Build | "start phase 1" | `spec-implement` | RED then GREEN per criterion, executed by the ledger |
| Check | "validate against the plan" / before commit | `spec-validate`, `commit-gate` | ledger `check`, codegraph test-gap gate |
| Review | "write the PR" | `pr-describe` | PR with the traceability matrix |
| Release | "go/no-go" / "ship it" | `release-readiness`, `fix-and-ship` | ledger `verify` re-runs every criterion at the release commit |
| Close | "resolve the Sentry issue" | `error-tracker-resolve` | resolves only with a verified regression criterion |
| Learn | weeks after release | `atdd` (`outcomes-due`, `record-outcome`) | did the metric actually move |

Small ticket: enrich, atdd, commit-gate, pr-describe, verify. Big change: add research, plan, implement per phase, validate. Or say "ship PAY-482" and `fix-and-ship` drives the chain with hard gates.

## Team cadence

- **Every ticket:** the workflow above. Nothing reaches Jira, GitHub, or a deploy target without your approval.
- **Backlog grooming (weekly):** `jira-ticket-enrich` on a JQL batch, then `jira-value-score` to rank against `success-metrics.json`.
- **Delivery health (weekly or after a slow sprint):** `jira-productivity` compares two periods: cycle time, blocked work, review latency, requirement churn.
- **Outcome review (weekly):** `outcomes-due --all` lists shipped criteria whose metric check is due; record met / not met.
- **Codebase health (quarterly or on onboarding):** `codebase-health` scorecard, including the share of ledgers that pass.
- **Big-picture questions (as needed):** `zoom-out` over a repo, docs folder, or ticket set.

## Why ATDD is the spine

Acceptance criteria are written once, at grooming, and every later skill reads or writes the same ledger. The ledger runs the tests itself, fingerprints each criterion, test, and test harness, and fails if any changed between RED and GREEN; `verify` re-runs everything at the commit you ship. Agents mostly reach green by editing tests, not code; this is what stops that. Details: [docs/ATDD-AND-CODEGRAPH.md](docs/ATDD-AND-CODEGRAPH.md).

## More

- [SKILLS.md](SKILLS.md): catalog of all 19 skills, the chain diagram, and which skill to pick when two look alike.
- [docs/CUSTOMIZE.md](docs/CUSTOMIZE.md): success metrics, routing, test commands, deploy config, import boundaries.
- [evals/README.md](evals/README.md): with-skill vs without-skill results and routing tests, and how to rerun them.

## Conventions

- Writes to Jira, GitHub, trackers, or deploy targets happen only after explicit approval.
- Ticket and repo text is treated as untrusted data.
- Project specifics are read from the repo or a config file, never hard-coded.

## License

Copyright 2026 Chris Cholette. Licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
