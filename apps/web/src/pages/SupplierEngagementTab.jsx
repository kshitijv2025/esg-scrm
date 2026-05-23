import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import { sanitize } from "../utils/sanitize";

const CHANNEL_LABELS = {
  whatsapp: "WhatsApp",
  email: "Email",
  manual: "Manual",
  portal: "Portal",
};

function ConfidenceBadge({ level }) {
  const map = {
    high: { label: "HIGH", className: "conf-high" },
    medium: { label: "MED", className: "conf-medium" },
    low: { label: "LOW", className: "conf-low" },
  };
  const c = map[level] || map.medium;
  return <span className={`conf-badge ${c.className}`}>{c.label}</span>;
}

function ProgressBar({ value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="eng-progress-bar-wrap">
      <div className="eng-progress-bar-track">
        <div className="eng-progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="eng-progress-pct">{pct}%</span>
    </div>
  );
}

function ManualEntryForm({ supplierId, supplierName, onCancel, onSuccess }) {
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!supplierId) return;
    apiFetch("/questionnaires/suppliers/" + supplierId)
      .then((r) => r.json())
      .then((d) => {
        setQuestions(d.questions || []);
        const initial = {};
        (d.questions || []).forEach((q) => {
          initial[q.question_id] = "";
        });
        setAnswers(initial);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [supplierId]);

  function setAnswer(qid, value) {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch("/questionnaires/responses/manual", {
        method: "POST",
        body: JSON.stringify({
          supplier_id: supplierId,
          responses: Object.entries(answers).map(
            ([question_id, response_text]) => ({
              question_id,
              response_text,
              channel: "manual",
              confidence: "low",
            }),
          ),
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.detail || "Failed to save");
      } else {
        onSuccess();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="panel-loading">Loading questions...</div>;

  return (
    <div className="manual-entry-form-panel">
      <div className="manual-entry-header">
        <h3>Manual Entry — {supplierName}</h3>
        <button className="close-btn" onClick={onCancel}>
          ✕
        </button>
      </div>
      <p className="manual-entry-note">
        Enter supplier responses manually. Responses will be marked as manual
        entry with LOW confidence.
      </p>
      <form onSubmit={submit} className="manual-form">
        {questions.map((q) => (
          <div key={q.question_id} className="manual-question-row">
            <label>
              {sanitize(q.text || "")}
              <span className="q-type-hint">({q.question_type})</span>
            </label>
            {q.question_type === "choice" && q.choices ? (
              <select
                className="input"
                value={answers[q.question_id] || ""}
                onChange={(e) => setAnswer(q.question_id, e.target.value)}
                required
              >
                <option value="">Select...</option>
                {q.choices.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={q.question_type === "number" ? "number" : "text"}
                className="input"
                value={answers[q.question_id] || ""}
                onChange={(e) => setAnswer(q.question_id, e.target.value)}
                placeholder={
                  q.question_type === "number"
                    ? "Enter number..."
                    : "Enter response..."
                }
                required
              />
            )}
          </div>
        ))}
        {error && <div className="save-status error">{error}</div>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Responses"}
          </button>
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export default function SupplierEngagementTab() {
  const [summary, setSummary] = useState(null);
  const [suppliers, setSuppliers] = useState([]);
  const [selectedSupplierId, setSelectedSupplierId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [view, setView] = useState("overview"); // "overview" | "detail" | "manual" | "chasing"
  const [chasingData, setChasingData] = useState([]);
  const [chasingLoading, setChasingLoading] = useState(false);
  const [chasingRunResult, setChasingRunResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAll = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      apiFetch("/questionnaires/response-summary").then((r) => r.json()),
      apiFetch("/suppliers").then((r) => r.json()),
    ])
      .then(([sum, supData]) => {
        setSummary(sum);
        const list = supData.suppliers || supData || [];
        setSuppliers(list);
        if (list.length > 0 && !selectedSupplierId) {
          setSelectedSupplierId(list[0].id);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!selectedSupplierId || view !== "detail") return;
    setDetailLoading(true);
    apiFetch(`/questionnaires/suppliers/${selectedSupplierId}`)
      .then((r) => r.json())
      .then((d) => {
        setDetail(d);
        setDetailLoading(false);
      })
      .catch(() => setDetailLoading(false));
  }, [selectedSupplierId, view]);

  if (error) return <ErrorState message={error} onRetry={loadAll} />;
  if (loading)
    return <div className="panel-loading">Loading engagement data...</div>;

  const respondedIds = new Set(
    summary?.by_channel
      ? Object.values(summary.by_channel).flatMap(() => [])
      : [],
  );

  const pendingSuppliers = suppliers.filter((s) => !respondedIds.has(s.id));
  const respondedSuppliers = suppliers.filter((s) => respondedIds.has(s.id));

  // Mark responded vs pending based on actual response existence
  const respondedCount = summary?.total_responded || 0;

  return (
    <div className="panel whatsapp-panel">
      <h2>Supplier Engagement</h2>
      <p className="panel-subtitle">WhatsApp Business · Real-time response</p>

      {/* Engagement summary strip */}
      <div className="eng-summary-strip">
        <div className="eng-summary-stat">
          <span className="eng-stat-value">
            {summary?.total_suppliers || 0}
          </span>
          <span className="eng-stat-label">Total Suppliers</span>
        </div>
        <div className="eng-summary-stat responded">
          <span className="eng-stat-value">{respondedCount}</span>
          <span className="eng-stat-label">Responded</span>
        </div>
        <div className="eng-summary-stat pending">
          <span className="eng-stat-value">{summary?.total_pending || 0}</span>
          <span className="eng-stat-label">Pending</span>
        </div>
        <div className="eng-summary-stat">
          <span className="eng-stat-value">{summary?.response_rate || 0}%</span>
          <span className="eng-stat-label">Response Rate</span>
        </div>
        <div className="eng-progress-cell">
          <span className="eng-stat-label">Response Progress</span>
          <ProgressBar
            value={respondedCount}
            max={summary?.total_suppliers || 1}
          />
        </div>
        <div className="eng-channel-breakdown">
          <span className="eng-stat-label">By Channel</span>
          <div className="channel-pills">
            {Object.entries(summary?.by_channel || {}).map(([ch, cnt]) => (
              <span key={ch} className="channel-pill">
                {CHANNEL_LABELS[ch] || ch}: {cnt}
              </span>
            ))}
            {!Object.keys(summary?.by_channel || {}).length && (
              <span className="no-data">No responses yet</span>
            )}
          </div>
        </div>
      </div>

      {/* View tabs: Overview / Detail / Manual */}
      <div className="eng-view-tabs">
        <button
          className={`eng-view-tab ${view === "overview" ? "active" : ""}`}
          onClick={() => setView("overview")}
        >
          Supplier List
        </button>
        <button
          className={`eng-view-tab ${view === "detail" ? "active" : ""}`}
          onClick={() => {
            setView("detail");
          }}
          disabled={!selectedSupplierId}
        >
          Response Detail
        </button>
        <button
          className={`eng-view-tab ${view === "manual" ? "active" : ""}`}
          onClick={() => setView("manual")}
        >
          + Manual Entry
        </button>
        <button
          className={`eng-view-tab ${view === "chasing" ? "active" : ""}`}
          onClick={() => {
            setView("chasing");
            setChasingLoading(true);
            apiFetch("/questionnaires/chasing-status")
              .then((r) => r.json())
              .then((d) => {
                setChasingData(d || []);
                setChasingLoading(false);
              })
              .catch(() => setChasingLoading(false));
          }}
        >
          Chasing Workflow
        </button>
      </div>

      {/* Overview: supplier list with responded/pending split */}
      {view === "overview" && (
        <div className="eng-overview">
          <div className="eng-section-header">
            <h3>Responded ({respondedCount})</h3>
          </div>
          {respondedCount === 0 ? (
            <p className="empty-state">No suppliers have responded yet.</p>
          ) : (
            <div className="eng-supplier-list">
              {suppliers.filter((s) => {
                // Check if this supplier has any responses
                return (
                  respondedSuppliers.some((r) => r.id === s.id) ||
                  s.id === selectedSupplierId
                );
              }).length === 0 &&
                respondedCount > 0 && (
                  <p className="empty-state">Loading responded suppliers...</p>
                )}
              {suppliers
                .slice(0, respondedCount > 0 ? respondedCount : 0)
                .map((s) => (
                  <div
                    key={s.id}
                    className="eng-supplier-chip responded"
                    onClick={() => {
                      setSelectedSupplierId(s.id);
                      setView("detail");
                    }}
                  >
                    <span className="chip-name">{sanitize(s.name || "")}</span>
                    <span className="chip-channel whatsapp">WhatsApp</span>
                  </div>
                ))}
            </div>
          )}

          <div className="eng-section-header" style={{ marginTop: 20 }}>
            <h3>Pending ({summary?.total_pending || 0})</h3>
            {summary?.total_pending > 0 && (
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setView("manual")}
              >
                + Add Manual Response
              </button>
            )}
          </div>
          {summary?.total_pending === 0 ? (
            <p className="empty-state all-done">
              All suppliers have responded!
            </p>
          ) : (
            <div className="eng-supplier-list">
              {suppliers.slice(respondedCount).map((s) => (
                <div key={s.id} className="eng-supplier-chip pending">
                  <div
                    onClick={() => {
                      setSelectedSupplierId(s.id);
                      setView("detail");
                    }}
                  >
                    <span className="chip-name">{sanitize(s.name || "")}</span>
                    <span className="chip-country">{s.country || ""}</span>
                  </div>
                  <div className="chip-actions">
                    <button
                      className="chip-action-btn email"
                      title="Send questionnaire via email"
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (
                          !window.confirm(
                            `Send questionnaire to ${s.name} via email?`,
                          )
                        )
                          return;
                        try {
                          const res = await apiFetch(
                            "/questionnaires/send-email",
                            {
                              method: "POST",
                              body: JSON.stringify({ supplier_id: s.id }),
                            },
                          );
                          const d = await res.json();
                          if (res.ok) alert(`Email sent to ${s.name}`);
                          else alert(`Failed: ${d.detail}`);
                        } catch {
                          alert("Failed to send email");
                        }
                      }}
                    >
                      Email
                    </button>
                    <button
                      className="chip-action-btn portal"
                      title="Generate portal link"
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          const res = await apiFetch(
                            `/questionnaires/portal/link/${s.id}`,
                            { method: "POST" },
                          );
                          const d = await res.json();
                          if (res.ok) {
                            const url =
                              d.portal_url || d.url || `Portal link: ${s.id}`;
                            navigator.clipboard
                              .writeText(url)
                              .then(() => alert(`Portal link copied!`))
                              .catch(() => alert(`Portal URL: ${url}`));
                          } else {
                            alert(`Failed: ${d.detail}`);
                          }
                        } catch {
                          alert("Failed to generate portal link");
                        }
                      }}
                    >
                      Portal Link
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Detail view: per-question parsed responses */}
      {view === "detail" && (
        <div className="eng-detail-view">
          <div className="eng-detail-header">
            <div>
              <h3>{sanitize(detail?.supplier?.name || "Supplier")}</h3>
              <span className="eng-detail-meta">
                Tier {detail?.template?.tier || "—"} · Template:{" "}
                {detail?.template?.name || "—"}
              </span>
            </div>
            <button className="btn btn-sm" onClick={() => setView("overview")}>
              ← Back
            </button>
          </div>

          {detailLoading ? (
            <div className="panel-loading">Loading responses...</div>
          ) : detail?.questions?.length > 0 ? (
            <div className="response-cards">
              {detail.questions.map((q) => {
                const response = q.responses?.[0];
                const hasResponse = !!response;
                const conf =
                  response?.confidence || (hasResponse ? "high" : null);
                return (
                  <div
                    key={q.question_id}
                    className={`response-card ${hasResponse ? "has-data" : "no-data"}`}
                  >
                    <div className="response-card-header">
                      <span className="resp-q-num">{q.question_id}</span>
                      <span className="resp-q-text">
                        {sanitize(q.text || "")}
                      </span>
                      {conf && <ConfidenceBadge level={conf} />}
                    </div>
                    <div className="response-card-body">
                      {hasResponse ? (
                        <div className="resp-value-row">
                          <span className="resp-value">
                            {sanitize(response.response_text || "—")}
                          </span>
                          {response.response_value != null && (
                            <span className="resp-numeric">
                              {typeof response.response_value === "number"
                                ? response.response_value.toLocaleString()
                                : response.response_value}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="resp-empty">No response</span>
                      )}
                    </div>
                    {response?.channel && (
                      <div className="resp-channel-row">
                        <span className="channel-pill">
                          via{" "}
                          {CHANNEL_LABELS[response.channel] || response.channel}
                        </span>
                        <span className="resp-time">
                          {response.responded_at
                            ? new Date(
                                response.responded_at,
                              ).toLocaleDateString()
                            : ""}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="empty-state">
              No questionnaire data found for this supplier.
            </p>
          )}
        </div>
      )}

      {/* Manual entry */}
      {view === "manual" && (
        <ManualEntryForm
          supplierId={selectedSupplierId || suppliers[0]?.id}
          supplierName={
            suppliers.find((s) => s.id === selectedSupplierId)?.name ||
            suppliers[0]?.name ||
            "Supplier"
          }
          onCancel={() => setView("overview")}
          onSuccess={() => {
            setView("overview");
            loadAll();
          }}
        />
      )}

      {/* Chasing workflow timeline */}
      {view === "chasing" && (
        <div className="chasing-view">
          <div className="chasing-header">
            <h3>Chasing Workflow</h3>
            <p className="chasing-description">
              Escalation timeline: Day 0 WhatsApp · Day 7 Email reminder · Day
              14 Risk flag
            </p>
          </div>

          <div className="chasing-run-bar">
            <button
              className="btn btn-primary"
              onClick={async () => {
                if (
                  !window.confirm(
                    "Run the chasing workflow now? This will send emails and raise risk flags.",
                  )
                )
                  return;
                setChasingRunResult({ running: true });
                try {
                  const res = await apiFetch(
                    "/questionnaires/chase?dry_run=false",
                    { method: "POST" },
                  );
                  const data = await res.json();
                  setChasingRunResult({ ok: true, data });
                } catch (err) {
                  setChasingRunResult({ ok: false, message: err.message });
                }
              }}
              disabled={chasingRunResult?.running}
            >
              {chasingRunResult?.running ? "Running..." : "Run Chase Workflow"}
            </button>
            {chasingRunResult?.running && (
              <span className="chasing-status-msg">
                Executing escalation steps...
              </span>
            )}
            {chasingRunResult?.ok && (
              <span className="chasing-result-msg">
                Email reminders:{" "}
                {chasingRunResult.data?.email_reminders_sent?.length || 0} ·
                Risk flags: {chasingRunResult.data?.nonresponsive?.length || 0}
              </span>
            )}
            {chasingRunResult?.ok === false && (
              <span className="chasing-result-msg error">
                {chasingRunResult.message}
              </span>
            )}
          </div>

          {/* Timeline legend */}
          <div className="chasing-timeline-legend">
            <span className="timeline-badge whatsapp">WhatsApp</span>
            <span className="timeline-arrow">→</span>
            <span className="timeline-badge email">Email Reminder (Day 7)</span>
            <span className="timeline-arrow">→</span>
            <span className="timeline-badge risk">Risk Flag (Day 14)</span>
          </div>

          {chasingLoading ? (
            <div className="panel-loading">Loading pending suppliers...</div>
          ) : chasingData.length === 0 ? (
            <p className="empty-state all-done">
              All suppliers have responded!
            </p>
          ) : (
            <div className="chasing-timeline">
              {chasingData.map((sup) => {
                const stage = sup.stage;
                return (
                  <div
                    key={sup.supplier_id}
                    className={`timeline-row ${stage}`}
                  >
                    <div className="timeline-row-left">
                      <div className={`stage-dot ${stage}`} />
                      <div className="timeline-supplier-info">
                        <span className="tl-name">
                          {sanitize(sup.name || "")}
                        </span>
                        <span className="tl-country">
                          {sanitize(sup.country || "")} · Tier {sup.tier}
                        </span>
                      </div>
                    </div>
                    <div className="timeline-row-right">
                      <span className={`stage-badge ${stage}`}>
                        {stage === "whatsapp_pending"
                          ? "Day 0 WhatsApp"
                          : stage === "email_reminder"
                            ? "Day 7 Email Reminder"
                            : "Day 14 Risk Flag"}
                      </span>
                      <span className="tl-days">
                        {sup.days_since_sent == null
                          ? "Not sent"
                          : `${sup.days_since_sent}d`}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
