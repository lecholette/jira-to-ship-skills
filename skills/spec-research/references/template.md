# Findings document template

```markdown
---
date: <ISO timestamp>
git_commit: <short hash or omit>
branch: <branch or omit>
repository: <name>
topic: "<question>"
status: complete
---

# Research: <topic>

## Question
<original question, verbatim>

## Summary
<direct answer, 3-8 lines>

## Detailed Findings
### <Area 1>
- <finding> (`path/to/file.ext:42`)
- <how it connects to other areas>

### <Area 2>
...

## Code References
- `path/file.ext:123` - what is there
- `other/file.ext:45-67` - what the block does

## Architecture Notes
<patterns, conventions, and constraints observed; no recommendations>

## Prior Art
<existing docs, ADRs, earlier related research, with paths>

## Acceptance Criteria Map
| AC | Code areas | Existing tests | Gap / question |
|----|-----------|----------------|----------------|

## Open Questions
<what could not be verified, and what would resolve it>
```

Keep Detailed Findings to what answers the question. Cut tangents into Open Questions.
