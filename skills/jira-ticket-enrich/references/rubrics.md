# Rubrics

## Classification

Classify from content, not title or current issue type.

| Type | Signals |
|---|---|
| BUG | Error, crash, fails, regression, "used to work", stack trace, expected vs actual |
| FEATURE | "As a ... I want", new capability, enhancement, "would like" |
| TASK | Chore, migration, upgrade, documentation, no user-facing behavior change |
| UNCLEAR | Vague ("doesn't work"), performance complaints with no baseline, mixed signals |

Confidence: 80+ clear signals; 60-79 some ambiguity; under 60 mark UNCLEAR and name the single question that resolves it.

## Definition of Ready

Score each item present / partial / missing. Readiness % = (present + 0.5 x partial) / applicable items.

Both types:
- Clear summary that states the problem or outcome
- Who is affected (role, customer, segment) and how many
- Link to related tickets, designs, or docs where relevant

Bug:
- Numbered reproduction steps
- Expected vs actual result
- Environment (version/build, browser/device, tenant/account type, region)
- Frequency (always / intermittent / once) and first seen date
- Evidence (error text, log excerpt, request ID, screenshot description)
- Workaround known or none

Feature / task:
- Problem or user need, not just a solution
- Acceptance criteria, testable (Given / When / Then)
- Scope boundary: what is explicitly out
- Dependencies and unknowns listed
- Small enough for one iteration, or a proposed split (INVEST: independent, negotiable, valuable, estimable, small, testable)

Readiness is a conversation aid, not a gate. Do not recommend blocking a ticket for a missing item the team can resolve in a five-minute conversation; say so instead.

## Impact

Rate two axes separately, because they differ.

**Severity** (technical damage): Critical (data loss, security exposure, outage) / Major (core flow broken, no workaround) / Minor (degraded, workaround exists) / Cosmetic.

**Urgency** (business pressure): named customer or contract at risk, regulatory or compliance deadline, revenue-path blocked, volume of reports, upcoming release.

Suggested priority decision path (adjust labels to the project's scheme):
1. Critical severity, or Major severity affecting most users or a named key customer: highest tier
2. Major severity with workaround, multiple customers, or revenue risk: high tier
3. Otherwise: normal tier

Always output the path taken and the evidence quote. If the current priority already fits, say "no change". Be conservative with the top tier. Detect customer mentions from bracketed company names, email domains, and words like "customer" or "account".
