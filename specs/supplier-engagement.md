# Supplier Engagement Specification

## WhatsApp Questionnaire Flow

### Current Questionnaire Template

The current WhatsApp questionnaire (`questionnaires.py:16-33`) covers:

1. Energy consumption (kWh) — required
2. Water withdrawal (m³) — required
3. Renewable energy share (%) — optional
4. Cotton/organic cotton spend ($) — optional
5. Waste recycling rate (%) — optional

### Expanded Questionnaire Scope (All Tiers)

**Tier 1 — Essential (Scope 3 completeness)**:

- Energy consumption (kWh) — required
- Water withdrawal (m³) — required
- Renewable energy share (%) — required
- Waste generated and disposition — required

**Tier 2 — Labour and Social**:

- Number of workers (headcount)
- Average wages vs. local minimum wage
- Overtime hours as % of regular hours
- Number of trade union or collective bargaining agreements
- Safety incidents (LTIFR)
- Training hours per worker

**Tier 3 — Fibre and Sourcing**:

- Fibre type breakdown (% cotton, polyester, viscose, etc.)
- Certified organic/recycled content (%)
- Country of origin of key raw materials
- Traceability level (farm-level, mill-level, country-level)

**Tier 4 — Financial and Governance**:

- Annual revenue
- Financial statements availability
- Existence of ESG policy
- Third-party ESG audit

### Coverage Stats

`GET /api/questionnaires/coverage-stats` returns:

```json
{
  "total_suppliers": 73,
  "responding_suppliers": 47,
  "total_coverage": 64.4,
  "previous_coverage": 61.2
}
```

### Coverage Calculation

```
coverage_pct = (responding_suppliers / total_suppliers) × 100
```

A supplier is "responding" when they have answered at least the required questions (Tier 1).

---

## WhatsApp Message Format

### Outbound (Platform → Supplier)

```
ESG Data Collection — H&M Supplier Platform

Bangladesh Export Textiles Ltd.,

Please share your Q1 2025 ESG data:

1. Energy: Electricity consumed? (kWh)
   Reply: [number] kWh

2. Water: Total water withdrawal? (m³)
   Reply: [number] m³

3. Workers: How many workers?
   Reply: [number]

4. Safety: Lost-time injuries this quarter?
   Reply: [number]
```

### Inbound (Supplier → Platform)

```
1. 2,450,000 kWh
2. 15,200 m³
3. 3,200
4. 2
```

### Coverage Impact Notification

```
Coverage Impact:
- Supplier: Bangladesh Export Textiles Ltd.
- Annual Spend: $4,200,000
- Coverage Added: +1.4%
- New Total: 65.8%
```
