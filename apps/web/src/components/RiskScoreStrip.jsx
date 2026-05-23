import React from "react";
import { useNavigate } from "react-router-dom";

const CLUSTER_CONFIG = {
  G2: {
    label: "G2",
    title: "Supply Chain",
    accent: "accent-red",
    color: "#ef4444",
  },
  G3: {
    label: "G3",
    title: "Grievances",
    accent: "accent-amber",
    color: "#f59e0b",
  },
  G8: {
    label: "G8",
    title: "Geopolitical",
    accent: "accent-amber",
    color: "#f59e0b",
  },
  G5: {
    label: "G5",
    title: "Financial",
    accent: "accent-green",
    color: "#22c55e",
  },
};

export default function RiskScoreStrip({ riskSummary, scorecard }) {
  const navigate = useNavigate();

  if (!riskSummary && !scorecard) {
    return (
      <div className="risk-score-strip">
        <div className="risk-score-strip-skeleton">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="risk-score-chip-skeleton" />
          ))}
        </div>
      </div>
    );
  }

  const chips = [
    {
      key: "G2",
      count:
        riskSummary?.g2_suppliers_at_risk ??
        scorecard?.quadrants?.find((q) => q.id === "G2")?.active_flags ??
        0,
      ...CLUSTER_CONFIG.G2,
    },
    {
      key: "G3",
      count:
        riskSummary?.g3_grievances ??
        scorecard?.quadrants?.find((q) => q.id === "G3")?.active_flags ??
        0,
      ...CLUSTER_CONFIG.G3,
    },
    {
      key: "G8",
      count:
        riskSummary?.g8_geopolitical ??
        scorecard?.quadrants?.find((q) => q.id === "G8")?.active_flags ??
        0,
      ...CLUSTER_CONFIG.G8,
    },
    {
      key: "G5",
      count:
        riskSummary?.g5_financial ??
        scorecard?.quadrants?.find((q) => q.id === "G5")?.active_flags ??
        0,
      ...CLUSTER_CONFIG.G5,
    },
  ];

  function handleChipClick(quadrant) {
    navigate(`/risk-alerts?quadrant=${quadrant}`);
  }

  return (
    <div className="risk-score-strip">
      <div className="risk-score-strip-label">Risk Overview</div>
      <div className="risk-score-strip-chips">
        {chips.map((chip) => (
          <button
            key={chip.key}
            className={`risk-score-chip ${chip.accent}`}
            onClick={() => handleChipClick(chip.key)}
            style={{ "--chip-color": chip.color }}
          >
            <span className="risk-chip-id">{chip.label}</span>
            <span className="risk-chip-title">{chip.title}</span>
            <span className="risk-chip-count">{chip.count}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
