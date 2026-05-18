import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";

export default function RiskAlertsTab() {
  const [flags, setFlags] = useState(null);
  const [summary, setSummary] = useState(null);
  const [scorecard, setScorecard] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [geopolitical, setGeopolitical] = useState(null);
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(null);
  const [error, setError] = useState(null);

  function loadData() {
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch("/risk/flags").then((r) => r.json()),
      apiFetch("/risk/summary").then((r) => r.json()),
      apiFetch("/risk/scorecard").then((r) => r.json()),
      apiFetch("/scope3/completeness").then((r) => r.json()),
      apiFetch("/risk/geopolitical").then((r) => r.json()),
    ])
      .then(([f, s, sc, comp, geo]) => {
        setFlags(f);
        setSummary(s);
        setScorecard(sc);
        setCompleteness(comp);
        setGeopolitical(geo);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load risk data");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadData();
  }, []);

  function acknowledgeFlag(flagId) {
    setAcknowledging(flagId);
    apiFetch(`/risk/flags/${flagId}/acknowledge`, { method: "POST" })
      .then((r) => r.json())
      .then((updated) => {
        setFlags((prev) => ({
          ...prev,
          flags: prev.flags.map((f) => (f.id === flagId ? updated : f)),
        }));
        setAcknowledging(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to acknowledge flag");
        setAcknowledging(null);
      });
  }

  if (loading) {
    return <div className="panel-loading">Loading risk data...</div>;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

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

      {/* Geopolitical Risk — fetched from API, replacing hardcoded data */}
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
    </div>
  );
}
