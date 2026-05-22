import { useState } from "react";
import { apiExport, apiFetch } from "../api/client";

const FRAMEWORKS = [
  { value: "gri", label: "GRI" },
  { value: "tcfd", label: "TCFD" },
  { value: "csrd", label: "CSRD" },
  { value: "issb", label: "ISSB" },
  { value: "sasb", label: "SASB" },
];

const FRAMEWORK_LABELS = Object.fromEntries(
  FRAMEWORKS.map((f) => [f.value, f.label]),
);

export default function ReportBuilder() {
  const [framework, setFramework] = useState("gri");
  const [period, setPeriod] = useState("2024-01-01_2024-12-31");
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState(null);

  function buildUrl() {
    return `/api/reports/pdf?framework=${encodeURIComponent(framework)}&period=${encodeURIComponent(period)}`;
  }

  async function handlePreview() {
    setError(null);
    setPreviewing(true);
    try {
      const token = localStorage.getItem("esg_token");
      const url = buildUrl();
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(text || `Preview failed (${response.status})`);
      }
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, "_blank");
    } catch (err) {
      setError(err.message || "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleDownload() {
    setError(null);
    try {
      const filename = `ESG_Report_${FRAMEWORK_LABELS[framework]}_${period}.pdf`;
      await apiExport(buildUrl(), filename);
    } catch (err) {
      setError(err.message || "Download failed");
    }
  }

  return (
    <div className="panel report-builder">
      <h2>Report Builder</h2>
      <p className="panel-subtitle">
        Generate ESG compliance reports for any framework and reporting period
      </p>

      <div className="report-builder-form">
        <div className="report-builder-select">
          <div className="field-row">
            <label htmlFor="rb-framework">Framework</label>
            <select
              id="rb-framework"
              className="input select"
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
            >
              {FRAMEWORKS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field-row">
            <label htmlFor="rb-period">Reporting Period</label>
            <input
              id="rb-period"
              type="text"
              className="input"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="YYYY-MM-DD_YYYY-MM-DD"
            />
            <span className="field-hint">
              Format: start date underscore end date, e.g. 2024-01-01_2024-12-31
            </span>
          </div>
        </div>

        <div className="report-builder-preview">
          <div className="report-builder-summary">
            <div className="summary-item">
              <span className="summary-label">Framework</span>
              <span className="summary-value">
                {FRAMEWORK_LABELS[framework]}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Period</span>
              <span className="summary-value">{period}</span>
            </div>
          </div>
        </div>

        {error && <div className="report-builder-error">{error}</div>}

        <div className="report-builder-actions">
          <button
            className="btn btn-primary"
            onClick={handlePreview}
            disabled={previewing || !framework || !period}
          >
            {previewing ? "Loading..." : "Preview Report"}
          </button>
          <button
            className="btn"
            onClick={handleDownload}
            disabled={!framework || !period}
          >
            Download Report
          </button>
        </div>
      </div>
    </div>
  );
}
