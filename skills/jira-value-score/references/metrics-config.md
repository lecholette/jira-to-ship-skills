# Metrics config

These are defaults; edit `success-metrics.json` (or put your own at `.jira-enrich/success-metrics.json` in the repo, which takes precedence) to match your business.

Precedence: `--metrics <path>` if given, else `.jira-enrich/success-metrics.json`, else the bundled `success-metrics.json`. The score output header names the file used. Always tell the user which one.

## Format

```json
{"metrics":[{"id":"activation_rate","name":"...","weight":5,"direction":"up",
             "unit":"%","baseline":38,"target":50,"how_measured":"dashboard or query"}],
 "guardrails":[{"id":"reliability_latency","limit":"...","weight":3}]}
```

- `id`: unique snake_case; judgments reference it. Unknown ids make `score.py` exit 2.
- `weight`: relative importance, 0-100 (use 1-5). Weights are the team's priorities, not facts to infer.
- `direction`: `up` or `down` (the good direction). A ticket that moves the metric the wrong way is judged `effect: worsens`.
- `baseline`, `target`: current and goal values; they anchor magnitude judgments.
- `how_measured`: the dashboard, event, or query. Outcome criteria must cite it.
- Guardrails are things that must not get worse; a risk subtracts `weight * severity * confidence`.

## Bundled defaults (generic SaaS)

| id | Name | Weight | Direction | Baseline -> target | How measured |
|---|---|---|---|---|---|
| activation_rate | New-user activation rate | 5 | up | 38% -> 50% | Funnel: activated_user / signup_completed |
| retention_30d | 30-day retention | 4 | up | 60% -> 68% | Weekly signup cohort report |
| expansion_revenue | Net revenue expansion | 4 | up | 102% -> 110% | Billing report, net revenue retention |
| support_volume | Support tickets per 1k active users | 2 | down | 42 -> 30 | Helpdesk export by contact reason |

| Guardrail id | Limit | Weight |
|---|---|---|
| reliability_latency | Availability >= 99.9% and API p95 < 400 ms | 3 |

Baselines and targets are placeholders. Replace them with real numbers when you have them.

## Judgment shape (input to score.py)

```json
{"key":"APP-102","summary":"...","size":"S","confidence":0.8,
 "time_criticality":0,"risk_reduction":0,
 "metrics":[{"id":"activation_rate","effect":"improves","magnitude":2,
             "confidence":0.7,"evidence":"\"43% abandon at step 3\""}],
 "guardrail_risks":[{"id":"reliability_latency","severity":1,"confidence":0.5}]}
```

`magnitude`/`severity`/`time_criticality`/`risk_reduction`: 0-3. `confidence`: 0-1. Any magnitude above 0 needs quoted evidence.
