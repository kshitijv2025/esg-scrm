# SAP B1 Configuration Guide

This document describes how to configure the SAP Business One Service Layer integration in the ESG SCRM platform.

## Environment Variables

| Variable            | Required           | Default   | Description                                                                   |
| ------------------- | ------------------ | --------- | ----------------------------------------------------------------------------- |
| `ERP_MODE`          | No                 | `demo`    | Operating mode: `demo` (CSV-backed) or `live` (SAP B1 Service Layer)          |
| `SAP_B1_SERVER_URL` | Yes (live)         | _(empty)_ | Base URL of the SAP B1 Service Layer, e.g. `https://sap-b1.example.com:50000` |
| `SAP_B1_API_KEY`    | Recommended (live) | _(empty)_ | API key for Service Layer authentication                                      |

## Operating Modes

### Demo Mode (Default)

When `ERP_MODE` is not set, or is set to anything other than `live`, the adapter reads data from local CSV files (`data/operations/summary.csv`). No SAP B1 server is required. This is the default for local development and demos.

```
ERP_MODE=demo        # default — uses CSV files
# (or simply omit ERP_MODE)
```

**Demo mode behavior:**

- `health_check()` returns `{"mode": "demo", "connected": True, "source": "CSV files"}`
- All data methods (`get_utility_invoices`, etc.) return CSV-backed demo data
- No network connections are made

### Live Mode

Set `ERP_MODE=live` to activate real SAP B1 Service Layer connectivity.

```bash
ERP_MODE=live
SAP_B1_SERVER_URL=https://sap-b1.example.com:50000
SAP_B1_API_KEY=your-api-key-here
```

**Live mode behavior:**

- `health_check()` makes an HTTP GET to `{SAP_B1_SERVER_URL}/Health`
- All data methods call the actual SAP B1 REST API
- Authentication uses the `APIKey` header

## Authentication

### API Key Authentication (Recommended)

The SAP B1 Service Layer supports API key authentication. Pass your key via the `SAP_B1_API_KEY` environment variable:

```bash
SAP_B1_API_KEY=your-service-layer-api-key
```

The adapter sends the key as the `APIKey` HTTP header on every request.

### OAuth / Session-Based Authentication

If your SAP B1 Service Layer uses OAuth 2.0 or session-based authentication, override the `SAPBusinessOneAdapter` class or extend `_live_call` to inject the appropriate Bearer token or session cookie.

### Network Requirements

- The application host must be able to reach `SAP_B1_SERVER_URL` on the configured port (default `50000`)
- A 10-second timeout applies to the health check; a 15-second timeout applies to data requests
- Both HTTPS (TLS) and HTTP are supported — use HTTPS in production

## Error Codes and Troubleshooting

### Health Check Error Responses

When `ERP_MODE=live`, `health_check()` may return these error shapes:

| Condition                   | `connected` | `error` field                            | Cause                                      |
| --------------------------- | ----------- | ---------------------------------------- | ------------------------------------------ |
| `SAP_B1_SERVER_URL` not set | `False`     | `"SAP_B1_SERVER_URL not configured"`     | Variable is empty or missing               |
| HTTP 401                    | `False`     | `"authentication_failed (401)"`          | Invalid or missing API key                 |
| HTTP 403                    | `False`     | `"authentication_failed (403)"`          | Valid key but insufficient permissions     |
| Connection refused          | `False`     | `"connection_failed"`                    | Server unreachable (wrong URL or firewall) |
| Request timeout             | `False`     | `"connection_timeout"`                   | Server did not respond within 10 seconds   |
| Unexpected error            | `False`     | `"health_check_failed: <ExceptionType>"` | Unhandled exception (check server logs)    |

### Data Method Error Handling

All data methods (`get_utility_invoices`, `get_inventory_items`, etc.) return an empty list `[]` on any live-mode failure. Errors are logged at WARNING level with the endpoint name and error type.

If `get_utility_invoices()` returns an empty list in live mode:

1. Check that `SAP_B1_SERVER_URL` is reachable from the application host
2. Verify the API key is valid and has `ServiceLayer` access
3. Check application logs for `sap_b1.auth_failed` or `sap_b1.connection_failed` entries

### Common Issues

**`connection_failed` immediately on startup**

- Verify `SAP_B1_SERVER_URL` is correct and the host is reachable: `curl -k https://sap-b1.example.com:50000/Health`
- Check that the SAP B1 Service Layer service is running on the target server

**`authentication_failed (401)` despite valid key**

- Confirm the API key has not expired or been rotated in the SAP B1 Admin Console
- Ensure the key is scoped to the Service Layer (not just the UI)

**`authentication_failed (403)` with a valid key**

- The key exists but lacks the required permissions. Assign the `ServiceLayerUser` (or equivalent) role to the API key in SAP B1.

**Works in demo mode, fails in live mode**

- Confirm `ERP_MODE=live` is set and the application has been restarted after changing the variable
- Check that `SAP_B1_API_KEY` is set — without it, requests are sent without authentication and may be rejected

## Example `.env` Entries

```bash
# Development / demo (CSV mode — no SAP B1 server needed)
ERP_MODE=demo

# Staging / production (live SAP B1)
ERP_MODE=live
SAP_B1_SERVER_URL=https://sap-b1-staging.example.com:50000
SAP_B1_API_KEY=sl_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Health Check in the API Dashboard

The `/api/health` endpoint includes the SAP B1 adapter status under the `components` key when `ERP_MODE=live`. A healthy integration shows:

```json
{
  "status": "ok",
  "version": "0.2.0",
  "components": {
    "database": "healthy",
    "sap_b1": "healthy"
  },
  "checks": {
    "sap_b1_connected": true,
    "db_connection": true,
    "disk_space": true
  }
}
```

If SAP B1 is unhealthy or unreachable, `sap_b1` will be `"degraded"` or absent.
