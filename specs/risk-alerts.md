# Risk Alerts Specification

## Risk Score Computation

### Cluster Risk Scores (0-100)

| Cluster              | Score Basis                               | Critical Threshold        |
| -------------------- | ----------------------------------------- | ------------------------- |
| G2 Supply-Chain Risk | % suppliers with critical non-compliances | >10% = critical           |
| G5 Financial Health  | Supplier D-E ratio                        | D-E ratio >3.0 = critical |
| G8 Geopolitical      | Country risk index                        | >60 = high risk           |
| G3 Ethics/Grievance  | Open grievances / total                   | >20% open = warning       |

### Flag Priority Score

```
priority = severity_weight × cluster_weight × urgency

severity_weight: CRITICAL=3, WARNING=2, INFO=1
cluster_weight: G2=1.2, G5=1.1, G8=1.0, G3=1.0
urgency: days_overdue / 30 (capped at 2.0)
```

---

## Flag Schema

```typescript
interface RiskFlag {
  id: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  cluster: string; // e.g. "G2", "G5", "G8", "G3"
  cluster_name: string;
  supplier?: string;
  country?: string;
  title: string;
  detail: string;
  recommendation: string;
  days_overdue?: number;
  acknowledged: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
  created_at: string;
}
```

---

## Acknowledge Workflow

1. User sees flag in Risk Flags Feed
2. User clicks "Acknowledge"
3. `POST /api/risk/flags/{id}/acknowledge`
4. Flag moves from "Active" to "Acknowledged" section
5. Acknowledged flags hidden by default, viewable via filter

---

## Flag Examples

### Labour Audit Overdue (G2)

```
Severity: CRITICAL
Cluster: G2 — Supply Chain Risk
Supplier: Bangladesh Export Textiles Ltd.
Title: Labour audit overdue
Detail: 187 days since last Higg FEM audit (threshold: 90 days)
Recommendation: Suspend new purchase orders until Higg FEM audit completed.
Days overdue: 97
```

### Financial Distress (G5)

```
Severity: WARNING
Cluster: G5 — Financial Health
Supplier: Gujarat Fabricators Ltd.
Title: D/E ratio above threshold
Detail: D-E ratio of 3.4 exceeds H&M threshold of 3.0
Recommendation: Request certified financial statements for the last 2 fiscal years.
```

### Geopolitical (G8)

```
Severity: INFO
Cluster: G8 — Geopolitical Risk
Country: Vietnam
Title: Currency devaluation risk elevated
Detail: VND depreciated 4.2% against USD in past 90 days.
Recommendation: Review hedging coverage for VND-denominated payments.
```

### Grievance Resolution (G3)

```
Severity: WARNING
Cluster: G3 — Ethics/Grievance
Supplier: Mekong Garment Co.
Title: Grievance resolution overdue
Detail: 2 of 8 open grievances exceeded 30-day resolution target.
```
