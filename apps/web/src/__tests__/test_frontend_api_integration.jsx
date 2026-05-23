import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";

// ---------------------------------------------------------------------------
// MetricCard tests
// ---------------------------------------------------------------------------
describe("MetricCard", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("renders label, value, and unit correctly", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Electricity (Scope 2)"
        value={12345.67}
        unit="kWh"
        confidence="HIGH"
        trend="+2.1%"
        chainValid={true}
      />,
    );

    expect(screen.getByText("Electricity (Scope 2)")).toBeInTheDocument();
    expect(screen.getByText(/12,345.67/)).toBeInTheDocument();
    expect(screen.getByText("kWh")).toBeInTheDocument();
  });

  it("renders HIGH confidence badge with green color", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Water"
        value={500}
        unit="m3"
        confidence="HIGH"
        trend="+1%"
        chainValid={true}
      />,
    );

    const badge = screen.getByText("HIGH");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveStyle({ background: "#22c55e" });
  });

  it("renders MEDIUM confidence badge with amber color", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Emissions"
        value={999}
        unit="tCO2e"
        confidence="MEDIUM"
        trend="-0.5%"
        chainValid={true}
      />,
    );

    const badge = screen.getByText("MEDIUM");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveStyle({ background: "#f59e0b" });
  });

  it("renders LOW confidence badge with red color", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Diesel"
        value={200}
        unit="litres"
        confidence="LOW"
        trend="+5%"
        chainValid={true}
      />,
    );

    const badge = screen.getByText("LOW");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveStyle({ background: "#ef4444" });
  });

  it("shows chain broken badge when chainValid is false", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Scope 3"
        value={0}
        unit="tCO2e"
        confidence="HIGH"
        trend="0%"
        chainValid={false}
      />,
    );

    expect(screen.getByText("Chain Broken")).toBeInTheDocument();
  });

  it("does not show chain broken badge when chainValid is true", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");

    render(
      <MetricCard
        label="Scope 3"
        value={100}
        unit="tCO2e"
        confidence="HIGH"
        trend="+1%"
        chainValid={true}
      />,
    );

    expect(screen.queryByText("Chain Broken")).not.toBeInTheDocument();
  });

  it("calls onClick when card is clicked", async () => {
    const { default: MetricCard } = await import("../components/MetricCard");
    const onClick = vi.fn();

    render(
      <MetricCard
        label="Energy"
        value={50}
        unit="kWh"
        confidence="HIGH"
        trend="+3%"
        chainValid={true}
        onClick={onClick}
      />,
    );

    fireEvent.click(screen.getByText("Electricity (Scope 2)").parentElement);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// TrustBadges tests
// ---------------------------------------------------------------------------
describe("TrustBadges", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("renders all badge labels", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(<TrustBadges badges={{}} />);

    expect(screen.getByText("CSRD Compliant")).toBeInTheDocument();
    expect(screen.getByText("GHG Protocol Source")).toBeInTheDocument();
    expect(screen.getByText("Audit Ready")).toBeInTheDocument();
    expect(screen.getByText("Scope 3 Verified")).toBeInTheDocument();
  });

  it("marks active badges with active class", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(<TrustBadges badges={{ csrd_compliant: true }} />);

    const csrdBadge = screen.getByText("CSRD Compliant").parentElement;
    expect(csrdBadge).toHaveClass("trust-badge--active");
  });

  it("marks inactive badges with inactive class", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(<TrustBadges badges={{ csrd_compliant: true }} />);

    const ghgBadge = screen.getByText("GHG Protocol Source").parentElement;
    expect(ghgBadge).toHaveClass("trust-badge--inactive");
  });

  it("renders all four badges even when empty object passed", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(<TrustBadges badges={{}} />);

    const allBadges = screen.getAllByRole("button", { hidden: true });
    // trust badges are divs with specific class
    const badgeDivs = document.querySelectorAll(".trust-badge--inactive");
    expect(badgeDivs.length).toBe(4);
  });

  it("renders multiple active badges", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(
      <TrustBadges badges={{ csrd_compliant: true, audit_ready: true }} />,
    );

    const activeBadges = document.querySelectorAll(".trust-badge--active");
    expect(activeBadges.length).toBe(2);
  });

  it("handles empty badges gracefully", async () => {
    const { default: TrustBadges } = await import("../components/TrustBadges");

    render(<TrustBadges badges={null} />);

    // Should not crash and render all badges as inactive
    const badgeDivs = document.querySelectorAll(".trust-badge--inactive");
    expect(badgeDivs.length).toBe(4);
  });
});

// ---------------------------------------------------------------------------
// OperationsTab loading state tests
// ---------------------------------------------------------------------------
describe("OperationsTab", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("renders skeleton loading cards when isLoading is true", async () => {
    const { default: OperationsTab } = await import("../pages/OperationsTab");

    render(
      <OperationsTab
        metrics={null}
        trends={null}
        riskSummary={null}
        scope3Completeness={null}
        isLoading={true}
        showEvidence={vi.fn()}
      />,
    );

    // Should show 6 skeleton cards
    const skeletons = document.querySelectorAll(".skeleton-card");
    expect(skeletons.length).toBe(6);
  });

  it("renders metric cards when metrics data is available", async () => {
    const { default: OperationsTab } = await import("../pages/OperationsTab");

    const mockMetrics = {
      metrics: {
        energy_kwh: {
          value: 1000,
          unit: "kWh",
          confidence: "HIGH",
          trend: "+5%",
          chain_valid: true,
        },
        emissions_tco2: {
          value: 50,
          unit: "tCO2e",
          confidence: "MEDIUM",
          trend: "-2%",
          chain_valid: true,
        },
        water_m3: {
          value: 200,
          unit: "m3",
          confidence: "HIGH",
          trend: "+1%",
          chain_valid: true,
        },
        scope3_category1: {
          value: 300,
          unit: "tCO2e",
          confidence: "LOW",
          trend: "+3%",
          chain_valid: true,
        },
        diesel_consumed: {
          value: 75,
          unit: "litres",
          confidence: "MEDIUM",
          trend: "0%",
          chain_valid: true,
        },
        scope3_category6: {
          value: 25,
          unit: "tCO2e",
          confidence: "HIGH",
          trend: "-1%",
          chain_valid: true,
        },
      },
    };

    render(
      <OperationsTab
        metrics={mockMetrics}
        trends={[]}
        riskSummary={{}}
        scope3Completeness={{}}
        isLoading={false}
        showEvidence={vi.fn()}
      />,
    );

    // Metric cards should be rendered
    const metricLabels = screen.getAllByText(
      /Electricity \(Scope 2\)|Total Emissions \(Scope 1\+2\)|Water Withdrawal|Purchased Goods \(Scope 3\)|Diesel Combustion \(Scope 1\)|Business Travel \(Scope 3\)/,
    );
    expect(metricLabels.length).toBe(6);
  });

  it("renders failed to load message when metrics is null and not loading", async () => {
    const { default: OperationsTab } = await import("../pages/OperationsTab");

    render(
      <OperationsTab
        metrics={null}
        trends={null}
        riskSummary={null}
        scope3Completeness={null}
        isLoading={false}
        showEvidence={vi.fn()}
      />,
    );

    expect(screen.getByText("Failed to load metrics")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// DashboardPage API integration tests
// ---------------------------------------------------------------------------
describe("DashboardPage API integration", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("DashboardPage calls correct API endpoints on mount", async () => {
    // Set up token in localStorage
    const { setToken } = await import("../api/client");
    setToken("test-jwt-token");

    const mockLiveData = {
      metrics: {
        energy_kwh: {
          value: 1000,
          unit: "kWh",
          confidence: "HIGH",
          trend: "+5%",
          chain_valid: true,
        },
        emissions_tco2: {
          value: 50,
          unit: "tCO2e",
          confidence: "MEDIUM",
          trend: "-2%",
          chain_valid: true,
        },
        water_m3: {
          value: 200,
          unit: "m3",
          confidence: "HIGH",
          trend: "+1%",
          chain_valid: true,
        },
        scope3_category1: {
          value: 300,
          unit: "tCO2e",
          confidence: "LOW",
          trend: "+3%",
          chain_valid: true,
        },
        diesel_consumed: {
          value: 75,
          unit: "litres",
          confidence: "MEDIUM",
          trend: "0%",
          chain_valid: true,
        },
        scope3_category6: {
          value: 25,
          unit: "tCO2e",
          confidence: "HIGH",
          trend: "-1%",
          chain_valid: true,
        },
      },
    };
    const mockTrends = { trends: [] };
    const mockRiskSummary = { flags: [], counts: {} };
    const mockScope3Completeness = { completeness: 0 };
    const mockTrustBadges = { badges: {} };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url) => {
        if (url.includes("/api/dashboard/live")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockLiveData),
          });
        }
        if (url.includes("/api/dashboard/trends")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockTrends),
          });
        }
        if (url.includes("/api/risk/summary")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockRiskSummary),
          });
        }
        if (url.includes("/api/scope3/completeness")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockScope3Completeness),
          });
        }
        if (url.includes("/api/trust/badges")) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(mockTrustBadges),
          });
        }
        return Promise.resolve({ ok: false, status: 404 });
      }),
    );

    const { default: DashboardPage } = await import("../pages/DashboardPage");

    render(<DashboardPage locale="en" onLocaleChange={vi.fn()} />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/dashboard/operations-summary",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-jwt-token",
          }),
        }),
      );
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/dashboard/trends",
      expect.any(Object),
    );
    expect(fetch).toHaveBeenCalledWith("/api/risk/summary", expect.any(Object));
    expect(fetch).toHaveBeenCalledWith(
      "/api/scope3/completeness",
      expect.any(Object),
    );
    expect(fetch).toHaveBeenCalledWith("/api/trust/badges", expect.any(Object));
  });

  it("DashboardPage shows loading state initially", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(
        () => new Promise(() => {}), // Never resolves to keep loading state
      ),
    );

    const { setToken } = await import("../api/client");
    setToken("test-jwt-token");

    const { default: DashboardPage } = await import("../pages/DashboardPage");

    render(<DashboardPage locale="en" onLocaleChange={vi.fn()} />);

    // Should show skeleton loading cards
    const skeletons = document.querySelectorAll(".skeleton-card");
    expect(skeletons.length).toBe(6);
  });
});
