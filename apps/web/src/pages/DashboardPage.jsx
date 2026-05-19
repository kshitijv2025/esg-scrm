import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { useToast } from "../components/Toast";
import OperationsTab from "./OperationsTab";
import SupplyChainTab from "./SupplyChainTab";
import RiskAlertsTab from "./RiskAlertsTab";
import FrameworksTab from "./FrameworksTab";
import SupplierEngagementTab from "./SupplierEngagementTab";
import EvidencePanel from "../components/EvidencePanel";
import Header from "../components/Header";

const METRIC_KEYS = [
  "energy_kwh",
  "emissions_tco2",
  "water_m3",
  "scope3_category1",
  "diesel_consumed",
  "scope3_category6",
];

const METRIC_LABELS = {
  energy_kwh: "Electricity (Scope 2)",
  emissions_tco2: "Total Emissions (Scope 1+2)",
  water_m3: "Water Withdrawal",
  scope3_category1: "Purchased Goods (Scope 3)",
  diesel_consumed: "Diesel Combustion (Scope 1)",
  scope3_category6: "Business Travel (Scope 3)",
};

function getTabFromPath(pathname) {
  if (pathname === "/" || pathname === "") return "operations";
  return pathname.replace("/", "");
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(null);
  const [trends, setTrends] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);
  const [scope3Completeness, setScope3Completeness] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const addToast = useToast();

  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = getTabFromPath(location.pathname);

  useWebSocket((event) => {
    if (event.type === "new_flag") {
      addToast({
        severity: event.data?.severity || "WARNING",
        message: event.data?.flag_text || "New risk flag detected",
        timestamp: event.timestamp,
      });
    }
  }, true);

  const loadData = useCallback(() => {
    setIsLoading(true);
    setError(null);
    Promise.all([
      apiFetch("/dashboard/live").then((r) => r.json()),
      apiFetch("/dashboard/trends").then((r) => r.json()),
      apiFetch("/risk/summary").then((r) => r.json()),
      apiFetch("/scope3/completeness").then((r) => r.json()),
    ])
      .then(([d1, d2, d3, d4]) => {
        setMetrics(d1);
        setTrends(d2.trends);
        setRiskSummary(d3);
        setScope3Completeness(d4);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function showEvidence(metricType) {
    setSelectedMetric(metricType);
    apiFetch(`/evidence/drilldown/${metricType}`)
      .then((r) => r.json())
      .then((d) => setEvidence(d))
      .catch(() => {});
  }

  const tabProps = {
    metrics,
    trends,
    riskSummary,
    scope3Completeness,
    isLoading,
    error,
    onRetry: loadData,
    showEvidence,
    metricKeys: METRIC_KEYS,
    metricLabels: METRIC_LABELS,
  };

  return (
    <div className="app">
      <Header />
      <main className="app-main">
        {activeTab === "operations" && <OperationsTab {...tabProps} />}
        {activeTab === "supply-chain" && <SupplyChainTab />}
        {activeTab === "risk-alerts" && <RiskAlertsTab />}
        {activeTab === "frameworks" && <FrameworksTab />}
        {activeTab === "supplier-engagement" && <SupplierEngagementTab />}
      </main>
      {evidence && (
        <EvidencePanel
          metricType={selectedMetric}
          data={evidence}
          onClose={() => setEvidence(null)}
        />
      )}
    </div>
  );
}
