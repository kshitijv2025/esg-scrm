import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import GeopoliticalRiskTable from "../components/GeopoliticalRiskTable";
import { sanitize } from "../utils/sanitize";

export default function RiskAlertsTab() {
  const [flags, setFlags] = useState(null);
  const [summary, setSummary] = useState(null);
  const [scorecard, setScorecard] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [geopolitical, setGeopolitical] = useState(null);
  const [correctiveActions, setCorrectiveActions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(null);
  const [creatingAction, setCreatingAction] = useState(null);
  const [actionForm, setActionForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    deadline: "",
  });
  const [error, setError] = useState(null);
  const [searchParams] = useSearchParams();
  const activeQuadrant = searchParams.get("quadrant");

  function loadData() {
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch("/risk/flags").then((r) => r.json()),
      apiFetch("/risk/summary").then((r) => r.json()),
      apiFetch("/risk/scorecard").then((r) => r.json()),
      apiFetch("/scope3/completeness").then((r) => r.json()),
      apiFetch("/risk/geopolitical").then((r) => r.json()),
      apiFetch("/corrective-actions").then((r) => r.json()),
    ])
      .then(([f, s, sc, comp, geo, ca]) => {
        setFlags(f);
        setSummary(s);
        setScorecard(sc);
        setCompleteness(comp);
        setGeopolitical(geo);
        setCorrectiveActions(ca);
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

  function createCorrectiveAction(flag) {
    setCreatingAction(flag.id);
    setActionForm({
      title: `Address: ${flag.flag_text?.slice(0, 80) || "Risk flag"}`,
      description: `Root cause analysis required for ${flag.cluster} flag. ${flag.flag_text || ""}`,
      priority:
        flag.severity === "CRITICAL"
          ? "critical"
          : flag.severity === "WARNING"
            ? "high"
            : "medium",
      deadline: "",
    });
  }

  function submitCorrectiveAction() {
    if (!actionForm.title.trim()) return;

    apiFetch("/corrective-actions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...actionForm,
        flag_id: creatingAction,
      }),
    })
      .then((r) => r.json())
      .then((result) => {
        // Refresh corrective actions
        return apiFetch("/corrective-actions").then((r) => r.json());
      })
      .then((ca) => {
        setCorrectiveActions(ca);
        setCreatingAction(null);
        setActionForm({
          title: "",
          description: "",
          priority: "medium",
          deadline: "",
        });
      })
      .catch((err) => {
        setError(err.message || "Failed to create corrective action");
      });
  }

  function updateActionStatus(actionId, newStatus) {
    apiFetch(`/corrective-actions/${actionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    })
      .then((r) => r.json())
      .then(() => {
        setCorrectiveActions((prev) => ({
          ...prev,
          actions: prev.actions.map((a) =>
            a.id === actionId ? { ...a, status: newStatus } : a,
          ),
        }));
      })
      .catch((err) => {
        setError(err.message || "Failed to update action");
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
              const isActive = activeQuadrant === q.id;
              return (
                <div
                  key={q.id}
                  className={`scorecard-cell ${isActive ? "scorecard-cell--active" : ""}`}
                  style={
                    isActive
                      ? {
                          borderColor: "#22c55e",
                          boxShadow: "0 0 12px rgba(34,197,94,0.3)",
                        }
                      : {}
                  }
                >
                  <div className="scorecard-id">
                    {q.id} — {q.name}
                    {isActive && (
                      <span style={{ color: "#22c55e", marginLeft: 8 }}>
                        ← Active
                      </span>
                    )}
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
                  <div
                    className="risk-flag-message"
                    dangerouslySetInnerHTML={{
                      __html: sanitize(flag.flag_text || ""),
                    }}
                  />
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
                  <button
                    className="action-btn create"
                    onClick={() => createCorrectiveAction(flag)}
                  >
                    Create Action
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
                  <div
                    className="risk-flag-message"
                    dangerouslySetInnerHTML={{
                      __html: sanitize(flag.flag_text || ""),
                    }}
                  />
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
          <GeopoliticalRiskTable countries={geopolitical.countries} />
        </div>
      )}

      {/* Corrective Actions Panel */}
      <div className="panel">
        <h3>Corrective Actions</h3>
        {correctiveActions?.actions?.length > 0 ? (
          <div className="corrective-actions-list">
            {correctiveActions.actions.map((action) => {
              const statusColors = {
                open: "#f59e0b",
                in_progress: "#3b82f6",
                completed: "#22c55e",
                cancelled: "#6b7280",
              };
              const priorityColors = {
                critical: "#ef4444",
                high: "#f97316",
                medium: "#eab308",
                low: "#6b7280",
              };
              return (
                <div key={action.id} className="action-card">
                  <div className="action-header">
                    <span
                      className="action-status"
                      style={{
                        background: statusColors[action.status] || "#6b7280",
                      }}
                    >
                      {action.status?.replace("_", " ")}
                    </span>
                    <span
                      className="action-priority"
                      style={{
                        color: priorityColors[action.priority] || "#6b7280",
                      }}
                    >
                      {action.priority}
                    </span>
                    <span className="action-deadline">
                      {action.deadline
                        ? `Due: ${action.deadline}`
                        : "No deadline"}
                    </span>
                  </div>
                  <h4 className="action-title">{action.title}</h4>
                  <p className="action-description">{action.description}</p>
                  <div className="action-footer">
                    {action.status === "open" && (
                      <button
                        className="action-btn start"
                        onClick={() =>
                          updateActionStatus(action.id, "in_progress")
                        }
                      >
                        Start
                      </button>
                    )}
                    {action.status === "in_progress" && (
                      <button
                        className="action-btn complete"
                        onClick={() =>
                          updateActionStatus(action.id, "completed")
                        }
                      >
                        Mark Complete
                      </button>
                    )}
                    {action.status !== "completed" &&
                      action.status !== "cancelled" && (
                        <button
                          className="action-btn cancel"
                          onClick={() =>
                            updateActionStatus(action.id, "cancelled")
                          }
                        >
                          Cancel
                        </button>
                      )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">No corrective actions yet</div>
        )}

        {/* Create action from flag */}
        {creatingAction && (
          <div className="action-form-overlay">
            <div className="action-form">
              <h4>Create Corrective Action</h4>
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={actionForm.title}
                  onChange={(e) =>
                    setActionForm((f) => ({ ...f, title: e.target.value }))
                  }
                  placeholder="Action title"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={actionForm.description}
                  onChange={(e) =>
                    setActionForm((f) => ({
                      ...f,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Describe the corrective action..."
                  rows={3}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Priority</label>
                  <select
                    value={actionForm.priority}
                    onChange={(e) =>
                      setActionForm((f) => ({ ...f, priority: e.target.value }))
                    }
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Deadline</label>
                  <input
                    type="date"
                    value={actionForm.deadline}
                    onChange={(e) =>
                      setActionForm((f) => ({ ...f, deadline: e.target.value }))
                    }
                  />
                </div>
              </div>
              <div className="form-actions">
                <button
                  className="btn-secondary"
                  onClick={() => setCreatingAction(null)}
                >
                  Cancel
                </button>
                <button
                  className="btn-primary"
                  onClick={submitCorrectiveAction}
                >
                  Create Action
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
