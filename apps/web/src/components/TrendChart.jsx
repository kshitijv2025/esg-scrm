import React from "react";

export default function TrendChart({ trends, isLoading }) {
  if (isLoading || !trends) {
    return (
      <div className="panel trend-panel">
        <div className="trend-header">
          <div>
            <h3>5-Month ESG Trend</h3>
            <p className="trend-subtitle">Energy · Emissions · Water · Waste</p>
          </div>
          <div className="trend-legend-custom">
            <span className="legend-dot energy" />
            Energy
            <span className="legend-dot emissions" />
            Emissions
            <span className="legend-dot water" />
            Water
            <span className="legend-dot waste" />
            Waste
            <span className="legend-dot incident" />
            Incident Rate
          </div>
        </div>
        <div className="skeleton-chart" />
      </div>
    );
  }

  // SVG line chart — avoids Recharts crash
  const W = 600,
    H = 180,
    PADDING = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartW = W - PADDING.left - PADDING.right;
  const chartH = H - PADDING.top - PADDING.bottom;

  const months = trends.map((t) => t.month);
  const n = months.length;

  const maxEnergy = Math.max(...trends.map((t) => t.energy));
  const maxEmissions = Math.max(...trends.map((t) => t.emissions));
  const maxWater = Math.max(...trends.map((t) => t.water));
  const maxWaste = Math.max(...trends.map((t) => t.waste));
  const maxRight = Math.max(maxEmissions, maxWater, maxWaste); // shared right axis for emissions + water + waste
  const maxIncident = Math.max(...trends.map((t) => t.incident_rate));

  const xOf = (i) => PADDING.left + (i / (n - 1)) * chartW;
  const yLeft = (v) => PADDING.top + chartH - (v / maxEnergy) * chartH; // energy → left axis
  const yRight = (v) => PADDING.top + chartH - (v / maxRight) * chartH; // emissions + water → right axis

  const energyPts = trends
    .map((t, i) => `${xOf(i)},${yLeft(t.energy)}`)
    .join(" ");
  const emissionsPts = trends
    .map((t, i) => `${xOf(i)},${yRight(t.emissions)}`)
    .join(" ");
  const waterPts = trends
    .map((t, i) => `${xOf(i)},${yRight(t.water)}`)
    .join(" ");
  const wastePts = trends
    .map((t, i) => `${xOf(i)},${yRight(t.waste)}`)
    .join(" ");

  return (
    <div className="panel trend-panel">
      <div className="trend-header">
        <div>
          <h3>5-Month ESG Trend</h3>
          <p className="trend-subtitle">Energy · Emissions · Water · Waste</p>
        </div>
        <div className="trend-legend-custom">
          <span className="legend-dot energy" />
          Energy (kWh)
          <span className="legend-dot emissions" />
          Emissions (tCO2e)
          <span className="legend-dot water" />
          Water (m³)
          <span className="legend-dot waste" />
          Waste (kg)
          <span className="legend-dot incident" />
          Incident Rate
        </div>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: 180, overflow: "visible" }}
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = PADDING.top + chartH * frac;
          return (
            <line
              key={frac}
              x1={PADDING.left}
              y1={y}
              x2={W - PADDING.right}
              y2={y}
              stroke="#2a3830"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          );
        })}
        {/* Left Y axis labels (energy) */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = PADDING.top + chartH * frac;
          const val = Math.round(maxEnergy * (1 - frac));
          return (
            <text
              key={frac}
              x={PADDING.left - 8}
              y={y + 4}
              textAnchor="end"
              fontSize="10"
              fill="#5a7862"
            >
              {val >= 1000 ? `${(val / 1000).toFixed(0)}K` : val}
            </text>
          );
        })}
        {/* Right Y axis labels (emissions + water) */}
        {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
          const y = PADDING.top + chartH * frac;
          const val = Math.round(maxRight * (1 - frac));
          return (
            <text
              key={frac}
              x={W - PADDING.right + 8}
              y={y + 4}
              textAnchor="start"
              fontSize="10"
              fill="#5a7862"
            >
              {val >= 1000 ? `${(val / 1000).toFixed(0)}K` : val}
            </text>
          );
        })}
        {/* Left axis title */}
        <text
          x={14}
          y={PADDING.top - 6}
          fontSize="9"
          fill="#5a7862"
          textAnchor="start"
        >
          kWh
        </text>
        {/* Right axis title */}
        <text
          x={W - 14}
          y={PADDING.top - 6}
          fontSize="9"
          fill="#5a7862"
          textAnchor="end"
        >
          tCO2e / m³
        </text>
        {/* X axis labels */}
        {months.map((m, i) => (
          <text
            key={i}
            x={xOf(i)}
            y={H - 8}
            textAnchor="middle"
            fontSize="10"
            fill="#5a7862"
          >
            {m}
          </text>
        ))}
        {/* Energy line */}
        <polyline
          points={energyPts}
          fill="none"
          stroke="#22c55e"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Emissions line */}
        <polyline
          points={emissionsPts}
          fill="none"
          stroke="#f59e0b"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Incident rate bars */}
        {trends.map((t, i) => {
          const barMaxH = 40;
          const barH =
            maxIncident > 0 ? (t.incident_rate / maxIncident) * barMaxH : 0;
          const barX = xOf(i) - 6;
          const barY = H - 18 - barH;
          return (
            <rect
              key={`bar-${i}`}
              x={barX}
              y={barY}
              width="12"
              height={barH}
              fill="#f87171"
              opacity="0.7"
              rx="2"
            />
          );
        })}
        {/* Water line */}
        <polyline
          points={waterPts}
          fill="none"
          stroke="#38bdf8"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Waste line (purple) */}
        <polyline
          points={wastePts}
          fill="none"
          stroke="#a855f7"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {/* Dots + values for energy (left axis) */}
        {trends.map((t, i) => (
          <g key={`e-${i}`}>
            <circle cx={xOf(i)} cy={yLeft(t.energy)} r="4" fill="#22c55e" />
            <text
              x={xOf(i)}
              y={yLeft(t.energy) - 10}
              textAnchor="middle"
              fontSize="9"
              fill="#22c55e"
              fontWeight="600"
            >
              {(t.energy / 1000).toFixed(0)}K
            </text>
          </g>
        ))}
        {/* Dots + values for emissions (right axis) */}
        {trends.map((t, i) => (
          <g key={`em-${i}`}>
            <circle cx={xOf(i)} cy={yRight(t.emissions)} r="4" fill="#f59e0b" />
            <text
              x={xOf(i)}
              y={yRight(t.emissions) - 10}
              textAnchor="middle"
              fontSize="9"
              fill="#f59e0b"
              fontWeight="600"
            >
              {t.emissions}
            </text>
          </g>
        ))}
        {/* Dots + values for water (right axis) */}
        {trends.map((t, i) => (
          <g key={`w-${i}`}>
            <circle cx={xOf(i)} cy={yRight(t.water)} r="4" fill="#38bdf8" />
            <text
              x={xOf(i)}
              y={yRight(t.water) - 10}
              textAnchor="middle"
              fontSize="9"
              fill="#38bdf8"
              fontWeight="600"
            >
              {(t.water / 1000).toFixed(1)}K
            </text>
          </g>
        ))}
        {/* Dots + values for waste (right axis) */}
        {trends.map((t, i) => (
          <g key={`wa-${i}`}>
            <circle cx={xOf(i)} cy={yRight(t.waste)} r="4" fill="#a855f7" />
            <text
              x={xOf(i)}
              y={yRight(t.waste) - 10}
              textAnchor="middle"
              fontSize="9"
              fill="#a855f7"
              fontWeight="600"
            >
              {(t.waste / 1000).toFixed(1)}K
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
