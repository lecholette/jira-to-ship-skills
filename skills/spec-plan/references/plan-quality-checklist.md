# Plan quality checklist

Run before presenting the plan. Fix failures; do not just note them.

- [ ] No TBD, "figure out later", or unresolved questions in the body
- [ ] Out of Scope section exists and is non-empty
- [ ] Each phase leaves the system working and can be verified alone
- [ ] Each phase has at least one automated criterion with an exact command
- [ ] Commands were taken from the repo (README, scripts, Makefile), not guessed
- [ ] Tests are planned in the phase that introduces the behavior, not deferred to the end
- [ ] Every AC in the ledger has a phase; every phase lists at least one AC id (`render` shows no `-`)
- [ ] Every claim about current code has a file:line
- [ ] Could anything planned be deleted or reused instead of built?
- [ ] Irreversible changes (schema, data, public API) have a specific rollback
- [ ] Top 2-3 ways this plan could fail are listed under Risks
