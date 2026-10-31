# Ten Whys: method, examples, stopping rules

## Contents

- [Method](#method)
- [Example: wrong total](#example-wrong-total)
- [Example: missing field after save](#example-missing-field-after-save)
- [Stopping rules](#stopping-rules)
- [Bad chains](#bad-chains)

## Method

1. Write the symptom exactly.
2. Ask why, answer from code or output, cite it.
3. Make the answer the next question.
4. Keep going past the first cause that "feels right". Ten is a ceiling for discipline, not a quota; five well-evidenced whys that reach an owned decision are enough.
5. Stop at a cause where the fix is a change you can make and test.

## Example: wrong total

```
SYMPTOM: Invoice total is 12.5% too high for EU customers
Why 1: the page shows invoice.total                        (invoice.html:30)
Why 2: invoice.total includes tax twice                    (repro: net 100, total 125.44)
Why 3: tax is added in compute_total and again in finalize (pricing.py:55, pricing.py:91)
Why 4: finalize assumes compute_total returned net         (comment pricing.py:88)
Why 5: compute_total was changed to return gross in a later refactor (git log -S)
ROOT CAUSE: contract drift between compute_total (gross) and finalize (expects net)
ORIGIN: the source function and its caller disagree; fix the contract once
```

Fix: make `compute_total` return a typed result with `net`, `tax`, `gross`; `finalize` reads `net`. Test at that function. Delete nothing downstream because nothing was patched.

## Example: missing field after save

```
SYMPTOM: "nickname" is blank after editing a profile
Why 1: the API response has nickname = ""                  (curl output)
Why 2: the stored row has nickname NULL                    (db query)
Why 3: the update handler builds the row from a whitelist  (profile.py:40)
Why 4: nickname was added to the form and model but not the whitelist (diff)
ROOT CAUSE: whitelist in profile.py:40 omits the new field
```

Fix at the handler, and add a test that every model field is either in the whitelist or explicitly excluded, so the next field cannot be forgotten.

## Stopping rules

| Stop when you reach | Because |
|---|---|
| A function that returns the wrong thing | You can fix and unit-test it |
| A boundary that accepts or converts bad input without checking | Validation belongs there |
| A contract mismatch between two components | The contract is the thing to fix |
| A verified external fact (vendor behavior, spec) | Adapt at the boundary and document it |
| A silent fallback or swallowed exception | Make it loud, then continue past it to what it hid |

Do not stop at: a template, a formatter, or a UI component unless every upstream value has been verified correct.

## Bad chains

- **Circular:** "why null? because the value is missing. why missing? because it is null."
- **Blame without evidence:** "why wrong? the cache is probably stale." Test it or label it a hypothesis.
- **Ends at a person:** "the author forgot." Ask what check would have caught it, and add that.
