# Enrichment JSON

Required fields marked * (the `//` comments below are annotations; real JSON has none).

```json
{
  "key": "ABC-123",                         // *
  "type": {"value": "BUG", "confidence": 90, "evidence": "quote"},   // *
  "readiness": {                             // *
    "percent": 60,
    "missing": ["Environment", "Expected result"],
    "questions_for_reporter": ["Which app version?"]
  },
  "impact": {                                // *
    "severity": "Major",
    "urgency": "Customer escalation",
    "current_priority": "Medium",
    "suggested_priority": "High",
    "path": "Major severity + named customer",
    "evidence": "quote"
  },
  "reproduction": {"approach": "TEST", "steps": [], "expected": "", "actual": "", "environment": "", "blockers": []},
  "acceptance_criteria": ["Given ... When ... Then ..."],
  "code_areas": [{"path": "src/x.py", "lines": "40-70", "note": ""}],
  "linked_work": [{"type": "PR", "ref": "org/repo#412", "state": "merged", "date": "2026-10-02", "note": ""}],
  "duplicates": [{"key": "ABC-77", "reason": ""}],
  "routing": {"team": "", "project": "", "confidence": 80, "alternative": "", "reasoning": ""},
  "size_signals": ["touches 3 services", "needs schema change"]
}
```

Bugs require `reproduction` and should lead `acceptance_criteria` with a Given/When/Then regression criterion. Features and tasks require `acceptance_criteria`. Each criterion needs an observable Then; otherwise list it under `questions_for_reporter`. `code_areas` appears only when deep mode ran.
