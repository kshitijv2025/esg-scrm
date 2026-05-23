import React from "react";

function SummaryStrip({
  riskSummary,
  scope3Completeness,
  metrics,
  scorecard,
  navigate,
}) {
  const diesel = metrics?.clusters?.diesel_consumed;
  const dieselBroken = diesel?.chain_valid === false;

  const totalCO2e = metrics
    ? (metrics.clusters.emissions_tco2?.value || 0) +
      (metrics.clusters.scope3_category1?.value || 0) +
      (metrics.clusters.scope3_category6?.value || 0)
    : 0;

  const stripItems = [
    {
      label: "Active Risk Flags",
      value: riskSummary ? String(riskSummary.total) : "—",
      sub: riskSummary
        ? `Avg ${riskSummary.avg_days_open?.toFixed(0)}d open`
        : "",
      accent:
        (riskSummary?.by_severity?.critical || 0) > 0
          ? "red"
          : (riskSummary?.by_severity?.warning || 0) > 3
            ? "amber"
            : "green",
    },
    {
      label: "Scope 3 Completeness",
      value: scope3Completeness
        ? `${scope3Completeness.overall_coverage_pct}%`
        : "—",
      sub: scope3Completeness
        ? `${scope3Completeness.total_respondents}/${scope3Completeness.total_suppliers} responded`
        : "",
      accent:
        parseInt(scope3Completeness?.overall_coverage_pct) >= 50
          ? "green"
          : "amber",
    },
    {
      label: "Scope 1+2+3 Emissions",
      value: totalCO2e > 0 ? `${(totalCO2e / 1000).toFixed(1)}K tCO2e` : "—",
      sub: "All scopes combined",
      accent: "default",
    },
    {
      label: "Diesel Chain",
      value: diesel ? `${diesel.value} tCO2e` : "—",
      sub: dieselBroken ? "BROKEN — manual entry" : "INTACT",
      accent: dieselBroken ? "red" : "green",
    },
  ];

  const quadrantChips =
    scorecard?.quadrants?.map((q) => {
      const tierColors = { A: "#22c55e", B: "#f59e0b", C: "#ef4444" };
      const trendArrows = { up: "↑", down: "↓", stable: "→" };
      return {
        id: q.id,
        label: q.id,
        sub: q.name,
        score: q.score,
        tier: q.tier,
        tierColor: tierColors[q.tier] || "#888",
        trend: trendArrows[q.trend] || "→",
        accent: q.tier === "A" ? "green" : q.tier === "B" ? "amber" : "red",
      };
    }) || [];

  return (
    <div className="summary-strip">
      {stripItems.map((item) => (
        <div
          key={item.label}
          className={`summary-strip-card accent-${item.accent}`}
        >
          <div className="summary-strip-label">{item.label}</div>
          <div className="summary-strip-value">{item.value}</div>
          <div className="summary-strip-sub">{item.sub}</div>
        </div>
      ))}
      {quadrantChips.length > 0 && (
        <div className="quadrant-chips">
          <div className="quadrant-chips-label">Risk Quadrants</div>
          <div className="quadrant-chips-row">
            {quadrantChips.map((chip) => (
              <button
                key={chip.id}
                className={`quadrant-chip accent-${chip.accent}`}
                onClick={() =>
                  navigate && navigate(`/risk-alerts?quadrant=${chip.id}`)
                }
                title={chip.sub}
              >
                <span className="quadrant-chip-id">{chip.label}</span>
                <span className="quadrant-chip-score">{chip.score}</span>
                <span
                  className="quadrant-chip-tier"
                  style={{ color: chip.tierColor }}
                >
                  {chip.tier}
                </span>
                <span className="quadrant-chip-trend">{chip.trend}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SummaryStrip;
