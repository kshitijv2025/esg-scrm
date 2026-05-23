import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import GeopoliticalRiskTable from "../components/GeopoliticalRiskTable";

const COUNTRY_FLAGS = {
  Bangladesh: "🇧🇩",
  Vietnam: "🇻🇳",
  India: "🇮🇳",
  China: "🇨🇳",
  Pakistan: "🇵🇰",
  Indonesia: "🇮🇩",
  Thailand: "🇹🇭",
  Malaysia: "🇲🇾",
  Philippines: "🇵🇭",
  Myanmar: "🇲🇲",
  Cambodia: "🇰🇭",
  Laos: "🇱🇦",
  "South Korea": "🇰🇷",
  Japan: "🇯🇵",
  Turkey: "🇹🇷",
  Egypt: "🇪🇬",
  Ethiopia: "🇪🇹",
  Nigeria: "🇳🇬",
  Kenya: "🇰🇪",
  Brazil: "🇧🇷",
  Mexico: "🇲🇽",
  Argentina: "🇦🇷",
  Germany: "🇩🇪",
  France: "🇫🇷",
  Italy: "🇮🇹",
  Spain: "🇪🇸",
  Poland: "🇵🇱",
  "United Kingdom": "🇬🇧",
  USA: "🇺🇸",
  default: "🌐",
};

function getFlag(country) {
  return COUNTRY_FLAGS[country] || COUNTRY_FLAGS.default;
}

function getTierColor(tier) {
  switch ((tier || "").toUpperCase()) {
    case "A":
      return "var(--green)";
    case "B":
      return "var(--amber)";
    case "C":
      return "var(--red)";
    case "D":
      return "#7f1d1d";
    default:
      return "var(--text-muted)";
  }
}

function getTierBg(tier) {
  switch ((tier || "").toUpperCase()) {
    case "A":
      return "rgba(34,197,94,0.15)";
    case "B":
      return "rgba(245,158,11,0.15)";
    case "C":
      return "rgba(239,68,68,0.15)";
    case "D":
      return "rgba(127,29,29,0.4)";
    default:
      return "var(--surface3)";
  }
}

function getCoverageColor(pct) {
  if (pct >= 75) return "var(--green)";
  if (pct >= 40) return "var(--amber)";
  return "var(--red)";
}

function getCoverageBg(pct) {
  if (pct >= 75) return "rgba(34,197,94,0.12)";
  if (pct >= 40) return "rgba(245,158,11,0.12)";
  return "rgba(239,68,68,0.12)";
}

// Mini score dot
function ScoreDot({ value }) {
  const color =
    value >= 70 ? "var(--green)" : value >= 40 ? "var(--amber)" : "var(--red)";
  return (
    <span
      style={{
        display: "inline-block",
        width: "8px",
        height: "8px",
        borderRadius: "50%",
        background: color,
        flexShrink: 0,
      }}
    />
  );
}

// Mini score bar (3 bars for E/S/G)
function MiniScoreBars({ e_score, s_score, g_score }) {
  const makeBar = (val) => ({
    width: `${Math.min(100, Math.max(0, val || 0))}%`,
    background:
      val >= 70 ? "var(--green)" : val >= 40 ? "var(--amber)" : "var(--red)",
    height: "4px",
    borderRadius: "999px",
    transition: "width 0.4s ease",
  });
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "2px",
        minWidth: "48px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
        <span
          style={{
            fontSize: "0.6rem",
            color: "var(--text-muted)",
            fontWeight: 700,
            width: "8px",
          }}
        >
          E
        </span>
        <div
          style={{
            flex: 1,
            height: "4px",
            background: "var(--surface3)",
            borderRadius: "999px",
            overflow: "hidden",
          }}
        >
          <div style={makeBar(e_score)} />
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
        <span
          style={{
            fontSize: "0.6rem",
            color: "var(--text-muted)",
            fontWeight: 700,
            width: "8px",
          }}
        >
          S
        </span>
        <div
          style={{
            flex: 1,
            height: "4px",
            background: "var(--surface3)",
            borderRadius: "999px",
            overflow: "hidden",
          }}
        >
          <div style={makeBar(s_score)} />
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
        <span
          style={{
            fontSize: "0.6rem",
            color: "var(--text-muted)",
            fontWeight: 700,
            width: "8px",
          }}
        >
          G
        </span>
        <div
          style={{
            flex: 1,
            height: "4px",
            background: "var(--surface3)",
            borderRadius: "999px",
            overflow: "hidden",
          }}
        >
          <div style={makeBar(g_score)} />
        </div>
      </div>
    </div>
  );
}

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
      .catch(() => {
        // non-fatal — profile panel stays empty
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
    <div className="supply-chain-layout">
      {/* LEFT — Supplier Sidebar (SC1) */}
      <aside className="supplier-sidebar">
        <div className="supplier-sidebar-header">
          <span className="supplier-sidebar-title">Suppliers</span>
          <span className="supplier-sidebar-count">{suppliersList.length}</span>
        </div>
        <div className="supplier-sidebar-list">
          {suppliersList.map((s) => {
            const isSelected = selectedSupplier?.id === s.id;
            return (
              <button
                key={s.id}
                className={`supplier-sidebar-item${isSelected ? " selected" : ""}`}
                onClick={() => selectSupplier(s)}
              >
                <div className="supplier-item-top">
                  <span className="supplier-item-flag">
                    {getFlag(s.country)}
                  </span>
                  <span className="supplier-item-name">{s.name}</span>
                  <span
                    className="supplier-item-tier"
                    style={{
                      color: getTierColor(s.risk_tier),
                      background: getTierBg(s.risk_tier),
                    }}
                  >
                    {s.risk_tier || "—"}
                  </span>
                </div>
                <div className="supplier-item-bottom">
                  <MiniScoreBars
                    e_score={s.e_score}
                    s_score={s.s_score}
                    g_score={s.g_score}
                  />
                  <span className="supplier-item-score">
                    {s.overall_score != null ? s.overall_score.toFixed(1) : "—"}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* RIGHT — Profile + SC3 */}
      <main className="supplier-main">
        {selectedSupplier && supplierProfile && (
          <>
            {/* Supplier Profile Panel (SC2) */}
            <div className="panel">
              <div className="profile-panel-header">
                <div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      marginBottom: "4px",
                    }}
                  >
                    <span style={{ fontSize: "1.4rem" }}>
                      {getFlag(selectedSupplier.country)}
                    </span>
                    <h3
                      style={{
                        margin: 0,
                        fontSize: "1rem",
                        fontWeight: 700,
                        color: "var(--text)",
                      }}
                    >
                      {selectedSupplier.name}
                    </h3>
                  </div>
                  <div
                    style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}
                  >
                    {selectedSupplier.country}
                  </div>
                </div>
                <span
                  className="supplier-item-tier"
                  style={{
                    fontSize: "0.85rem",
                    color: getTierColor(selectedSupplier.risk_tier),
                    background: getTierBg(selectedSupplier.risk_tier),
                    padding: "4px 12px",
                    borderRadius: "999px",
                    fontWeight: 700,
                    alignSelf: "flex-start",
                  }}
                >
                  Tier {selectedSupplier.risk_tier || "—"}
                </span>
              </div>

              <div className="profile-kpi-grid">
                <div className="profile-kpi-card">
                  <div className="profile-kpi-label">Overall Risk Score</div>
                  <div
                    className="profile-kpi-value"
                    style={{ color: getTierColor(selectedSupplier.risk_tier) }}
                  >
                    {supplierProfile.overall_risk_score != null
                      ? supplierProfile.overall_risk_score.toFixed(1)
                      : "—"}
                  </div>
                </div>
                <div className="profile-kpi-card">
                  <div className="profile-kpi-label">Financial Health</div>
                  <div
                    className="profile-kpi-value"
                    style={{
                      color:
                        (supplierProfile.financial_health_score ?? 0) >= 70
                          ? "var(--green)"
                          : (supplierProfile.financial_health_score ?? 0) >= 40
                            ? "var(--amber)"
                            : "var(--red)",
                    }}
                  >
                    {supplierProfile.financial_health_score ?? "—"}
                  </div>
                </div>
                <div className="profile-kpi-card">
                  <div className="profile-kpi-label">Scope 3 Coverage</div>
                  <div
                    className="profile-kpi-value"
                    style={{
                      color: getCoverageColor(
                        supplierProfile.scope3_coverage_pct,
                      ),
                    }}
                  >
                    {supplierProfile.scope3_coverage_pct != null
                      ? `${supplierProfile.scope3_coverage_pct}%`
                      : "—"}
                  </div>
                </div>
                <div className="profile-kpi-card">
                  <div className="profile-kpi-label">Traceability</div>
                  <div
                    className="profile-kpi-value"
                    style={{
                      color:
                        supplierProfile.traceability_status === "Full"
                          ? "var(--green)"
                          : supplierProfile.traceability_status === "Partial"
                            ? "var(--amber)"
                            : "var(--red)",
                    }}
                  >
                    {supplierProfile.traceability_status || "—"}
                  </div>
                </div>
              </div>

              <div className="cluster-bars">
                <h4
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--text)",
                    marginBottom: "12px",
                  }}
                >
                  ESG Cluster Scores
                </h4>
                {Object.entries(supplierProfile.clusters || {}).map(
                  ([key, val]) => {
                    const color =
                      val >= 70
                        ? "var(--green)"
                        : val >= 40
                          ? "var(--amber)"
                          : "var(--red)";
                    return (
                      <div key={key} className="cluster-bar-row">
                        <span className="cluster-name">
                          {key.replace(/_/g, " ")}
                        </span>
                        <div className="cluster-bar-track">
                          <div
                            className="cluster-bar-fill"
                            style={{ width: `${val}%`, background: color }}
                          />
                        </div>
                        <span className="cluster-val" style={{ color }}>
                          {val}
                        </span>
                      </div>
                    );
                  },
                )}
              </div>

              {supplierProfile.ml_recommendations?.length > 0 && (
                <div className="ml-recommendations">
                  <h4
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--text)",
                      marginBottom: "8px",
                    }}
                  >
                    ML Recommendations
                  </h4>
                  <ul>
                    {supplierProfile.ml_recommendations.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Scope 3 Detail Panel (SC3) */}
            <div className="panel">
              <h3 style={{ marginBottom: "16px" }}>
                GHG Protocol Scope 3 Categories
              </h3>
              <div className="scope3-detail-list">
                {scope3List.length === 0 && (
                  <div className="empty-state">No Scope 3 data available.</div>
                )}
                {scope3List.map((cat) => {
                  const pct = cat.coverage_pct || 0;
                  const color = getCoverageColor(pct);
                  const bg = getCoverageBg(pct);
                  return (
                    <div key={cat.id} className="scope3-detail-row">
                      <div className="scope3-detail-label">
                        <span className="scope3-detail-cat-id">{cat.id}</span>
                        <span className="scope3-detail-name">{cat.name}</span>
                      </div>
                      <div className="scope3-detail-bar-wrap">
                        <div className="scope3-detail-bar-track">
                          <div
                            className="scope3-detail-bar-fill"
                            style={{ width: `${pct}%`, background: color }}
                          />
                        </div>
                        <span
                          className="scope3-detail-pct"
                          style={{ color, background: bg }}
                        >
                          {pct}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {!selectedSupplier && (
          <div className="panel empty-state">
            Select a supplier from the sidebar to view their profile and Scope 3
            data.
          </div>
        )}

        {/* Geopolitical Risk Heat Map — SC4 (unchanged) */}
        {geopolitical && (
          <div className="panel">
            <h3>Geopolitical Risk — Tier 1 Supplier Countries</h3>
            <GeopoliticalRiskTable countries={geopolitical.countries} />
          </div>
        )}
      </main>
    </div>
  );
}
