import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";

// Industry benchmarks for garment manufacturing (Higg Index / SAC published data)
const BENCHMARKS = {
  energy_kwh: { label: "Energy", unit: "kWh/garment", avg: 1.2 },
  water_m3: { label: "Water", unit: "m³/garment", avg: 0.02 },
  emissions_tco2: { label: "Emissions", unit: "tCO₂e/garment", avg: 0.004 },
};

function getStatusColor(actualPerGarment, benchmark) {
  if (actualPerGarment <= benchmark) return "#22c55e"; // green — better than avg
  const pctAbove = ((actualPerGarment - benchmark) / benchmark) * 100;
  if (pctAbove <= 20) return "#f59e0b"; // amber — within 20%
  return "#ef4444"; // red — significantly above
}

function getStatusLabel(actualPerGarment, benchmark) {
  if (actualPerGarment <= benchmark) return "Better than avg";
  const pctAbove = ((actualPerGarment - benchmark) / benchmark) * 100;
  if (pctAbove <= 20) return "Within 20% of avg";
  return "Above industry avg";
}

export default function BenchmarkCard({ metrics }) {
  const [intensityData, setIntensityData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/dashboard/intensity")
      .then((r) => r.json())
      .then((d) => {
        setIntensityData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading || !intensityData) {
    return (
      <div className="panel benchmark-panel">
        <div className="benchmark-header">
          <h3>Industry Benchmark</h3>
          <p className="benchmark-subtitle">
            Garment Manufacturing — Higg Index
          </p>
        </div>
        <div className="benchmark-skeleton" />
      </div>
    );
  }

  const { production_volume, energy_kwh, emissions_tco2 } = intensityData;
  const water_m3 = metrics?.clusters?.water_m3?.value ?? null;

  // Guard against zero or missing production volume
  const vol =
    production_volume && production_volume > 0 ? production_volume : null;

  const rows = [
    {
      key: "energy_kwh",
      label: BENCHMARKS.energy_kwh.label,
      unit: BENCHMARKS.energy_kwh.unit,
      benchmark: BENCHMARKS.energy_kwh.avg,
      yourValue: vol ? energy_kwh / vol : null,
      totalValue: energy_kwh,
      totalUnit: "kWh",
    },
    {
      key: "water_m3",
      label: BENCHMARKS.water_m3.label,
      unit: BENCHMARKS.water_m3.unit,
      benchmark: BENCHMARKS.water_m3.avg,
      yourValue: vol ? water_m3 / vol : null,
      totalValue: water_m3,
      totalUnit: "m³",
    },
    {
      key: "emissions_tco2",
      label: BENCHMARKS.emissions_tco2.label,
      unit: BENCHMARKS.emissions_tco2.unit,
      benchmark: BENCHMARKS.emissions_tco2.avg,
      yourValue: vol ? emissions_tco2 / vol : null,
      totalValue: emissions_tco2,
      totalUnit: "tCO₂e",
    },
  ];

  return (
    <div className="panel benchmark-panel">
      <div className="benchmark-header">
        <div>
          <h3>Industry Benchmark</h3>
          <p className="benchmark-subtitle">
            Garment Manufacturing — Higg Index / SAC
          </p>
        </div>
        {vol && (
          <div className="benchmark-vol">
            <span className="benchmark-vol-label">Production volume</span>
            <span className="benchmark-vol-value">
              {vol.toLocaleString()} garments
            </span>
          </div>
        )}
      </div>

      <div className="benchmark-table">
        <div className="benchmark-table-head">
          <span>Metric</span>
          <span>Your value (total)</span>
          <span>Per garment</span>
          <span>Industry avg</span>
          <span>Status</span>
        </div>
        {rows.map((row) => {
          const color =
            row.yourValue != null
              ? getStatusColor(row.yourValue, row.benchmark)
              : "#6b7280";
          const statusLabel =
            row.yourValue != null
              ? getStatusLabel(row.yourValue, row.benchmark)
              : "Data unavailable";
          return (
            <div key={row.key} className="benchmark-row">
              <span className="benchmark-row-label">{row.label}</span>
              <span className="benchmark-row-total">
                {row.totalValue != null ? row.totalValue.toLocaleString() : "—"}{" "}
                {row.totalUnit}
              </span>
              <span className="benchmark-row-per" style={{ color }}>
                {row.yourValue != null ? row.yourValue.toFixed(4) : "—"}{" "}
                {row.unit}
              </span>
              <span className="benchmark-row-avg">
                {row.benchmark.toFixed(4)} {row.unit}
              </span>
              <span
                className="benchmark-status-badge"
                style={{
                  background: `${color}22`,
                  color,
                  borderColor: `${color}55`,
                }}
              >
                {statusLabel}
              </span>
            </div>
          );
        })}
      </div>

      <p className="benchmark-note">
        Benchmarks sourced from SAC Higg Index published data for garment
        manufacturing. Green = at or below industry average; Amber = within 20%
        above; Red = significantly above.
      </p>
    </div>
  );
}
