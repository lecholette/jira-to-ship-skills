# Fix at the source, not the consumer

## Contents

- [Why downstream patches fail](#why-downstream-patches-fail)
- [Smells that you are patching the wrong place](#smells-that-you-are-patching-the-wrong-place)
- [Source vs boundary vs consumer](#source-vs-boundary-vs-consumer)
- [Before and after](#before-and-after)
- [When the consumer fix is right](#when-the-consumer-fix-is-right)

## Why downstream patches fail

- The bad value keeps flowing to every other consumer.
- The patch encodes a guess about what "bad" looks like and misses the next variant.
- Defaults such as "Unknown" or 0 turn a visible failure into a plausible wrong answer.
- Each patch makes the real cause harder to find.

## Smells that you are patching the wrong place

- Adding `if x is None: continue` or `or "N/A"` in rendering code.
- Wrapping a call in try/except that logs nothing.
- Filtering results after the fact because the query returns too much.
- Adding a retry to hide a nondeterministic failure you have not explained.
- Re-deriving in the consumer a value the source already knows.
- Adding a rule to a validator that flags correct output, instead of asking whether the validator can decide that question at all.

## Source vs boundary vs consumer

| Place | Job | Fix looks like |
|---|---|---|
| Source (where data is created or calculated) | Produce correct, typed values | Fix the calculation, add a return type, expose derived values here |
| Boundary (serialization, storage, API, intake) | Validate and convert once | Schema or type checks, clear errors, a log on malformed input |
| Consumer (UI, report, caller) | Use data it can trust | Remove defensive code once the two above are fixed |

## Before and after

Before: a report page filters out `None` entries and shows "Unknown" for missing owners.
After: the lookup function raises or skips on miss with a logged warning; the serializer rejects null owners; the page prints the list as given and the filter is deleted.

Before: three services each re-round currency amounts.
After: one money type rounds at creation; services pass it through.

## When the consumer fix is right

Only when upstream is verified correct and the consumer misreads or mislabels it: wrong column, wrong unit label, wrong time zone on display, a formatting bug. Say what you verified upstream.

If you cannot change the source (third-party code, another team), put the workaround at the boundary closest to it, comment why, and report the source defect so it can be fixed properly.
