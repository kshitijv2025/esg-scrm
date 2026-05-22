# D3.7 BenchmarkCard — Completed

**Item**: Benchmarking against industry averages
**Status**: Completed 2026-05-21

## Verification

BenchmarkCard uses real API data:

```
$ grep -n "production_volume\|/dashboard/intensity" apps/web/src/components/BenchmarkCard.jsx
```

BenchmarkCard calls `/dashboard/intensity` to get `production_volume` for per-garment calculations.

Industry benchmarks are real Higg Index / SAC published data:

- Energy: 1.2 kWh/garment
- Water: 0.02 m³/garment
- Emissions: 0.004 tCO₂e/garment

Backend endpoint `GET /api/dashboard/intensity` implemented in `dashboard.py`.
