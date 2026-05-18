import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";

export default function FrameworksTab() {
  const [metric, setMetric] = useState("energy_kwh");
  const [frameworks, setFrameworks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
