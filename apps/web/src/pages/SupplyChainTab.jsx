import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import GeopoliticalRiskTable from "../components/GeopoliticalRiskTable";

export default function SupplyChainTab() {
  const [suppliers, setSuppliers] = useState(null);
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [supplierProfile, setSupplierProfile] = useState(null);
  const [scope3, setScope3] = useState(null);
  const [geopolitical, setGeopolitical] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  function loadData() {
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch("/suppliers/risk-ranked").then((r) => r.json()),
      apiFetch("/scope3/categories").then((r) => r.json()),
      apiFetch("/risk/geopolitical").then((r) => r.json()),
    ])
      .then(([s, sc, geo]) => {
        setSuppliers(s);
        setScope3(sc);
        setGeopolitical(geo);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load supply chain data");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadData();
  }, []);

  function selectSupplier(s) {
    setSelectedSupplier(s);
    setSupplierProfile(null);
    apiFetch(`/suppliers/${s.id}/profile`)
      .then((r) => r.json())
      .then(setSupplierProfile)
      .catch((err) => {
        setError(err.message || "Failed to load supplier profile");
      });
  }

  if (loading) {
    return <div className="panel-loading">Loading supply chain data...</div>;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

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
          <GeopoliticalRiskTable countries={geopolitical.countries} />
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
