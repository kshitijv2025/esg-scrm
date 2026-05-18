import React from "react";
import SummaryStrip from "../components/SummaryStrip";
import MetricCard from "../components/MetricCard";
import TrendChart from "../components/TrendChart";

const METRIC_LABELS = {
  energy_kwh: "Electricity (Scope 2)",
  emissions_tco2: "Total Emissions (Scope 1+2)",
  water_m3: "Water Withdrawal",
  scope3_category1: "Purchased Goods (Scope 3)",
  diesel_consumed: "Diesel Combustion (Scope 1)",
  scope3_category6: "Business Travel (Scope 3)",
};

export default function OperationsTab({
  metrics,
  trends,
  riskSummary,
  scope3Completeness,
  isLoading,
  showEvidence,
}) {
  return (
    <div>
      <div className="section-title">Live ESG Metrics — January 2025</div>

      <SummaryStrip
        riskSummary={riskSummary}
        scope3Completeness={scope3Completeness}
        metrics={metrics}
      />

      {isLoading ? (
        <div className="metrics-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="metric-card skeleton-card">
              <div className="skeleton-label" />
              <div className="skeleton-value" />
              <div className="skeleton-footer" />
            </div>
          ))}
        </div>
      ) : metrics ? (
        <div className="metrics-grid">
          {[
            "energy_kwh",
            "emissions_tco2",
            "water_m3",
            "scope3_category1",
            "diesel_consumed",
            "scope3_category6",
          ].map((key) => {
            const m = metrics.metrics[key];
            if (!m) return null;
            return (
              <MetricCard
                key={key}
                label={METRIC_LABELS[key] || key}
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
        <div className="panel-loading">Failed to load metrics</div>
      )}

      <TrendChart trends={trends} isLoading={isLoading} />
    </div>
  );
}
