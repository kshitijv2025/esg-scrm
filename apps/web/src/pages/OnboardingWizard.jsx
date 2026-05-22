import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import "./OnboardingWizard.css";

const STEPS = [
  { id: 1, title: "Industry", description: "Select your industry" },
  { id: 2, title: "ERP System", description: "Choose your ERP or data source" },
  { id: 3, title: "Initial Data", description: "Upload baseline data" },
  { id: 4, title: "Frameworks", description: "Select compliance frameworks" },
  {
    id: 5,
    title: "Alert Thresholds",
    description: "Configure monitoring alerts",
  },
];

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    industry: "",
    erp_system: "",
    uploaded_files: [],
    frameworks: [],
    alert_thresholds: [
      {
        cluster: "energy",
        warning_threshold: 1000,
        critical_threshold: 2000,
        unit: "kWh/day",
      },
      {
        cluster: "water",
        warning_threshold: 500,
        critical_threshold: 1000,
        unit: "m³/day",
      },
      {
        cluster: "emissions",
        warning_threshold: 10,
        critical_threshold: 20,
        unit: "tCO2e/day",
      },
      {
        cluster: "waste",
        warning_threshold: 100,
        critical_threshold: 500,
        unit: "kg/day",
      },
    ],
  });

  const handleNext = () => {
    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiFetch("/onboarding/wizard", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Onboarding failed");
      }

      const result = await response.json();
      if (result.success) {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleFramework = (fw) => {
    setFormData((prev) => ({
      ...prev,
      frameworks: prev.frameworks.includes(fw)
        ? prev.frameworks.filter((f) => f !== fw)
        : [...prev.frameworks, fw],
    }));
  };

  const updateThreshold = (cluster, field, value) => {
    setFormData((prev) => ({
      ...prev,
      alert_thresholds: prev.alert_thresholds.map((t) =>
        t.cluster === cluster ? { ...t, [field]: parseFloat(value) || 0 } : t,
      ),
    }));
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="wizard-step-content">
            <h3>Select Your Industry</h3>
            <p className="step-description">
              This helps us configure default ESG metrics and benchmarks for
              your sector.
            </p>
            <div className="industry-grid">
              {[
                "Garment/Textile",
                "Electronics",
                "Food & Beverage",
                "Automotive",
                "Chemicals",
                "Pharmaceuticals",
                "Construction",
                "Other",
              ].map((industry) => (
                <button
                  key={industry}
                  className={`industry-card ${formData.industry === industry ? "selected" : ""}`}
                  onClick={() => setFormData((prev) => ({ ...prev, industry }))}
                >
                  {industry}
                </button>
              ))}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="wizard-step-content">
            <h3>Select ERP System or Data Source</h3>
            <p className="step-description">
              Choose how you'll be importing ESG data. You can always change
              this later.
            </p>
            <div className="erp-grid">
              {[
                "SAP Business One",
                "SAP S/4HANA",
                "Oracle ERP",
                "Microsoft Dynamics",
                "NetSuite",
                "QuickBooks",
                "Xero",
                "CSV Import",
                "No ERP (Manual)",
              ].map((erp) => (
                <button
                  key={erp}
                  className={`erp-card ${formData.erp_system === erp ? "selected" : ""}`}
                  onClick={() =>
                    setFormData((prev) => ({ ...prev, erp_system: erp }))
                  }
                >
                  {erp}
                </button>
              ))}
            </div>
          </div>
        );

      case 3:
        return (
          <div className="wizard-step-content">
            <h3>Upload Initial Data (Optional)</h3>
            <p className="step-description">
              Upload historical ESG data to get started faster. You can skip
              this step.
            </p>
            <div className="upload-area">
              <input
                type="file"
                id="csv-upload"
                accept=".csv,.xlsx"
                onChange={(e) => {
                  const files = Array.from(e.target.files);
                  setFormData((prev) => ({
                    ...prev,
                    uploaded_files: files.map((f) => ({
                      name: f.name,
                      size: f.size,
                      type: f.type,
                    })),
                  }));
                }}
                multiple
              />
              <label htmlFor="csv-upload" className="upload-label">
                <span className="upload-icon">📁</span>
                <span>Drop files here or click to browse</span>
                <span className="upload-hint">CSV, XLSX up to 10MB</span>
              </label>
            </div>
            {formData.uploaded_files.length > 0 && (
              <div className="uploaded-files">
                {formData.uploaded_files.map((f, i) => (
                  <div key={i} className="file-item">
                    <span>{f.name}</span>
                    <span className="file-size">
                      {(f.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="wizard-step-content">
            <h3>Select Compliance Frameworks</h3>
            <p className="step-description">
              Choose the ESG reporting frameworks you need to comply with. You
              can add more later.
            </p>
            <div className="frameworks-grid">
              {[
                { id: "GRI", name: "GRI", desc: "Global Reporting Initiative" },
                {
                  id: "TCFD",
                  name: "TCFD",
                  desc: "Task Force on Climate Disclosures",
                },
                {
                  id: "CSRD",
                  name: "CSRD",
                  desc: "Corporate Sustainability Reporting",
                },
                {
                  id: "ISSB",
                  name: "ISSB",
                  desc: "International Sustainability Board",
                },
                { id: "CDP", name: "CDP", desc: "Carbon Disclosure Project" },
                {
                  id: "EcoVadis",
                  name: "EcoVadis",
                  desc: "EcoVadis Assessment",
                },
                {
                  id: "Higg FEM",
                  name: "Higg FEM",
                  desc: "Higg Facility Environmental",
                },
                { id: "SA8000", name: "SA8000", desc: "Social Accountability" },
              ].map((fw) => (
                <button
                  key={fw.id}
                  className={`framework-card ${formData.frameworks.includes(fw.id) ? "selected" : ""}`}
                  onClick={() => toggleFramework(fw.id)}
                >
                  <span className="framework-name">{fw.name}</span>
                  <span className="framework-desc">{fw.desc}</span>
                </button>
              ))}
            </div>
          </div>
        );

      case 5:
        return (
          <div className="wizard-step-content">
            <h3>Configure Alert Thresholds</h3>
            <p className="step-description">
              Set warning and critical thresholds for your key ESG metrics.
              Adjust as needed.
            </p>
            <div className="thresholds-list">
              {formData.alert_thresholds.map((threshold) => (
                <div key={threshold.cluster} className="threshold-row">
                  <div className="threshold-header">
                    <span className="cluster-name">{threshold.cluster}</span>
                    <span className="cluster-unit">{threshold.unit}</span>
                  </div>
                  <div className="threshold-inputs">
                    <div className="threshold-input-group">
                      <label>Warning</label>
                      <input
                        type="number"
                        value={threshold.warning_threshold}
                        onChange={(e) =>
                          updateThreshold(
                            threshold.cluster,
                            "warning_threshold",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div className="threshold-input-group">
                      <label>Critical</label>
                      <input
                        type="number"
                        value={threshold.critical_threshold}
                        onChange={(e) =>
                          updateThreshold(
                            threshold.cluster,
                            "critical_threshold",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="onboarding-wizard">
      <div className="wizard-header">
        <h1>Welcome to ESG SCRM</h1>
        <p>Let's set up your account in a few quick steps</p>
      </div>

      <div className="wizard-progress">
        {STEPS.map((step) => (
          <div
            key={step.id}
            className={`progress-step ${currentStep >= step.id ? "active" : ""} ${
              currentStep === step.id ? "current" : ""
            }`}
          >
            <div className="step-number">{step.id}</div>
            <div className="step-info">
              <span className="step-title">{step.title}</span>
              <span className="step-desc">{step.description}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="wizard-body">{renderStep()}</div>

      {error && <div className="wizard-error">{error}</div>}

      <div className="wizard-footer">
        {currentStep > 1 && (
          <button
            className="btn-secondary"
            onClick={handleBack}
            disabled={isLoading}
          >
            Back
          </button>
        )}
        <div className="footer-spacer" />
        {currentStep < STEPS.length ? (
          <button
            className="btn-primary"
            onClick={handleNext}
            disabled={currentStep === 1 && !formData.industry}
          >
            Continue
          </button>
        ) : (
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={isLoading || formData.frameworks.length === 0}
          >
            {isLoading ? "Setting up..." : "Complete Setup"}
          </button>
        )}
      </div>
    </div>
  );
}
