# Interpreting the metrics

## Contents

- [Metric definitions](#metric-definitions)
- [Shift to hypothesis map](#shift-to-hypothesis-map)
- [Linking Jira and GitHub](#linking-jira-and-github)
- [Review-time reading guide](#review-time-reading-guide)
- [Reporting caveats](#reporting-caveats)

## Metric definitions

| Metric | Definition | Note |
|---|---|---|
| Throughput | Issues resolved per ISO week | Count, not effort |
| Lead time | created to resolved | Includes time waiting in backlog |
| Cycle time | first entry to start status to resolved | Needs changelog |
| Blocked share | issues blocked now or previously, over all issues | Blocked days sum time in the blocked status |
| Time to first review | PR created to first review by someone other than the author | Hours |
| Time to merge | PR created to merged | Hours |

Use median and p90. Means are dominated by a few long-running items.

## Shift to hypothesis map

| Observed shift | Hypotheses to test | Confirm with |
|---|---|---|
| Throughput down, cycle time flat | Fewer or larger items; less capacity | Points and size mix; team roster and leave |
| Cycle time up, review time flat | Waiting before work starts; WIP too high | Time in each status from changelog |
| Cycle time up, first-review time up | Review bottleneck | Reviewer concentration; PR size trend |
| Blocked share up | External dependency, unclear requirements, environment issues | Blocked ticket comments and links; blocker labels |
| Bug share up | Regression after a release, incident load, quality debt | Bug creation dates against releases |
| Epic spread up | Context switching, interrupt-driven work | Distinct epics per week; unplanned items |
| p90 far above median | A few stuck items | List the top 5 by cycle time; read each |
| Many issues without points | Estimation habit lapsed | Points coverage by period |

Report the top one or two hypotheses with evidence; do not list every possibility.

## Linking Jira and GitHub

- Match by ticket key in PR title, branch name, or commit message. Keys in titles are the most reliable.
- Unlinked PRs are normal (chores, dependency bumps). Report the linked share so readers know coverage.
- A ticket can have several PRs; take first PR opened to last PR merged for the engineering span.
- Never infer individual effort from PR counts or size.

## Review-time reading guide

- First review under a few hours on a working day is healthy; days indicate a queue or ownership gap.
- If a single reviewer handles most reviews (high top-reviewer share), that person is a bottleneck and a single point of failure.
- Large PRs (500+ changed lines) merge slower and get shallower review; compare by size bucket before blaming reviewers.
- Several change-request rounds suggest unclear requirements or missing conventions, not only code quality.
- Time to merge includes author delay; first-review time isolates reviewer responsiveness.

## Reporting caveats

State the date ranges, issue counts per period, whether changelog was available, field ids used, and anything excluded (bots, subtasks). Say plainly when the data cannot support a conclusion.
