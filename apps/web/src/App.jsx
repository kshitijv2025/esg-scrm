import { AuthProvider, RequireAuth, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./components/Toast";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";

function Router() {
  const { user, loading } = useAuth();
  const hash = window.location.hash.replace("#", "") || "/";

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
          background: "var(--bg)",
          color: "var(--text-secondary)",
        }}
      >
        Loading...
      </div>
    );
  }

  if (!user || hash === "/login") {
    return <LoginPage />;
  }

  return (
    <RequireAuth>
      <DashboardPage />
    </RequireAuth>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Router />
      </ToastProvider>
    </AuthProvider>
  );
}
