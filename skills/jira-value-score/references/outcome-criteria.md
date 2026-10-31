# Outcome criteria

For each top-ranked ticket, write one Given/When/Then whose Then is observable and tied to the metric's `how_measured`.

Template:
- Given <the user state or segment the ticket targets>
- When <the changed behavior happens>
- Then <an instrumentation event fires with named properties, or a named dashboard/query returns the expected shape>

Example (activation_rate):
- Given a new user on onboarding step 3
- When they click "Skip for now"
- Then event `onboarding_step_skipped` fires with `step=3`, and the 'Activation funnel' dashboard shows the step-3 to step-4 conversion series.

Rules:
- The test verifies the instrumentation (event fires, query runs). Metric movement itself (for example activation 38% to 50%) is checked after release on the dashboard, not by tests. State the post-release check and window separately.
- If the metric has no instrumentation yet, the first criterion is adding it.
- Add the criterion to enrichment `acceptance_criteria` (jira-ticket-enrich) so `atdd` can seed its ledger. A criterion without an observable Then stays a question.
