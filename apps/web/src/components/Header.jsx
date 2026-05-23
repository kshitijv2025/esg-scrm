import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import Logo from "./Logo";
import LanguageSelector from "./LanguageSelector";
import { sanitize } from "../utils/sanitize";

const TABS = [
  { id: "operations", label: "Operations" },
  { id: "supply-chain", label: "Supply Chain" },
  { id: "risk-alerts", label: "Risk Alerts" },
  { id: "frameworks", label: "Frameworks" },
  { id: "supplier-engagement", label: "Engagement" },
  { id: "template-builder", label: "Templates" },
  { id: "reports", label: "Report Builder" },
  { id: "admin-settings", label: "Admin" },
];

function getTabFromPath(pathname) {
  if (pathname === "/" || pathname === "") return "operations";
  return pathname.replace("/", "");
}

export default function Header({ locale, onLocaleChange }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = getTabFromPath(location.pathname);

  return (
    <header className="app-header">
      <div className="header-left">
        <Logo />
        <div className="header-divider" />
        <div className="header-org">
          <strong>{sanitize(user?.full_name || "User")}</strong>
          <span>{sanitize(user?.email || "")}</span>
        </div>
      </div>

      <nav className="header-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`header-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => navigate(`/${tab.id}`)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <LanguageSelector value={locale} onChange={onLocaleChange} />
        <button className="logout-btn" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
