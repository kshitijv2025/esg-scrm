import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import "./BuyerPortalPage.css";

export default function BuyerPortalPage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchPortalData() {
      try {
        const response = await fetch(`/api/buyer-portal/${token}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to load portal");
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      fetchPortalData();
    }
  }, [token]);

  if (loading) {
    return (
      <div className="buyer-portal">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading portal data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="buyer-portal">
        <div className="error-state">
          <h2>Unable to Load Portal</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="buyer-portal">
      <header className="portal-header">
        <div className="header-content">
          <h1>{data.buyer_org_name} ESG Portal</h1>
          <p>Supplier ESG Performance Overview</p>
        </div>
      </header>

      <main className="portal-content">
        <section className="metrics-section">
          <h2>Key Metrics</h2>
          <div className="metrics-grid">
            {Object.entries(data.metrics || {}).map(([cluster, metric]) => (
              <div key={cluster} className="metric-card">
                <span className="metric-cluster">{cluster}</span>
                <span className="metric-value">
                  {metric.value?.toLocaleString() ?? "—"}
                </span>
                <span className="metric-latest">
                  Latest: {metric.latest?.slice(0, 10) || "—"}
                </span>
              </div>
            ))}
            {Object.keys(data.metrics || {}).length === 0 && (
              <p className="no-data">No metrics data available yet.</p>
            )}
          </div>
        </section>

        <section className="suppliers-section">
          <h2>Suppliers in Scope</h2>
          <div className="suppliers-list">
            {data.suppliers?.map((supplier) => (
              <div key={supplier.id} className="supplier-card">
                <div className="supplier-header">
                  <h3>{supplier.name}</h3>
                  <span
                    className={`risk-tier tier-${supplier.risk_tier?.toLowerCase() || "unknown"}`}
                  >
                    {supplier.risk_tier || "Unrated"}
                  </span>
                </div>
                <div className="supplier-details">
                  <span>{supplier.country}</span>
                  <span>{supplier.industry}</span>
                  <span>Tier {supplier.tier?.replace("tier", "")}</span>
                </div>
                <div className="supplier-metrics">
                  <div className="supplier-metric">
                    <span className="label">ESG Score</span>
                    <span className="value">{supplier.esg_score ?? "—"}</span>
                  </div>
                  <div className="supplier-metric">
                    <span className="label">Status</span>
                    <span
                      className={`status status-${supplier.questionnaire_status}`}
                    >
                      {supplier.questionnaire_status?.replace("_", " ") ||
                        "Unknown"}
                    </span>
                  </div>
                </div>
                {supplier.certifications?.length > 0 && (
                  <div className="supplier-certs">
                    {supplier.certifications.map((cert, i) => (
                      <span key={i} className="cert-badge">
                        {cert}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {(!data.suppliers || data.suppliers.length === 0) && (
              <p className="no-data">No suppliers in scope.</p>
            )}
          </div>
        </section>

        <section className="risk-section">
          <h2>Active Risk Flags</h2>
          <div className="risk-flags-list">
            {data.risk_flags?.map((flag) => (
              <div
                key={flag.id}
                className={`risk-flag severity-${flag.severity?.toLowerCase()}`}
              >
                <div className="flag-header">
                  <span className="severity-badge">{flag.severity}</span>
                  <span className="cluster">{flag.cluster}</span>
                </div>
                <p className="flag-text">{flag.flag_text}</p>
                <span className="supplier-name">
                  {flag.supplier_name || "Unknown Supplier"}
                </span>
              </div>
            ))}
            {(!data.risk_flags || data.risk_flags.length === 0) && (
              <p className="no-data">No active risk flags.</p>
            )}
          </div>
        </section>

        <section className="evidence-section">
          <h2>Evidence Summary</h2>
          <div className="evidence-stats">
            <div className="stat">
              <span className="stat-value">
                {data.evidence_summary?.total_entries || 0}
              </span>
              <span className="stat-label">Total Evidence Entries</span>
            </div>
            <div className="stat">
              <span className="stat-value">
                {data.evidence_summary?.latest_entry?.slice(0, 10) || "—"}
              </span>
              <span className="stat-label">Latest Entry</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
