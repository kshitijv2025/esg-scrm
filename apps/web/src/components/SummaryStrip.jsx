import React from "react";

function SummaryStrip({ riskSummary, scope3Completeness, metrics }) {
  const diesel = metrics?.metrics?.diesel_consumed;
  const dieselBroken = diesel?.chain_valid === false;

  const totalCO2e = metrics
    ? (metrics.metrics.emissions_tco2?.value || 0) +
      (metrics.metrics.scope3_category1?.value || 0) +
      (metrics.metrics.scope3_category6?.value || 0)
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
    </div>
  );
}

export default SummaryStrip;
