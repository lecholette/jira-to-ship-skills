# Zoom Out failure modes, with repairs

## Contents

- [Judgment at L0](#judgment-at-l0)
- [One-legged pattern](#one-legged-pattern)
- [Situation as recap](#situation-as-recap)
- [Unfalsifiable implication](#unfalsifiable-implication)
- [Coverage silence](#coverage-silence)
- [Smoothed contradictions](#smoothed-contradictions)
- [Inherited premise](#inherited-premise)
- [Loop by narrative](#loop-by-narrative)
- [Context from survivors](#context-from-survivors)
- [Undated outside fact](#undated-outside-fact)
- [Verdict leaking into L4](#verdict-leaking-into-l4)

## Judgment at L0

Looks like: `E7 - only 3 integration tests exist, which is thin.` The verdict is baked into the foundation and every level above inherits it.
Repair: split observation from judgment.
```
E7. [FACT] 3 integration tests cover checkout - tests/integration/test_checkout.py
E8. [COMPUTED] 3 of 61 integration tests (4.9%) cover checkout, which handles 31% of requests
```
Leak words: only, just, still, merely, unfortunately, already, thin, solid, fragile.

## One-legged pattern

Looks like: `P2. The code relies heavily on global state [E9]`. One observation restated more abstractly.
Repair: find the second leg (`read in 3 modules, written in 1, no locking [E9, E14, E21]`) or leave it as evidence. 14 evidence items and 3 patterns is a real result.

## Situation as recap

Looks like a bulleted list of the patterns. Nothing new at this level.
Repair: ask what the patterns do to each other. Look for a tension (they pull opposite ways), a dependency (fixing one first fails), or a trajectory (stages of one process).

## Unfalsifiable implication

Looks like "focus on quality" or "needs more validation". Nothing would overturn it.
Repair: name the decision, what the judgment excludes, and one observation that would change it. A preference with no falsifier is not a finding.

## Coverage silence

No statement of what was read. Confidence is unbounded and unearned.
Repair: always give universe / examined / selection rule, for example "read all 6 design docs, sampled 12 of 212 source files, picked by recent churn".

## Smoothed contradictions

Two patterns disagree and one quietly disappears.
Repair: keep both and list the conflict under Open contradictions. It often points at the real finding.

## Inherited premise

Looks like `E3. [FACT] system handles 2M requests/day - README.md:14`. The material testifying about itself is not observation.
Repair: tag `[REPORTED]`, then verify where load-bearing. The gap between claim and measurement is often the pattern.

## Loop by narrative

A feedback loop with no countable stock, no dates, and no cited edges is a story.
Repair: name the stock, cite each edge to L1/L2 items, check that dated evidence shows cause before effect, and assign HYPOTHESIZED / SUPPORTED / TESTED honestly. An edge with no cited item is deleted, not softened. Do not promote a loop to improve the narrative.

## Context from survivors

A map of who exists, read as a map of who tried.
Repair: before claiming a gap, check who tried and stopped, which alternatives are invisible to the usual lists (open source, in-house, the do-nothing option), and why an empty space is empty. Record the zeros as evidence.

## Undated outside fact

An outside claim with no as-of date silently expires. Prices and benchmarks go stale in weeks; architecture and roadmap claims in months; ownership and regulation in a year or more.
Repair: attach source and date to every outside fact; drop any you cannot date.

## Verdict leaking into L4

Looks like `C2. The vendor is a serious threat.` Outside facts and causal structure sound analytical, so verdicts hide there.
Repair: state what is (`Vendor shipped a native equivalent on 2026-08-14 [X5]`) and move the meaning to the implication or the check. Leak words: threat, opportunity, moat, white space, inevitable, doomed, dangerous.
