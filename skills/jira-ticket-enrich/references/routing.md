# Routing

Signals, strongest first:

1. **Component field.** Usually maps directly to an owning team.
2. **Similar-ticket history.** `text ~ "<terms>" AND status in (Done, Closed) ORDER BY updated DESC`, max 10. Note which project, team, and assignee resolved them.
3. **Routing config** (`.jira-enrich/routing.yaml`, optional). See format below.
4. **Code ownership** (deep mode): CODEOWNERS entries and recent git authors for the located files.
5. **Explicit mentions** of a team or system in the ticket.

Output: team, project, confidence, the top alternative and why it lost. Suggest an individual assignee only with strong history; otherwise route to the team's triage queue. Confirm the target project exists before proposing a move.

## Config format

```yaml
teams:
  - name: Payments
    project: PAY
    components: ["Billing", "Checkout"]
    keywords: ["invoice", "refund", "card"]
    triage_assignee: null
disambiguation:
  - when_all: ["policy"]
    if_any: ["invoice", "refund", "charge"]
    route_to: Billing
  - when_all: ["policy"]
    if_any: ["login", "password", "sso"]
    route_to: Identity
```

Apply `disambiguation` rules before keyword matching. With no config, say routing is based on components and history only.
