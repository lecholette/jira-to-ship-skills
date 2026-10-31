# Failure patterns (starter)

Use to seed the hypothesis register, not to replace evidence. Extend this file with recurring causes from your own systems: add a pattern, its diagnostic questions, and the evidence that proves it. Keep entries short.

## Contents

- [State desync between systems](#state-desync-between-systems)
- [Silent partial commit](#silent-partial-commit)
- [Stale or missing data](#stale-or-missing-data)
- [Data not propagated](#data-not-propagated)
- [Status display wrong](#status-display-wrong)
- [Retry and idempotency](#retry-and-idempotency)
- [Time and timezone](#time-and-timezone)
- [Config or feature flag](#config-or-feature-flag)
- [Permissions and tenancy](#permissions-and-tenancy)
- [Recent change regression](#recent-change-regression)
- [Tooling and operational](#tooling-and-operational)
- [Adding your own pattern](#adding-your-own-pattern)

## State desync between systems

Two systems hold contradictory state after an action. Variants: write never delivered, change applied without the follow-up step, manual action outside the automated pipeline, cancel not propagated.
Ask: was the downstream write acknowledged? Was our record created before or after acknowledgement? Is there a retry queue and was it checked? Does manual tooling trigger the same sync?
Evidence: record ids and state in both systems with timestamps.

## Silent partial commit

An error was shown but part of the operation persisted. Typical in multi-step flows without a transaction or compensation.
Ask: which steps are atomic? What happens on timeout between steps?
Evidence: logs for each step with the same correlation id; resulting rows.

## Stale or missing data

A cache, index, or inventory source is out of date, or an expected record was never created.
Ask: when was the source last refreshed? Is the key present upstream? Is there a TTL?
Evidence: source value versus cached value with timestamps.

## Data not propagated

A field exists at the origin but is dropped by a mapper, serializer, or API version, or is overwritten by a later sync.
Ask: is the field in every hop's mapping? Does a later job rewrite it?
Evidence: the value at each hop for one record.

## Status display wrong

The status shown differs from the real one: poll not updated, event missed, wrong source of truth displayed.
Ask: how does the UI learn status (push, poll)? Which field is read?
Evidence: API response versus stored state versus UI.

## Retry and idempotency

Duplicates or double effects after timeouts or user re-submits; missing idempotency keys.
Ask: is the operation idempotent? What key dedupes? Do clients and workers both retry?
Evidence: request ids, repeated writes with the same payload.

## Time and timezone

Off-by-hours, off-by-day, DST edges, date-only versus datetime, clock skew.
Ask: what zone is stored, parsed, displayed? Is the symptom near midnight or a DST change?
Evidence: raw stored value, parsed value, displayed value.

## Config or feature flag

Behavior depends on a flag, tenant setting, or environment value that differs from expectation.
Ask: what flags gate this path? What are their values for the affected scope?
Evidence: flag state and its change history.

## Permissions and tenancy

A user or tenant sees too much, too little, or someone else's data; role checks missing on one path.
Ask: which check guards this path? Does a sibling path have it?
Evidence: the authorization code path and a request that crosses the boundary.

## Recent change regression

It worked before a specific deploy, migration, or dependency bump.
Ask: first-seen time versus deploy log; what changed in the touched paths?
Evidence: `git log` for the suspect paths, deploy timestamps, a bisect result.

## Tooling and operational

Missing access, broken job, full disk, expired credential, rate limit.
Ask: is the failure present at the infrastructure layer before it reaches code?
Evidence: job status, quota and expiry data.

## Adding your own pattern

```
## <Pattern name>
Definition: <one sentence>
Ask: <2-4 diagnostic questions>
Evidence: <the artifacts that prove it>
Fix path: <usual owner or area>
```
