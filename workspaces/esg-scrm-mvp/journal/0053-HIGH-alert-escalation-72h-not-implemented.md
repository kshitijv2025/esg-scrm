# HIGH: Alert severity escalation after 72h not implemented — FIXED

**Type**: GAP — spec compliance
**Discovered**: 2026-05-21 redteam Round 1
**Fixed**: 2026-05-21 (same session)

## Finding

`specs/risk-alerts.md` § "Alert Severity Escalation" defines:

> "Alert severity escalation: WARNING/INFO → CRITICAL after 72h."

`days_overdue` was stored and returned in API responses, but no automatic escalation logic existed.

## Fix

Implemented `_escalated_severity()` in `risk.py`:

- WARNING/INFO with `days_overdue >= 3` (72h) escalates to CRITICAL
- Applied in `get_flags` (returned severity field uses escalated value)
- Applied in `_flag_priority` (escalated severity used for priority calculation)

## Verification

```bash
$ grep -n 'escalat\|72.*hour' src/api/routes/risk.py
183:def _escalated_severity(flag: dict) -> str:
185:    if days_overdue >= 3 and severity in ("WARNING", "INFO"):
$ .venv/bin/python -m pytest tests/unit/test_risk_routes.py tests/unit/test_org_isolation.py -q
47 passed
```
