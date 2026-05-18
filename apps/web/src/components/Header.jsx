import { useAuth } from "../contexts/AuthContext";
import Logo from "./Logo";

const TABS = [
  { id: "operations", label: "Operations" },
  { id: "supply-chain", label: "Supply Chain" },
  { id: "risk-alerts", label: "Risk Alerts" },
  { id: "frameworks", label: "Frameworks" },
  { id: "supplier-engagement", label: "Engagement" },
];

export default function Header({ activeTab, onTabChange }) {
  const { user, logout } = useAuth();

  return (
    <header className="app-header">
      <div className="header-left">
        <Logo />
        <div className="header-divider" />
        <div className="header-org">
          <strong>{user?.full_name || "User"}</strong>
          <span>{user?.email || ""}</span>
        </div>
      </div>

      <nav className="header-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`header-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="header-right">
        <button className="logout-btn" onClick={logout}>
          Logout
        </button>
      </div>
    </header>
  );
}
