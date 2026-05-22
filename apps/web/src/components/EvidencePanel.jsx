import { apiFetch, apiExport } from "../api/client";
import { useState } from "react";

const FRAMEWORKS = [
  { value: "", label: "All Frameworks" },
  { value: "csrd", label: "CSRD" },
  { value: "gri", label: "GRI" },
  { value: "tcfd", label: "TCFD" },
  { value: "issb", label: "ISSB" },
];

export default function EvidencePanel({ metricType, data, onClose }) {
  if (!data) return null;

  const { entries = [], chain_valid = true, summary = {} } = data;
  const [period, setPeriod] = useState("");
  const [framework, setFramework] = useState("");
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (period) params.set("period", period);
      if (framework) params.set("framework", framework);
      const query = params.toString() ? `?${params.toString()}` : "";
      await apiExport(`/evidence/export${query}`, "evidence_export.zip");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="evidence-overlay" onClick={onClose}>
      <div className="evidence-panel" onClick={(e) => e.stopPropagation()}>
        <div className="evidence-header">
          <h3>Evidence Chain — {metricType}</h3>
          <button className="evidence-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="evidence-export-controls">
          <div className="export-filters">
            <input
              type="text"
              placeholder="Period (e.g. 2024-01-01_2024-12-31)"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="export-period-input"
            />
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="export-framework-select"
            >
              {FRAMEWORKS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <button
              className="btn-export-audit"
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? "Exporting..." : "Export for Audit"}
            </button>
          </div>
        </div>

        <div className="evidence-chain-status">
          <span className={`chain-badge ${chain_valid ? "valid" : "invalid"}`}>
            {chain_valid ? "Chain Valid" : "Chain Broken"}
          </span>
          {summary.total_entries > 0 && (
            <span className="chain-meta">
              {summary.total_entries} entries &middot;{" "}
              {new Date(summary.earliest).toLocaleDateString()} —{" "}
              {new Date(summary.latest).toLocaleDateString()}
            </span>
          )}
        </div>

        <div className="evidence-entries">
          {entries.length === 0 ? (
            <div className="empty-state">
              No evidence entries found for this metric.
            </div>
          ) : (
            entries.map((entry, i) => (
              <div key={i} className="evidence-entry">
                <div className="evidence-entry-header">
                  <span className="evidence-source">{entry.source}</span>
                  <span className="evidence-time">
                    {new Date(entry.recorded_at).toLocaleString()}
                  </span>
                </div>
                <div className="evidence-entry-body">
                  <div className="evidence-field">
                    <span className="evidence-label">Value</span>
                    <span className="evidence-val">
                      {entry.value} {entry.unit}
                    </span>
                  </div>
                  {entry.confidence && (
                    <div className="evidence-field">
                      <span className="evidence-label">Confidence</span>
                      <span className="evidence-val">
                        {(entry.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                  <div className="evidence-field">
                    <span className="evidence-label">Hash</span>
                    <code className="evidence-hash">
                      {entry.hash ? entry.hash.substring(0, 16) + "..." : "N/A"}
                    </code>
                  </div>
                  {entry.prev_hash && (
                    <div className="evidence-field">
                      <span className="evidence-label">Previous Hash</span>
                      <code className="evidence-hash">
                        {entry.prev_hash.substring(0, 16) + "..."}
                      </code>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
