# HIGH: Risk priority formula not matching spec — FIXED

**Type**: GAP — spec compliance
**Discovered**: 2026-05-21 redteam Round 1
**Fixed**: 2026-05-21 (same session)

## Finding

`specs/risk-alerts.md` defines:

```
priority = severity_weight × cluster_weight × urgency
severity_weight: CRITICAL=3, WARNING=2, INFO=1
cluster_weight: G2=1.2, G5=1.1, G8=1.0, G3=1.0
urgency: days_overdue / 30 (capped at 2.0)
```

`src/api/routes/risk.py` implemented: `score = base - flags * 5` (no severity/cluster/urgency weighting).

## Fix

Implemented the spec formula in `risk.py`:

- Added `SEVERITY_WEIGHTS` and `CLUSTER_WEIGHTS` constants
- Added `_escalated_severity()`: WARNING/INFO → CRITICAL after 72h (days_overdue >= 3)
- Added `_flag_priority()`: computes priority = severity_weight × cluster_weight × urgency
- Updated `_cluster_score()`: score = base - sum(flag_priorities) × 5, clamped at 0
- Updated `get_flags`, `get_risk_summary`, `get_risk_scorecard` to use new formula
- Updated `test_org_isolation.py` to use `days_overdue` parameter so org scores differ

## Verification

```bash
$ grep -n 'severity_weight\|cluster_weight\|urgency' src/api/routes/risk.py
107:SEVERITY_WEIGHTS = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
108:CLUSTER_WEIGHTS = {"G2": 1.2, "G5": 1.1, "G8": 1.0, "G3": 1.0}
109:ESCALATION_HOURS = 72
185:_escalated_severity(flag)
188:severity_weight = SEVERITY_WEIGHTS.get(severity, 1)
190:urgency = min(days_overdue / 30.0, 2.0)
$ .venv/bin/python -m pytest tests/unit/test_risk_routes.py tests/unit/test_org_isolation.py -q
47 passed
```
