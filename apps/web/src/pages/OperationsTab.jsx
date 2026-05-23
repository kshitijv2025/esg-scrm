import React from "react";
import SummaryStrip from "../components/SummaryStrip";
import MetricCard from "../components/MetricCard";
import TrendChart from "../components/TrendChart";
import BenchmarkCard from "../components/BenchmarkCard";
import RiskScoreStrip from "../components/RiskScoreStrip";

/** Available ESG clusters returned by /dashboard/operations-summary */
const CLUSTER_KEYS = [
  "energy_kwh", // E1 — Energy
  "water_m3", // G6 — Water
  "emissions_tco2", // E2 — Total Emissions (Scope 1+2)
  "scope3_category1", // E4 — Scope 3 Purchased Goods
  "scope3_category6", // E4 — Scope 3 Business Travel
  "diesel_consumed", // E1 — Diesel Combustion (Scope 1)
];

const CLUSTER_LABELS = {
  energy_kwh: "E1 — Energy",
  water_m3: "G6 — Water",
  emissions_tco2: "E2 — Total Emissions",
  scope3_category1: "E4 — Scope 3 (Goods)",
  scope3_category6: "E4 — Scope 3 (Travel)",
  diesel_consumed: "E1 — Diesel Combustion",
};

export default function OperationsTab({
  metrics,
  trends,
  riskSummary,
  scope3Completeness,
  isLoading,
  showEvidence,
  scorecard,
}) {
  return (
    <div>
      <div className="section-title">
        Live ESG Metrics —{" "}
        {new Date().toLocaleDateString("en-US", {
          month: "long",
          year: "numeric",
        })}
      </div>

      <SummaryStrip
        riskSummary={riskSummary}
        scope3Completeness={scope3Completeness}
        metrics={metrics}
      />

      {isLoading ? (
        <div className="metrics-grid">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="metric-card skeleton-card">
              <div className="skeleton-label" />
              <div className="skeleton-value" />
              <div className="skeleton-footer" />
            </div>
          ))}
        </div>
      ) : metrics ? (
        metrics.clusters && Object.keys(metrics.clusters).length > 0 ? (
          <div className="metrics-grid">
            {CLUSTER_KEYS.map((key) => {
              const m = metrics.clusters ? metrics.clusters[key] : null;
              if (!m) return null;
              return (
                <MetricCard
                  key={key}
                  label={CLUSTER_LABELS[key] || key}
                  value={m.value}
                  unit={m.unit}
                  confidence={m.confidence}
                  trend={m.trend}
                  chainValid={m.chain_valid}
                  onClick={() => showEvidence(key)}
                />
              );
            })}
          </div>
        ) : (
          <div className="panel-loading">
            No live data — MQTT meters and SAP integrations not connected
          </div>
        )
      ) : (
        <div className="panel-loading">Failed to load metrics</div>
      )}

      <TrendChart trends={trends} isLoading={isLoading} />

      <RiskScoreStrip riskSummary={riskSummary} scorecard={scorecard} />

      <BenchmarkCard metrics={metrics} />
    </div>
  );
}
