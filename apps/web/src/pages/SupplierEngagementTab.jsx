import React, { useState, useEffect } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";

export default function SupplierEngagementTab() {
  const [suppliers, setSuppliers] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiFetch("/suppliers")
      .then((r) => r.json())
      .then((data) => {
        const list = data.suppliers || data || [];
        setSuppliers(list);
        if (list.length > 0) {
          setSelectedId(list[0].id);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err.message || "Failed to load suppliers");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    apiFetch(`/questionnaires/whatsapp-preview/${selectedId}`)
      .then((r) => r.json())
      .then((d) => {
        setPreview(d);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load supplier engagement data");
        setLoading(false);
      });
  }, [selectedId]);

  if (error) {
    return (
      <ErrorState message={error} onRetry={() => setSelectedId(selectedId)} />
    );
  }

  if (loading || !preview) {
    return <div className="panel-loading">Loading supplier data...</div>;
  }

  return (
    <div className="panel whatsapp-panel">
      <h2>Supplier Engagement</h2>
      <p className="panel-subtitle">WhatsApp Business · Real-time response</p>

      <div className="supplier-select-row">
        <select
          value={selectedId || ""}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

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
