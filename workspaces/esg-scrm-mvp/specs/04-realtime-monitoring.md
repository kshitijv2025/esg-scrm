# Spec 04: Real-Time ESG Monitoring

## What This Module Does

Reads existing IoT sensor data through ERP integration, displays live sustainability metrics on a dashboard, and sends threshold alerts when emissions, energy, or water usage exceed defined limits.

## The IoT Reality Check

Mid-market export manufacturers have more IoT infrastructure than most people assume:

| Industry        | Sensors Already Present                                                              | Data Access                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| Garment factory | Smart energy meters, water flow meters, ETP sensors, PLC-controlled production lines | Energy meters → utility bills or modbus. Water meters → ETP daily logs. PLC → production tracking via SCADA |
| Pharma          | Environmental monitoring (temperature, humidity), flow meters, utility monitors      | 21 CFR Part 11 compliant data loggers. Often already integrated to ERP                                      |
| Auto parts      | CNC machine monitoring, energy meters, coolant systems                               | OPC-UA available on some machines. Energy data in ERP                                                       |

The platform does NOT install sensors. It reads existing sensor data through whatever integration path is available.

## Data Architecture

### Integration Paths (Priority Order)

```
Priority 1: Through ERP Integration (easiest)
ERP System (SAP, NetSuite, Xero)
    ↓
Connector reads utility invoices / meter readings
    ↓
Frequency: Hourly batch from ERP (not real-time, but frequent)
    ↓
DataPoint created with timestamp of meter reading

Priority 2: Direct Sensor Integration (harder)
IoT Gateway (existing PLC, SCADA, OPC-UA server)
    ↓
Platform IoT Adapter reads via Modbus/OPC-UA
    ↓
Real-time streaming (every 1-15 minutes)
    ↓
DataPoint created with sensor timestamp

Priority 3: Manual Data Entry (last resort)
Mobile app or web form
    ↓
Operator enters meter readings manually
    ↓
Frequency: Daily at best
    ↓
DataPoint created with manual entry timestamp
```

### Streaming vs Batch

| Approach                      | Frequency            | Infrastructure Required           | MVP Viable?             |
| ----------------------------- | -------------------- | --------------------------------- | ----------------------- |
| ERP batch (Priority 1)        | Hourly               | Just the ERP connector            | **Yes — MVP uses this** |
| SCADA/PLC direct (Priority 2) | Real-time (1-15 min) | OPC-UA or Modbus adapter per site | Later                   |
| IoT Gateway (Priority 3)      | Real-time            | Dedicated IoT gateway hardware    | Later                   |
| Manual entry                  | Daily                | None                              | Fallback only           |

**MVP decision:** Use ERP batch (Priority 1) as the real-time data source. This means "real-time" for MVP = hourly updates from ERP, not seconds-level streaming. This is sufficient for mid-market use cases.

## Dashboard

### Metrics Displayed

| Metric                           | Update Frequency | Source                                    | Display                   |
| -------------------------------- | ---------------- | ----------------------------------------- | ------------------------- |
| Total energy consumed (kWh)      | Hourly           | ERP utility invoices                      | Live counter + trend line |
| Total CO2 emissions (tCO2e)      | Hourly           | Calculated from energy × grid factor      | Live counter + trend line |
| Water consumption (m³)           | Hourly           | ERP water invoices                        | Live counter + trend line |
| Emissions intensity (tCO2e/unit) | Daily            | Calculated: emissions ÷ production volume | Benchmark comparison      |
| Alert count                      | Real-time        | Alert system                              | Badge count + list        |

### Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Org Logo]  Real-Time ESG Command Center          [Settings]   │
├─────────────────────────────────────────────────────────────────┤
│  Energy          Emissions          Water           Alerts       │
│  12,450 kWh      8,230 tCO2e      4,120 m³       3 ⚠️         │
│  ▲ 4% vs yesterday  ▲ 2% vs yesterday  ▼ 1% vs yesterday       │
├─────────────────────────────────────────────────────────────────┤
│  [Energy Trend - 7 day line chart]                             │
│                                                                 │
│  [Emissions by Source - stacked bar chart]                      │
│                                                                 │
│  [Alert Feed - real-time scroll]                                │
│                                                                 │
│  [Framework Compliance Status]                                   │
│  CSRD: ████████░░ 80%     ISSB: ██████░░░░ 60%              │
└─────────────────────────────────────────────────────────────────┘
```

### Alert Fatigue Prevention

**Problem:** A plant with 47 sensors triggering alerts on every threshold breach creates noise that operations managers stop reading.

**Solutions:**

1. **Aggregate alerts first:** Don't alert on every sensor reading. Alert on daily aggregates ("Plant X exceeded daily emissions target")
2. **Smart thresholds:** Start with wide thresholds (3 standard deviations). Narrow only if data quality is proven
3. **Alert grouping:** Multiple breaches in same category → one digest, not 47 individual messages
4. **Escalation ladder:** Day 1: dashboard badge. Day 3: email. Day 7: WhatsApp to operations manager

```python
# Alert aggregation logic
class AlertAggregator:
    def should_send(self, alert_event: AlertEvent) → bool:
        # Only send if:
        # 1. Threshold breached for 3 consecutive periods (not one-off spike)
        # 2. OR breach exceeds 2x threshold (significant event)
        # 3. Or daily digest time (batch alerts)
```

## Threshold Alerts

### Alert Definition

```python
class ThresholdAlert:
    id: UUID
    organization_id: UUID
    metric_type: ENUM(energy_kwh, emissions_tco2, water_m3)

    # Threshold
    threshold_value: Decimal
    threshold_unit: str
    comparison: ENUM(gt, lt, gte, lte, eq)  # gt = > threshold_value triggers alert

    # Scope
    scope: ENUM(daily_total, hourly_total, per_unit, per_shift)
    entity_filter: dict | null  # e.g., {"factory_id": "Plant-A"}

    # Notification
    notification_channel: ENUM(dashboard, email, whatsapp, all)
    recipient_emails: str[]
    recipient_whatsapp: str

    # Alert fatigue settings
    consecutive_periods_before_alert: int  # Default: 3
    grouping_window_minutes: int           # Default: 60

    active: bool
    created_at: timestamp
```

### Alert Lifecycle

```
Sensor reading received
    ↓
Check against all active ThresholdAlerts
    ↓
If threshold breached for N consecutive periods
    → Create AlertEvent
    → Determine notification channel
    → Send (WhatsApp / email / dashboard badge)
    → Wait for acknowledgment
    ↓
If no acknowledgment in 24 hours
    → Escalate to next level
    → Notify backup contact
```

### Alert Actions

| Alert Type                             | Immediate Action               | Follow-Up Action           |
| -------------------------------------- | ------------------------------ | -------------------------- |
| Emissions spike (>20% above target)    | WhatsApp to Operations Manager | Open investigation ticket  |
| Energy spike (>30% above baseline)     | Dashboard badge                | Schedule maintenance check |
| Water anomaly (>2x normal consumption) | Email + dashboard              | ETP operator check         |
| No data received (sensor offline)      | Dashboard warning              | IT ticket to check meter   |

## Real-Time Data Pipeline

### MVP Architecture (Hourly Batch)

```
ERP System
    ↓ (hourly via connector)
Integration Queue (SQS / Kafka)
    ↓
Normalize → Create DataPoint
    ↓
Evidence Record created (with chain hash)
    ↓
Dashboard refresh (polling or WebSocket push)
    ↓
Alert evaluation
```

### Post-MVP Architecture (Real-Time Streaming)

```
IoT Gateway (OPC-UA / Modbus)
    ↓ (every 1-5 minutes)
Edge Processor (filter, aggregate)
    ↓ (MQTT or HTTP)
Platform Streaming API
    ↓
Real-Time Pipeline (Kafka)
    ↓
Instant DataPoint creation
    ↓
Live dashboard (WebSocket)
    ↓
Real-time alert evaluation
```

## Integration with Other Features

### With Evidence Vault

- Every real-time DataPoint generates an EvidenceRecord
- Real-time data has same confidence tagging as batch data
- Audit trail is continuous, not just at reporting time

### With Data Orchestration

- Same ERP connector used for both batch reporting and real-time monitoring
- Real-time is a higher-frequency view of the same data pipeline
- No additional ERP integration work for Feature 4 if Feature 1 is done

### With Supplier Collection

- Real-time monitoring shows SCOPE 3 emissions from suppliers
- If supplier misses reporting deadline → real-time Scope 3 drops → alert triggered

## Brief Traceability

| Brief Requirement                                   | Spec Section                                          |
| --------------------------------------------------- | ----------------------------------------------------- |
| "Read existing sensor data through ERP integration" | Integration Paths (Priority Order), Data Architecture |
| "No new hardware required"                          | The IoT Reality Check, Integration Paths              |
| "Live emissions, energy, water dashboard"           | Dashboard section, Metrics Displayed table            |
| "Threshold alerts"                                  | Threshold Alerts section, Alert Definition            |
| "Mid-market already have smart meters / PLC / BMS"  | The IoT Reality Check table                           |
| "Real-time alongside compliance data"               | Dashboard Layout, Integration with Other Features     |
| "Higher-frequency data pull than batch reporting"   | Streaming vs Batch, MVP vs Post-MVP Architecture      |
| "Alert fatigue prevention"                          | Alert Fatigue Prevention section                      |
| "Alert escalation ladder"                           | Alert Lifecycle                                       |
