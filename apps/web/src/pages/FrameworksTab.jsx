import React, { useState, useEffect, useRef } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";

const _CLUSTER_METRIC_MAP = {
  energy_kwh: "Energy — E1",
  scope3_category_1: "Purchased Goods — E1",
  scope3_cat2: "Capital Goods — E1",
  scope3_cat3: "Fuel & Energy — E1",
  scope3_cat4: "Upstream Transport — E1",
  scope3_cat5: "Waste Generated — E1",
  scope3_category_6: "Business Travel — E1",
  scope3_cat7: "Employee Commuting — E1",
  scope3_cat8: "Upstream Leased — E1",
  scope3_cat9: "Downstream Transport — E1",
  scope3_cat11: "Downstream Leased — E1",
  scope3_cat12: "End of Life — E1",
  diesel_consumed: "Diesel — Scope 1",
  water_m3: "Water — E3",
  waste_tonnes: "Waste — E3",
  gender_pct: "Gender Diversity — S3",
  safety_incidents: "Workforce Safety — S1",
  governance_score: "Board Governance — G1",
};

export default function FrameworksTab() {
  const [metric, setMetric] = useState("energy_kwh");
  const [frameworks, setFrameworks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedFramework, setSelectedFramework] = useState(null);
  const panelRef = useRef(null);

  function loadFrameworks() {
    setLoading(true);
    setError(null);
    apiFetch(`/frameworks/compare/${metric}`)
      .then((r) => r.json())
      .then((d) => {
        setFrameworks(d);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load framework comparison");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadFrameworks();
  }, [metric]);

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) {
      setSelectedFramework(null);
    }
  }

  useEffect(() => {
    function handleKey(e) {
      if (e.key === "Escape") setSelectedFramework(null);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  if (error) {
    return <ErrorState message={error} onRetry={loadFrameworks} />;
  }

  if (!frameworks && !loading)
    return <div className="panel-loading">Loading frameworks...</div>;
  if (loading) return <div className="panel-loading">Loading...</div>;

  return (
    <div className="panel framework-panel">
      <h2>Framework Comparison</h2>
      <p className="panel-subtitle">
        One data entry · Multiple disclosure standards
      </p>
      <div className="cluster-select-wrap">
        <select
          className="cluster-select input"
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
        >
          {Object.entries(_CLUSTER_METRIC_MAP).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
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
            <tr
              key={f.name}
              onClick={() => setSelectedFramework(f)}
              style={{ cursor: "pointer" }}
            >
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

      {selectedFramework && (
        <div className="side-panel-overlay" onClick={handleOverlayClick}>
          <div className="side-panel" ref={panelRef} role="dialog">
            <div className="side-panel-header">
              <h3>{selectedFramework.name}</h3>
              <button
                className="side-panel-close"
                onClick={() => setSelectedFramework(null)}
              >
                &times;
              </button>
            </div>
            <div className="side-panel-content">
              <div className="side-panel-field">
                <span className="side-panel-label">Field ID</span>
                <span className="side-panel-value fw-field">
                  {selectedFramework.field_id}
                </span>
              </div>
              <div className="side-panel-field side-panel-description">
                <span className="side-panel-label">Disclosure Requirement</span>
                <p className="side-panel-description-text">
                  {selectedFramework.description}
                </p>
              </div>
              <div className="side-panel-field">
                <span className="side-panel-label">Value</span>
                <span className="side-panel-value fw-value">
                  {selectedFramework.value}
                </span>
              </div>
              <div className="side-panel-field">
                <span className="side-panel-label">Unit</span>
                <span className="side-panel-value">
                  {selectedFramework.unit}
                </span>
              </div>
              <div className="side-panel-field">
                <span className="side-panel-label">Confidence</span>
                <span
                  className={`confidence-badge ${selectedFramework.confidence.toLowerCase()}`}
                >
                  {selectedFramework.confidence}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
