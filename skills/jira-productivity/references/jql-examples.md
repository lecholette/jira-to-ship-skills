# JQL examples

Replace placeholders: `<PROJECT>` project key, `<TEAM_LABEL>` team label or component, `<START>`/`<END>` dates (`YYYY-MM-DD`), `<ASSIGNEE>` account id or name (only for per-person views the user asked for). Always request changelog expansion for cycle time. Quote status names that contain spaces.

## Contents

- [Period pulls](#period-pulls)
- [Drill-downs](#drill-downs)
- [Field notes](#field-notes)
- [Tips](#tips)

## Period pulls

Resolved in the window (throughput, lead and cycle time):

```jql
project = <PROJECT> AND resolutiondate >= "<START>" AND resolutiondate <= "<END>"
```

Created in the window (intake mix):

```jql
project = <PROJECT> AND created >= "<START>" AND created <= "<END>"
```

Team scope by label or component:

```jql
project = <PROJECT> AND labels = <TEAM_LABEL> AND resolutiondate >= "<START>" AND resolutiondate <= "<END>"
```

```jql
project = <PROJECT> AND component = "<COMPONENT>" AND updated >= "<START>"
```

Work in flight at the end of the window:

```jql
project = <PROJECT> AND status in ("In Progress", "In Review") AND created <= "<END>"
```

## Drill-downs

Blocked now or in the window:

```jql
project = <PROJECT> AND (status = Blocked OR labels in (blocked)) AND updated >= "<START>"
```

```jql
project = <PROJECT> AND status was Blocked DURING ("<START>", "<END>")
```

Bug load:

```jql
project = <PROJECT> AND issuetype = Bug AND created >= "<START>" AND created <= "<END>"
```

Reopened work:

```jql
project = <PROJECT> AND status changed from Done to "To Do" DURING ("<START>", "<END>")
```

Long-running open items:

```jql
project = <PROJECT> AND statusCategory = "In Progress" AND created <= "<START>"
```

Sprint scope (if the project uses sprints):

```jql
project = <PROJECT> AND sprint = "<SPRINT NAME>"
```

```jql
project = <PROJECT> AND sprint in closedSprints() AND resolutiondate >= "<START>"
```

Epic spread:

```jql
project = <PROJECT> AND "Epic Link" is not EMPTY AND resolutiondate >= "<START>"
```

One person, only when requested:

```jql
assignee = "<ASSIGNEE>" AND resolutiondate >= "<START>" AND resolutiondate <= "<END>"
```

## Field notes

- Story points: often `customfield_10016` on cloud sites, but it varies. Find yours in a sample issue JSON and pass `--points-field`.
- Epic: `parent.key` on next-gen and recent cloud projects; `customfield_10014` ("Epic Link") on older ones. Pass `--epic-field` if needed.
- Changelog: request `expand=changelog` (or the equivalent option in the connected tool). Status transitions drive cycle time and blocked days.
- Status names are workflow specific: confirm "In Progress" and "Blocked" spellings.

## Tips

- Use `resolutiondate` for throughput and `created` for intake; mixing them in one comparison misleads.
- Page large results (50 to 100 per call) and merge the JSON.
- Test a JQL with a small `maxResults` first, then expand.
- `DURING` and `was` clauses need the history index; they can be slow on large projects.
