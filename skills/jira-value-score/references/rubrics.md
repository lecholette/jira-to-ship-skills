# Judgment rubrics

## Magnitude (per metric)
- 0 none; 1 small (a segment, a minor step); 2 meaningful (closes a visible part of baseline-to-target gap); 3 major (could close most of the gap).
- Anchor to baseline and target. Quote the ticket text or linked data that supports it. No quote, no score.

## Confidence (0-1)
- 0.8+ ticket cites data (funnel numbers, ticket counts); 0.5-0.7 plausible mechanism, no data; under 0.5 speculation. Say what evidence would raise it.

## Time criticality (0-3)
- 0 none; 1 soft preference; 2 dated commitment or value decaying within a quarter; 3 hard deadline, contract, or regulation within weeks. Quote the date.

## Risk reduction / enablement (0-3)
- Reduces outage, security, or compliance risk, or unblocks other high-value work. 0 none; 3 prevents a serious incident or unblocks several tickets. Name what is unblocked.

## Size band (cost, not story points)
Use enrichment `size_signals` when present, else ticket content. Never estimate hours.
- S: one component, no unknowns. M: a few files, one team, minor unknowns. L: multiple components or a cross-team dependency. XL: new subsystem, migration, or many unknowns.
- Mapped to divisors 1/2/3/5. Size only divides; it never adds to value.

## Guardrail risk (0-3)
- Chance and size of harm to a guardrail (a new query on a hot path, a heavier page). Judge with confidence like any metric.
