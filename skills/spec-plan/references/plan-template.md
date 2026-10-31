# Plan template

```markdown
---
status: draft            # draft | approved | in-progress | complete
date: <ISO date>
source: <ticket key or path>
---

# <Feature> Implementation Plan

## Overview
<1-2 sentences: what and why>

## Current State
<what exists, what is missing, constraints; cite file:line>

### Key Discoveries
- <finding> (`path:line`)

## Desired End State
<observable result and how to verify it>

## Out of Scope
- <explicit non-goals>

## Approach
<chosen strategy and why; alternatives rejected>

## Phase 1: <name>
### Overview
<what this phase achieves; system works after it>
### Acceptance Criteria Satisfied
- AC-1, AC-3 (ids from docs/specs/<id>/acceptance.json)
### Changes
- `path/to/file`: <summary of change>
### Tests
First step: acceptance test(s) for the ACs above, observed RED.
<tests written first in this phase and what they assert>
### Success Criteria
#### Automated
- [ ] Tests pass: `<exact command>`
- [ ] Lint / types pass: `<exact command>`
#### Manual
- [ ] <concrete step and expected result>

## Phase 2: <name>
...

## Testing Strategy
<unit, integration, end-to-end; key edge cases>

## Migration / Rollback
<only if schema, data, or public API changes: sequencing, backfill, specific rollback steps>

## Risks
- <risk>: <mitigation>

## References
- Ticket: <key or path>
- Research: <path>
- Similar implementation: `path:line`
```
