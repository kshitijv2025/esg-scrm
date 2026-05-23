import React from "react";

function MetricCard({
  label,
  value,
  unit,
  confidence,
  trend,
  chainValid,
  onClick,
}) {
  const confColors = { HIGH: "#22c55e", MEDIUM: "#f59e0b", LOW: "#ef4444" };
  const isBroken = chainValid === false;
  return (
    <div
      className={`metric-card${isBroken ? " metric-card--broken" : ""}`}
      onClick={onClick}
    >
      {isBroken && (
        <div className="metric-chain-badge">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M6 1L11 6L6 11M1 6H11"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          Chain Broken
        </div>
      )}
      <div className="metric-label">{label}</div>
      <div className="metric-value">
        {value.toLocaleString()} <span className="metric-unit">{unit}</span>
      </div>
      <div className="metric-footer">
        <span
          className="confidence-badge"
          style={{ background: confColors[confidence] }}
        >
          {confidence}
        </span>
        <span className="trend">{trend}</span>
      </div>
      <div className="click-hint">Click to see evidence →</div>
    </div>
  );
}

export default MetricCard;
