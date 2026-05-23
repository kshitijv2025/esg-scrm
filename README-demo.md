# ESG+SCRM — Investor Demo

## What this is

A working demo of the ESG+SCRM platform for a Bangladesh garment factory.
Shows the four investor-validated features without any real customer data.

**Demo company:** Bangladesh Export Textiles Ltd. (3,200 employees, $42M annual orders from H&M)

## Quick Start

```bash
# Run once to set up
./demo.sh

# Terminal 1 — Backend
source .venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd apps/web && npm run dev
```

Open **http://localhost:5173**

---

## What investors see

### 1. Live Dashboard

Real KPIs for a Bangladesh factory — electricity, emissions, water, Scope 3.
Every number tagged with HIGH/MEDIUM/LOW confidence.

**Click any KPI card** → Evidence drill-down shows:

- Source system (SAP Business One)
- Source record ID (invoice number)
- Emission factor with version (IEA 2023, Table 4.2)
- SHA-256 hash chain for tamper detection
- Chain integrity status ✓

### 2. Framework Comparison

Same meter reading → CSRD / ISSB / GRI / TCFD labels.
One data entry, multiple framework outputs automatically.

### 3. WhatsApp Supplier Engagement

What a supplier sees when they receive the ESG questionnaire.
Supplier responds via WhatsApp in seconds.
Coverage tracking: 64% of procurement spend covered.

---

## Tech Stack

- **Backend:** FastAPI (Python) — mock data, real API shape
- **Frontend:** React + Vite + Recharts
- **No real integrations** — all data is realistic demo data

## What to say to investors

> "This is what the platform looks like. Every number has an audit trail.
> Here's a real factory — 3,200 employees, $42M in annual orders from H&M.
> Here's the evidence behind each number. Here's how it maps across frameworks.
> Here's how a supplier responds on WhatsApp."

---

## File Structure

```
src/api/
  main.py              # FastAPI app
  routes/
    dashboard.py        # Live KPI endpoints
    evidence.py        # Evidence chain endpoints
    frameworks.py      # Framework mapping endpoint
    questionnaires.py  # WhatsApp questionnaire endpoints
    suppliers.py       # Supplier list endpoint

apps/web/
  src/
    App.jsx            # React dashboard (3 tabs)
    styles.css         # Dark theme
  package.json
  vite.config.js

demo.sh               # One-time setup
README-demo.md         # This file
```
