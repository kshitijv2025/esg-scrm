import { apiFetch } from "../api/client";

export default function EvidencePanel({ metricType, data, onClose }) {
  if (!data) return null;

  const { entries = [], chain_valid = true, summary = {} } = data;

  return (
    <div className="evidence-overlay" onClick={onClose}>
      <div className="evidence-panel" onClick={(e) => e.stopPropagation()}>
        <div className="evidence-header">
          <h3>Evidence Chain — {metricType}</h3>
          <button className="evidence-close" onClick={onClose}>
            &times;
          </button>
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
