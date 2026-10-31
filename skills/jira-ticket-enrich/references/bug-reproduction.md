# Bug reproduction plan

Pick one approach:

| Approach | Use when |
|---|---|
| STATIC | Logic error, config, or missing validation findable by reading code |
| TEST | Deterministic, API or unit level; an automated test can capture it |
| MANUAL | UI, browser, timing, or environment specific |
| BLOCKED | Steps, environment, or expected behavior missing; list exactly what is needed |

Output:
1. Approach and confidence
2. Preconditions (account type, feature flags, data state)
3. Numbered steps, one action each
4. Expected vs actual
5. Environment
6. Blockers, each phrased as a question for the reporter
7. Deep mode only: suspected location (`path:line-range`), hypothesis, complexity (Low/Med/High), risk (Low/Med/High)

Keep reporter-supplied steps verbatim and label them. Mark any step you inferred as "inferred". A hypothesis is not a root cause until a test or a trace confirms it; label it accordingly.
