import React, { useState } from "react";

const API = "http://localhost:8000/api";

// ─── Logo ───────────────────────────────────────────────────────────────────
function Logo() {
  return (
    <div className="logo-wordmark">
      <svg
        width="32"
        height="32"
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="32" height="32" rx="8" fill="#22c55e" fillOpacity="0.15" />
        <path
          d="M8 24V12L16 8L24 12V24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M11 24V17H21V24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="13" r="2.5" fill="#22c55e" />
        <path
          d="M8 24H24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span className="logo-text">Integro</span>
    </div>
  );
}

// ─── MetricCard ────────────────────────────────────────────────────────────────
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

// ─── CoverageHero ─────────────────────────────────────────────────────────────
function CoverageHero({ coverageData, isLoading }) {
  if (isLoading) {
    return (
      <div className="coverage-hero">
        <div className="coverage-hero-label">Supply Chain Coverage</div>
        <div className="coverage-hero-number skeleton-number" />
        <div className="coverage-bar-track">
          <div className="coverage-bar-fill skeleton-bar" />
        </div>
        <div className="coverage-stats">
          <div className="coverage-stat">
            <div className="skeleton-stat" />
            <div className="skeleton-stat-label" />
          </div>
          <div className="coverage-stat highlight">
            <div className="skeleton-stat" />
            <div className="skeleton-stat-label" />
          </div>
        </div>
      </div>
    );
  }
  if (!coverageData) return null;
  const pct = coverageData.total_coverage;
  const prev = coverageData.previous_coverage;
  const delta = pct - prev;
  return (
    <div className="coverage-hero">
      <div className="coverage-hero-label">Supply Chain Coverage</div>
      <div className="coverage-hero-number">
        {pct.toFixed(1)}
        <span className="coverage-hero-pct">%</span>
      </div>
      <div className="coverage-bar-track">
        <div className="coverage-bar-fill" style={{ width: `${pct}%` }}>
          <div className="coverage-bar-glow" />
        </div>
        <div className="coverage-bar-marker" style={{ left: `${prev}%` }}>
          <div className="coverage-marker-dot" />
          <div className="coverage-marker-label">Before Gujarat</div>
        </div>
      </div>
      <div className="coverage-stats">
        <div className="coverage-stat">
          <span className="coverage-stat-num">
            {coverageData.responding_suppliers}
          </span>
          <span className="coverage-stat-label">
            of {coverageData.total_suppliers} suppliers reporting
          </span>
        </div>
        <div className="coverage-stat highlight">
          <span className="coverage-stat-num">+{delta.toFixed(1)}%</span>
          <span className="coverage-stat-label">
            from new supplier response
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── EvidencePanel ────────────────────────────────────────────────────────────
function EvidencePanel({ metricType, data, onClose }) {
  if (!data) return null;

  return (
    <div className="evidence-overlay" onClick={onClose}>
      <div className="evidence-panel" onClick={(e) => e.stopPropagation()}>
        <div className="evidence-header">
          <h2>Audit Trail — {metricType.replace("_", " ").toUpperCase()}</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="evidence-body">
          <div className="evidence-row">
            <span className="evidence-key">Data Point ID</span>
            <span className="evidence-val">{data.data_point_id}</span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Value</span>
            <span className="evidence-val highlight">
              {Number(data.value).toLocaleString()} {data.unit}
            </span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Confidence</span>
            <span
              className={`evidence-val badge-${data.confidence.toLowerCase()}`}
            >
              {data.confidence}
            </span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Calculation</span>
            <span className="evidence-val">
              {data.calculation_method.replace(/_/g, " ")}
            </span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Source System</span>
            <span className="evidence-val">{data.source_system}</span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Source Record</span>
            <span className="evidence-val">{data.source_record_id}</span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Extraction Time</span>
            <span className="evidence-val">{data.extraction_timestamp}</span>
          </div>

          <div className="evidence-section-title">Emission Factor</div>
          <div className="evidence-row">
            <span className="evidence-key">Source</span>
            <span className="evidence-val">
              {data.emission_factor_source} {data.emission_factor_year}
            </span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Reference</span>
            <span className="evidence-val">{data.emission_factor_table}</span>
          </div>
          <div className="evidence-row">
            <span className="evidence-key">Factor Value</span>
            <span className="evidence-val">
              {data.emission_factor_value} {data.emission_factor_unit}
            </span>
          </div>

          <div className="evidence-section-title">Tamper-Proof Record</div>
          <div className="chain-visual">
            <div className="chain-node">
              <div className="chain-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <rect
                    x="3"
                    y="6"
                    width="14"
                    height="11"
                    rx="2"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                  />
                  <path
                    d="M7 6V4.5C7 3.12 8.12 2 9.5 2h1C11.88 2 13 3.12 13 4.5V6"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  <circle cx="10" cy="11.5" r="1.5" fill="#22c55e" />
                  <path
                    d="M10 13v2"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <div className="chain-label">This Record</div>
              <div className="chain-hash-preview">
                {data.hash ? data.hash.substring(0, 8) + "..." : "—"}
              </div>
            </div>
            <div className="chain-connector">
              <div className="chain-line" />
              <div className="chain-arrow">→</div>
              <div className="chain-line" />
            </div>
            <div className="chain-node">
              <div className="chain-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <rect
                    x="3"
                    y="6"
                    width="14"
                    height="11"
                    rx="2"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                  />
                  <path
                    d="M7 6V4.5C7 3.12 8.12 2 9.5 2h1C11.88 2 13 3.12 13 4.5V6"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  <circle cx="10" cy="11.5" r="1.5" fill="#22c55e" />
                  <path
                    d="M10 13v2"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <div className="chain-label">Previous Record</div>
              <div className="chain-hash-preview">
                {data.previous_hash
                  ? data.previous_hash.substring(0, 8) + "..."
                  : "genesis"}
              </div>
            </div>
          </div>
          <div className="chain-status">
            <span
              className={`chain-status-badge ${data.chain_valid ? "chain-ok" : "chain-broken"}`}
            >
              {data.chain_valid ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path
                      d="M2.5 7L5.5 10L11.5 4"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Integrity Intact
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path
                      d="M3 3L11 11M11 3L3 11"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                  Chain Broken
                </>
              )}
            </span>
          </div>

          <div className="evidence-section-title">Reported In</div>
          <div className="framework-badges">
            {data.reported_in_frameworks.map((f) => (
              <span key={f} className="framework-badge">
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── TrendChart ───────────────────────────────────────────────────────────────
function TrendChart({ trends, isLoading }) {
  if (isLoading || !trends) {
    return (
      <div className="panel trend-panel">
        <div className="trend-header">
          <div>
            <h3>5-Month ESG Trend</h3>
            <p className="trend-subtitle">Energy · Emissions · Water</p>
          </div>
          <div className="trend-legend-custom">
            <span className="legend-dot energy" />
            Energy
            <span className="legend-dot emissions" />
            Emissions
            <span className="legend-dot water" />
            Water
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
  const maxRight = Math.max(maxEmissions, maxWater); // shared right axis for emissions + water

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

  return (
    <div className="panel trend-panel">
      <div className="trend-header">
        <div>
          <h3>5-Month ESG Trend</h3>
          <p className="trend-subtitle">Energy · Emissions · Water</p>
        </div>
        <div className="trend-legend-custom">
          <span className="legend-dot energy" />
          Energy (kWh)
          <span className="legend-dot emissions" />
          Emissions (tCO2e)
          <span className="legend-dot water" />
          Water (m³)
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
        {/* Water line */}
        <polyline
          points={waterPts}
          fill="none"
          stroke="#38bdf8"
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
      </svg>
    </div>
  );
}

// ─── FrameworkCompare ──────────────────────────────────────────────────────────
function FrameworkCompare() {
  const [metric, setMetric] = useState("energy_kwh");
  const [frameworks, setFrameworks] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    setLoading(true);
    fetch(`${API}/frameworks/compare/${metric}`)
      .then((r) => r.json())
      .then((d) => {
        setFrameworks(d);
        setLoading(false);
      });
  }, [metric]);

  if (!frameworks && !loading)
    return <div className="panel-loading">Loading frameworks...</div>;
  if (loading) return <div className="panel-loading">Loading...</div>;

  return (
    <div className="panel framework-panel">
      <h2>Framework Comparison</h2>
      <p className="panel-subtitle">
        One data entry · Multiple disclosure standards
      </p>
      <div className="metric-tabs">
        <button
          className={metric === "energy_kwh" ? "active" : ""}
          onClick={() => setMetric("energy_kwh")}
        >
          Energy (kWh)
        </button>
        <button
          className={metric === "scope3_category_1" ? "active" : ""}
          onClick={() => setMetric("scope3_category_1")}
        >
          Scope 3 Cat 1
        </button>
        <button
          className={metric === "diesel_consumed" ? "active" : ""}
          onClick={() => setMetric("diesel_consumed")}
        >
          Diesel (Scope 1)
        </button>
        <button
          className={metric === "scope3_category_6" ? "active" : ""}
          onClick={() => setMetric("scope3_category_6")}
        >
          Business Travel
        </button>
      </div>
      <table className="framework-table">
        <thead>
          <tr>
            <th>Framework</th>
            <th>Field ID</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {frameworks.frameworks.map((f) => (
            <tr key={f.name}>
              <td className="fw-name">{f.name}</td>
              <td className="fw-field">{f.field_id}</td>
              <td className="fw-value">{f.value}</td>
              <td>{f.unit}</td>
              <td>
                <span
                  className={`confidence-badge ${f.confidence.toLowerCase()}`}
                >
                  {f.confidence}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="panel-note">
        Data entered once in SAP · Auto-mapped to CSRD, ISSB, GRI, TCFD
      </p>
    </div>
  );
}

// ─── WhatsApp Business Preview ────────────────────────────────────────────────
function WhatsAppBusinessPreview() {
  const [preview, setPreview] = React.useState(null);
  React.useEffect(() => {
    fetch(`${API}/questionnaires/whatsapp-preview/sup_001`)
      .then((r) => r.json())
      .then((d) => setPreview(d));
  }, []);

  if (!preview)
    return <div className="panel-loading">Loading supplier data...</div>;

  return (
    <div className="panel whatsapp-panel">
      <h2>Supplier Engagement</h2>
      <p className="panel-subtitle">WhatsApp Business · Real-time response</p>

      <div className="business-account-card">
        <div className="ba-header">
          <div className="ba-avatar">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect
                width="40"
                height="40"
                rx="20"
                fill="#22c55e"
                fillOpacity="0.15"
              />
              <text
                x="20"
                y="26"
                textAnchor="middle"
                fill="#22c55e"
                fontSize="18"
                fontWeight="700"
              >
                H
              </text>
            </svg>
          </div>
          <div className="ba-info">
            <div className="ba-name">
              H&M ESG Platform
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="verified-check"
              >
                <circle cx="8" cy="8" r="8" fill="#22c55e" />
                <path
                  d="M4.5 8L7 10.5L11.5 6"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div className="ba-meta">
              <span className="ba-badge">Business Account</span>
              <span className="ba-separator">·</span>
              <span className="ba-supplier">Bangladesh Export Textiles</span>
            </div>
          </div>
        </div>

        <div className="ba-message">
          <div className="ba-message-bubble">
            <p className="ba-msg-text">{preview.message_preview}</p>
            <div className="ba-msg-time">10:32 AM ✓✓</div>
          </div>
        </div>

        <div className="ba-supplier-response">
          <div className="ba-sr-label">Supplier response via WhatsApp:</div>
          <div className="ba-message-bubble supplier">
            <p className="ba-msg-text">{preview.supplier_response_example}</p>
            <div className="ba-msg-time">10:34 AM ✓✓</div>
          </div>
        </div>

        <div className="coverage-impact-box">
          <div className="ci-header">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M8 1L10 6H15L11 9.5L12.5 15L8 11.5L3.5 15L5 9.5L1 6H6L8 1Z"
                fill="#22c55e"
              />
            </svg>
            Coverage Impact
          </div>
          <div className="ci-grid">
            <div className="ci-item">
              <span className="ci-label">Supplier</span>
              <span className="ci-value">
                {preview.coverage_impact.supplier_name}
              </span>
            </div>
            <div className="ci-item">
              <span className="ci-label">Annual Spend</span>
              <span className="ci-value">
                ${preview.coverage_impact.annual_spend?.toLocaleString()}
              </span>
            </div>
            <div className="ci-item highlight">
              <span className="ci-label">Coverage Added</span>
              <span className="ci-value">
                +{preview.coverage_impact.coverage_added}%
              </span>
            </div>
            <div className="ci-item highlight">
              <span className="ci-label">New Total</span>
              <span className="ci-value">
                {preview.coverage_impact.new_total_coverage}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <p className="panel-note">
        Suppliers respond in seconds, not weeks. No email portals. No Excel
        forms.
      </p>
    </div>
  );
}

// ─── TrustBadges ──────────────────────────────────────────────────────────────
function TrustBadges() {
  return (
    <div className="trust-badges">
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 1L10 6H15L11 9.5L12.5 15L8 11.5L3.5 15L5 9.5L1 6H6L8 1Z"
            fill="#22c55e"
          />
        </svg>
        CSRD Compliant
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="#22c55e" strokeWidth="1.5" />
          <path
            d="M5 8L7 10L11 6"
            stroke="#22c55e"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        GHG Protocol Source
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect
            x="2"
            y="4"
            width="12"
            height="9"
            rx="2"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <path
            d="M5 4V3C5 1.9 5.9 1 7 1h2C10.1 1 11 1.9 11 3v1"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <circle cx="8" cy="9" r="1.5" fill="#22c55e" />
        </svg>
        Audit Ready
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 2C5.24 2 3 4.24 3 7c0 3 3 7 5 9 2-2 5-6 5-9 0-2.76-2.24-5-5-5z"
            fill="#22c55e"
            fillOpacity="0.2"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <circle cx="8" cy="7" r="2" fill="#22c55e" />
        </svg>
        Scope 3 Verified
      </div>
    </div>
  );
}

// ─── SupplyChainPanel ───────────────────────────────────────────────────────────
function SupplyChainPanel() {
  const [suppliers, setSuppliers] = React.useState(null);
  const [selectedSupplier, setSelectedSupplier] = React.useState(null);
  const [supplierProfile, setSupplierProfile] = React.useState(null);
  const [scope3, setScope3] = React.useState(null);
  const [geopolitical, setGeopolitical] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/suppliers/risk-ranked`),
      fetch(`${API}/scope3/categories`),
      fetch(`${API}/risk/geopolitical`),
    ])
      .then(([r1, r2, r3]) => Promise.all([r1.json(), r2.json(), r3.json()]))
      .then(([s, sc, geo]) => {
        setSuppliers(s);
        setScope3(sc);
        setGeopolitical(geo);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  function selectSupplier(s) {
    setSelectedSupplier(s);
    setSupplierProfile(null);
    fetch(`${API}/suppliers/${s.id}/profile`)
      .then((r) => r.json())
      .then(setSupplierProfile)
      .catch(() => {});
  }

  if (loading)
    return <div className="panel-loading">Loading supply chain data...</div>;

  const suppliersList = suppliers?.suppliers || [];
  const scope3List = scope3?.categories || [];

  return (
    <div className="supply-chain-panel">
      <div className="section-title">Supply Chain Overview</div>

      {/* Scope 3 Coverage */}
      <div className="panel">
        <h3>Scope 3 Category Coverage</h3>
        <div className="scope3-grid">
          {scope3List.map((cat) => (
            <div key={cat.id} className="scope3-category-card">
              <div className="scope3-cat-name">{cat.name}</div>
              <div className="scope3-coverage-bar">
                <div
                  className="scope3-coverage-fill"
                  style={{ width: `${cat.coverage_pct}%` }}
                />
              </div>
              <div className="scope3-coverage-pct">{cat.coverage_pct}%</div>
              <div className="scope3-meta">
                {cat.respondents}/{cat.total} suppliers
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Supplier Risk Table */}
      <div className="panel">
        <h3>Supplier Risk Ranking</h3>
        <table className="supplier-table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Country</th>
              <th>Risk Tier</th>
              <th>Risk Score</th>
              <th>Active Flags</th>
              <th>Certifications</th>
            </tr>
          </thead>
          <tbody>
            {suppliersList.map((s) => (
              <tr
                key={s.id}
                onClick={() => selectSupplier(s)}
                className={selectedSupplier?.id === s.id ? "selected" : ""}
                style={{ cursor: "pointer" }}
              >
                <td className="supplier-name">{s.name}</td>
                <td>{s.country}</td>
                <td>
                  <span
                    className={`risk-tier tier-${s.risk_tier?.toLowerCase()}`}
                  >
                    {s.risk_tier || "—"}
                  </span>
                </td>
                <td>{s.risk_score != null ? s.risk_score.toFixed(2) : "—"}</td>
                <td>{s.active_flags || 0}</td>
                <td>{s.certifications?.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Geopolitical Risk Heat Map */}
      {geopolitical && (
        <div className="panel">
          <h3>Geopolitical Risk — Tier 1 Supplier Countries</h3>
          <table className="geo-table">
            <thead>
              <tr>
                <th>Country</th>
                <th>Political Stability</th>
                <th>Trade Exposure</th>
                <th>Currency Volatility</th>
                <th>Overall Score</th>
              </tr>
            </thead>
            <tbody>
              {geopolitical.countries.map((c) => (
                <tr key={c.country_code}>
                  <td>{c.country}</td>
                  <td>
                    <div className="geo-bar-container">
                      <div
                        className="geo-bar-fill"
                        style={{
                          width: `${c.political_stability}%`,
                          background:
                            c.political_stability > 60
                              ? "#22c55e"
                              : c.political_stability > 40
                                ? "#f59e0b"
                                : "#ef4444",
                        }}
                      />
                      <span>{c.political_stability}</span>
                    </div>
                  </td>
                  <td>
                    <div className="geo-bar-container">
                      <div
                        className="geo-bar-fill"
                        style={{
                          width: `${c.trade_exposure}%`,
                          background:
                            c.trade_exposure > 70
                              ? "#ef4444"
                              : c.trade_exposure > 50
                                ? "#f59e0b"
                                : "#22c55e",
                        }}
                      />
                      <span>{c.trade_exposure}</span>
                    </div>
                  </td>
                  <td>
                    <div className="geo-bar-container">
                      <div
                        className="geo-bar-fill"
                        style={{
                          width: `${c.currency_volatility}%`,
                          background:
                            c.currency_volatility > 60
                              ? "#ef4444"
                              : c.currency_volatility > 40
                                ? "#f59e0b"
                                : "#22c55e",
                        }}
                      />
                      <span>{c.currency_volatility}</span>
                    </div>
                  </td>
                  <td>
                    <span
                      className={`geo-score score-${c.overall_score > 60 ? "green" : c.overall_score > 40 ? "amber" : "red"}`}
                    >
                      {c.overall_score}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Supplier Profile Panel */}
      {selectedSupplier && supplierProfile && (
        <div className="panel">
          <h3>Supplier Profile — {selectedSupplier.name}</h3>
          <div className="profile-grid">
            <div className="profile-score-card">
              <div className="profile-label">Overall Risk Score</div>
              <div className="profile-value">
                {supplierProfile.overall_risk_score?.toFixed(1) || "—"}
              </div>
              <div
                className={`risk-tier tier-${(supplierProfile.risk_tier || "").toLowerCase()}`}
              >
                {supplierProfile.risk_tier || "—"}
              </div>
            </div>
            <div className="profile-score-card">
              <div className="profile-label">Financial Health</div>
              <div className="profile-value">
                {supplierProfile.financial_health_score || "—"}
              </div>
            </div>
            <div className="profile-score-card">
              <div className="profile-label">Scope 3 Coverage</div>
              <div className="profile-value">
                {supplierProfile.scope3_coverage_pct || 0}%
              </div>
            </div>
            <div className="profile-score-card">
              <div className="profile-label">Traceability</div>
              <div className="profile-value">
                {supplierProfile.traceability_status || "—"}
              </div>
            </div>
          </div>
          <div className="cluster-bars">
            <h4>ESG Cluster Scores</h4>
            {Object.entries(supplierProfile.clusters || {}).map(
              ([key, val]) => (
                <div key={key} className="cluster-bar-row">
                  <span className="cluster-name">{key.replace(/_/g, " ")}</span>
                  <div className="cluster-bar-track">
                    <div
                      className="cluster-bar-fill"
                      style={{ width: `${val}%` }}
                    />
                  </div>
                  <span className="cluster-val">{val}</span>
                </div>
              ),
            )}
          </div>
          {supplierProfile.ml_recommendations?.length > 0 && (
            <div className="ml-recommendations">
              <h4>ML Recommendations</h4>
              <ul>
                {supplierProfile.ml_recommendations.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── RiskAlertsPanel ──────────────────────────────────────────────────────────
function RiskAlertsPanel() {
  const [flags, setFlags] = React.useState(null);
  const [summary, setSummary] = React.useState(null);
  const [scorecard, setScorecard] = React.useState(null);
  const [completeness, setCompleteness] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [acknowledging, setAcknowledging] = React.useState(null);

  React.useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/risk/flags`),
      fetch(`${API}/risk/summary`),
      fetch(`${API}/risk/scorecard`),
      fetch(`${API}/scope3/completeness`),
    ])
      .then(([r1, r2, r3, r4]) =>
        Promise.all([r1.json(), r2.json(), r3.json(), r4.json()]),
      )
      .then(([f, s, sc, comp]) => {
        setFlags(f);
        setSummary(s);
        setScorecard(sc);
        setCompleteness(comp);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  function acknowledgeFlag(flagId) {
    setAcknowledging(flagId);
    fetch(`${API}/risk/flags/${flagId}/acknowledge`, { method: "POST" })
      .then((r) => r.json())
      .then((updated) => {
        setFlags((prev) => ({
          ...prev,
          flags: prev.flags.map((f) => (f.id === flagId ? updated : f)),
        }));
        setAcknowledging(null);
      })
      .catch(() => setAcknowledging(null));
  }

  if (loading) return <div className="panel-loading">Loading risk data...</div>;

  const flagsList = flags?.flags || [];
  const activeFlags = flagsList.filter((f) => !f.acknowledged);
  const acknowledgedFlags = flagsList.filter((f) => f.acknowledged);

  const sevColors = {
    CRITICAL: "#ef4444",
    WARNING: "#f59e0b",
    INFO: "#38bdf8",
  };

  return (
    <div className="risk-alerts-panel">
      <div className="section-title">Risk & Alerts</div>

      {/* Risk Summary Strip */}
      {summary && (
        <div className="risk-summary-strip">
          <div className="risk-sum-card critical">
            <div className="risk-sum-count">
              {summary.by_severity?.critical || 0}
            </div>
            <div className="risk-sum-label">Critical</div>
          </div>
          <div className="risk-sum-card warning">
            <div className="risk-sum-count">
              {summary.by_severity?.warning || 0}
            </div>
            <div className="risk-sum-label">Warning</div>
          </div>
          <div className="risk-sum-card info">
            <div className="risk-sum-count">
              {summary.by_severity?.info || 0}
            </div>
            <div className="risk-sum-label">Info</div>
          </div>
          <div className="risk-sum-card">
            <div className="risk-sum-count">{summary.avg_days_open || 0}</div>
            <div className="risk-sum-label">Avg Days Open</div>
          </div>
        </div>
      )}

      {/* 2x2 Risk Scorecard */}
      {scorecard && (
        <div className="panel">
          <h3>Risk Scorecard</h3>
          <div className="scorecard-grid">
            {scorecard.quadrants.map((q) => {
              const tierColors = { A: "#22c55e", B: "#f59e0b", C: "#ef4444" };
              const trendArrows = { up: "↑", down: "↓", stable: "→" };
              return (
                <div key={q.id} className="scorecard-cell">
                  <div className="scorecard-id">
                    {q.id} — {q.name}
                  </div>
                  <div className="scorecard-score">{q.score}</div>
                  <div className="scorecard-meta">
                    <span
                      className="scorecard-tier"
                      style={{ color: tierColors[q.tier] || "#888" }}
                    >
                      Tier {q.tier}
                    </span>
                    <span className="scorecard-trend">
                      {trendArrows[q.trend] || "→"} {q.trend}
                    </span>
                  </div>
                  <div className="scorecard-flags">
                    {q.active_flags} active flag(s)
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Scope 3 Completeness Meter */}
      {completeness && (
        <div className="panel">
          <h3>Scope 3 Completeness</h3>
          <div className="completeness-header">
            <div className="completeness-donut">
              <svg viewBox="0 0 36 36" width="80" height="80">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="3"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#22c55e"
                  strokeWidth="3"
                  strokeDasharray={`${completeness.overall_coverage_pct}, 100`}
                />
                <text
                  x="18"
                  y="20.5"
                  textAnchor="middle"
                  fontSize="8"
                  fill="#374151"
                >
                  {completeness.overall_coverage_pct}%
                </text>
              </svg>
            </div>
            <div className="completeness-stats">
              <div>
                <strong>{completeness.total_respondents}</strong> of{" "}
                <strong>{completeness.total_suppliers}</strong> suppliers
                responded
              </div>
              <div className="completeness-cat-bars">
                {completeness.by_category.map((c) => (
                  <div key={c.id} className="completeness-cat-row">
                    <span>{c.name}</span>
                    <div className="completeness-bar-track">
                      <div
                        className="completeness-bar-fill"
                        style={{ width: `${c.coverage_pct}%` }}
                      />
                    </div>
                    <span>{c.coverage_pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Flags Feed */}
      <div className="panel">
        <h3>Active Risk Flags</h3>
        {activeFlags.length === 0 ? (
          <div className="empty-state">No active risk flags</div>
        ) : (
          <div className="risk-flags-feed">
            {activeFlags
              .sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0))
              .map((flag) => (
                <div key={flag.id} className="risk-flag-card">
                  <div className="risk-flag-header">
                    <span
                      className="risk-flag-severity"
                      style={{ background: sevColors[flag.severity] || "#888" }}
                    >
                      {flag.severity}
                    </span>
                    <span className="risk-flag-cluster">{flag.cluster}</span>
                    <span className="risk-flag-priority">
                      P{(flag.priority_score || 0).toFixed(1)}
                    </span>
                  </div>
                  <div className="risk-flag-message">{flag.flag_text}</div>
                  <div className="risk-flag-meta">
                    <span>{flag.days_overdue} days overdue</span>
                    <span>{flag.created_at}</span>
                  </div>
                  <button
                    className="ack-btn"
                    onClick={() => acknowledgeFlag(flag.id)}
                    disabled={acknowledging === flag.id}
                  >
                    {acknowledging === flag.id
                      ? "Acknowledging..."
                      : "Acknowledge"}
                  </button>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Acknowledged Flags */}
      {acknowledgedFlags.length > 0 && (
        <div className="panel">
          <h3>Acknowledged Flags</h3>
          <details className="acknowledged-details">
            <summary>
              View {acknowledgedFlags.length} acknowledged flag(s)
            </summary>
            <div className="risk-flags-feed acknowledged">
              {acknowledgedFlags.map((flag) => (
                <div key={flag.id} className="risk-flag-card acknowledged">
                  <div className="risk-flag-header">
                    <span
                      className="risk-flag-severity"
                      style={{ background: "#888" }}
                    >
                      {flag.severity}
                    </span>
                    <span className="risk-flag-cluster">{flag.cluster}</span>
                    <span className="risk-flag-ack-time">
                      Acknowledged {flag.acknowledged_at}
                    </span>
                  </div>
                  <div className="risk-flag-message">{flag.flag_text}</div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* Geopolitical Heatmap Placeholder */}
      <div className="panel">
        <h3>Geopolitical Risk Map</h3>
        <div className="geo-heatmap">
          <div className="geo-country high-risk">
            <span className="country-code">BD</span>
            <span className="country-name">Bangladesh</span>
            <span className="risk-level">Elevated Risk</span>
          </div>
          <div className="geo-country medium-risk">
            <span className="country-code">VN</span>
            <span className="country-name">Vietnam</span>
            <span className="risk-level">Moderate Risk</span>
          </div>
          <div className="geo-country low-risk">
            <span className="country-code">IN</span>
            <span className="country-name">India</span>
            <span className="risk-level">Low Risk</span>
          </div>
          <div className="geo-country medium-risk">
            <span className="country-code">PK</span>
            <span className="country-name">Pakistan</span>
            <span className="risk-level">Moderate Risk</span>
          </div>
          <div className="geo-country low-risk">
            <span className="country-code">MM</span>
            <span className="country-name">Myanmar</span>
            <span className="risk-level">Low Risk</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── SummaryStrip ───────────────────────────────────────────────────────────────
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

// ─── Dashboard ────────────────────────────────────────────────────────────────
function Dashboard() {
  const [metrics, setMetrics] = React.useState(null);
  const [trends, setTrends] = React.useState(null);
  const [riskSummary, setRiskSummary] = React.useState(null);
  const [scope3Completeness, setScope3Completeness] = React.useState(null);
  const [selectedMetric, setSelectedMetric] = React.useState(null);
  const [evidence, setEvidence] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState("operations");
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    Promise.all([
      fetch(`${API}/dashboard/live`),
      fetch(`${API}/dashboard/trends`),
      fetch(`${API}/risk/summary`),
      fetch(`${API}/scope3/completeness`),
    ])
      .then(([r1, r2, r3, r4]) =>
        Promise.all([r1.json(), r2.json(), r3.json(), r4.json()]),
      )
      .then(([d1, d2, d3, d4]) => {
        setMetrics(d1);
        setTrends(d2.trends);
        setRiskSummary(d3);
        setScope3Completeness(d4);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  }, []);

  function showEvidence(metricType) {
    setSelectedMetric(metricType);
    fetch(`${API}/evidence/drilldown/${metricType}`)
      .then((r) => r.json())
      .then((d) => setEvidence(d));
  }

  function downloadReport() {
    fetch(`${API}/reports/esg-pdf`)
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "ESG-Report-Bangladesh-Export-Textiles-2025-Q1.pdf";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
  }

  const METRIC_LABELS = {
    energy_kwh: "Electricity (Scope 2)",
    emissions_tco2: "Total Emissions (Scope 1+2)",
    water_m3: "Water Withdrawal",
    scope3_category1: "Purchased Goods (Scope 3)",
    diesel_consumed: "Diesel Combustion (Scope 1)",
    scope3_category6: "Business Travel (Scope 3)",
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <Logo />
          <div className="header-divider" />
          <div className="header-org">
            <strong>Integro</strong>
            <span>ESG Supply Chain Intelligence</span>
          </div>
        </div>
        <nav className="header-nav">
          <button
            className={activeTab === "operations" ? "active" : ""}
            onClick={() => setActiveTab("operations")}
          >
            Operations
          </button>
          <button
            className={activeTab === "supply-chain" ? "active" : ""}
            onClick={() => setActiveTab("supply-chain")}
          >
            Supply Chain
          </button>
          <button
            className={activeTab === "risk-alerts" ? "active" : ""}
            onClick={() => setActiveTab("risk-alerts")}
          >
            Risk & Alerts
          </button>
          <button
            className={activeTab === "frameworks" ? "active" : ""}
            onClick={() => setActiveTab("frameworks")}
          >
            Frameworks
          </button>
          <button
            className={activeTab === "whatsapp" ? "active" : ""}
            onClick={() => setActiveTab("whatsapp")}
          >
            Supplier Engagement
          </button>
        </nav>
        <button className="download-btn" onClick={downloadReport}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path
              d="M7 1v8M4 6l3 3 3-3M2 11h10"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Download Report
        </button>
        <TrustBadges />
      </header>

      <main className="app-main">
        {activeTab === "operations" && (
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
        )}
        {activeTab === "supply-chain" && <SupplyChainPanel />}
        {activeTab === "risk-alerts" && <RiskAlertsPanel />}
        {activeTab === "frameworks" && <FrameworkCompare />}
        {activeTab === "whatsapp" && <WhatsAppBusinessPreview />}
      </main>

      {evidence && (
        <EvidencePanel
          metricType={selectedMetric}
          data={evidence}
          onClose={() => setEvidence(null)}
        />
      )}
    </div>
  );
}

export default Dashboard;
