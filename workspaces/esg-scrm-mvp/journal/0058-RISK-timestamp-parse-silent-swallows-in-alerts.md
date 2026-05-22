# RISK: Timestamp parse errors silently swallowed in alerts.py

## Finding

**File**: `src/realtime/alerts.py:69`

**Code**:

```python
def _should_escalate(timestamp: str, severity: str) -> tuple[bool, str]:
    try:
        # ... timestamp parsing ...
    except Exception:
        return False, severity  # silently swallows ALL errors
```

**Problem**: Malformed `timestamp` strings from user input or DB corruption cause the function to return the default severity without any diagnostic trace. This is the same class as CRITICAL 5 (`except: pass`) but in a different code path.

**Severity**: HIGH — escalation logic silently falls through, untrusted input not logged.

## Fix Applied

```python
except Exception:
    logging.getLogger("alerts").debug(
        "alerts.escalate.parse_error", timestamp=timestamp, severity=severity
    )
    return False, severity
```

Level: DEBUG — malformed timestamps are expected/ordinary user input, not operational incidents. The fallback behavior is correct; the logging makes it auditable.

## Verification

```bash
grep -n "except Exception" src/realtime/alerts.py
# Line 69 now has logging; line 103 is AlertBus.broadcast cleanup (acceptable per rules)
```

## Related

- CRITICAL 5: `except json.JSONDecodeError: pass` in ws_alerts_endpoint (already fixed, same class)
- Zero-tolerance Rule 3: no silent error hiding
