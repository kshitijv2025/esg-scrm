import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";

const PLAN_FEATURES = {
  starter: [
    "Up to 5 suppliers",
    "Basic ESG reporting",
    "Scope 1 & 2 emissions tracking",
    "Email support",
    "Standard templates",
    "Monthly reports",
  ],
  professional: [
    "Up to 50 suppliers",
    "Advanced ESG analytics",
    "Full Scope 3 tracking",
    "Priority support",
    "Custom templates",
    "Real-time dashboards",
    "API access",
    "Multi-language (EN/BN/VI)",
  ],
  enterprise: [
    "Unlimited suppliers",
    "Custom integrations",
    "Full Scope 3 + supply chain",
    "Dedicated account manager",
    "White-label reports",
    "Advanced security & SSO",
    "SLA guarantee",
    "Onboarding support",
  ],
};

const COMPARISON_DATA = [
  {
    feature: "Suppliers",
    starter: "5",
    professional: "50",
    enterprise: "Unlimited",
  },
  {
    feature: "Emissions tracking",
    starter: "Scope 1 & 2",
    professional: "Full Scope 3",
    enterprise: "Full Scope 3 + chain",
  },
  {
    feature: "Reporting",
    starter: "Monthly",
    professional: "Real-time",
    enterprise: "Real-time + custom",
  },
  {
    feature: "Support",
    starter: "Email",
    professional: "Priority",
    enterprise: "Dedicated manager",
  },
  {
    feature: "Templates",
    starter: "Standard",
    professional: "Custom",
    enterprise: "White-label",
  },
  {
    feature: "API access",
    starter: false,
    professional: true,
    enterprise: true,
  },
  {
    feature: "Multi-language",
    starter: false,
    professional: true,
    enterprise: true,
  },
  {
    feature: "SSO / Advanced security",
    starter: false,
    professional: false,
    enterprise: true,
  },
  {
    feature: "SLA guarantee",
    starter: false,
    professional: false,
    enterprise: true,
  },
];

function CheckIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M13.5 4.5L6.5 11.5L2.5 7.5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 4L12 12M12 4L4 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PlanCard({ plan, isPopular, onSelect }) {
  const cardStyle = {
    background: isPopular
      ? "linear-gradient(145deg, #162119 0%, #1d2a22 100%)"
      : "var(--surface2)",
    border: isPopular ? "2px solid var(--green)" : "1px solid var(--border)",
    borderRadius: "16px",
    padding: isPopular ? "32px 28px" : "28px 24px",
    width: isPopular ? "340px" : "300px",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    position: "relative",
    boxShadow: isPopular ? "0 0 40px rgba(34, 197, 94, 0.15)" : "none",
    transform: isPopular ? "scale(1.05)" : "scale(1)",
    transition: "all 0.2s ease",
  };

  const badgeStyle = {
    position: "absolute",
    top: "-12px",
    left: "50%",
    transform: "translateX(-50%)",
    background: "var(--green)",
    color: "#080e0c",
    fontSize: "0.7rem",
    fontWeight: "700",
    padding: "4px 16px",
    borderRadius: "999px",
    letterSpacing: "0.05em",
    textTransform: "uppercase",
  };

  const nameStyle = {
    fontSize: "1.25rem",
    fontWeight: "700",
    color: "var(--text)",
  };

  const priceStyle = {
    display: "flex",
    alignItems: "baseline",
    gap: "4px",
  };

  const priceAmountStyle = {
    fontSize: isPopular ? "3rem" : "2.5rem",
    fontWeight: "800",
    color: "var(--green)",
    lineHeight: "1",
  };

  const pricePeriodStyle = {
    fontSize: "0.875rem",
    color: "var(--text-muted)",
  };

  const featuresStyle = {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    flex: "1",
  };

  const featureItemStyle = {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    fontSize: "0.875rem",
    color: "var(--text-dim)",
  };

  const checkColor = { color: "var(--green)" };
  const xColor = { color: "var(--text-muted)" };

  const buttonStyle = {
    background: isPopular ? "var(--green)" : "transparent",
    border: isPopular ? "none" : "1px solid var(--green-dim)",
    color: isPopular ? "#080e0c" : "var(--green)",
    padding: "12px 24px",
    borderRadius: "8px",
    fontSize: "0.9rem",
    fontWeight: "600",
    fontFamily: "var(--font)",
    cursor: "pointer",
    transition: "all 0.15s",
    width: "100%",
  };

  const features = PLAN_FEATURES[plan.id] || [];

  return (
    <div style={cardStyle}>
      {isPopular && <div style={badgeStyle}>Most Popular</div>}

      <div>
        <div style={nameStyle}>{plan.name}</div>
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--text-muted)",
            marginTop: "4px",
          }}
        >
          {plan.description}
        </p>
      </div>

      <div style={priceStyle}>
        <span style={priceAmountStyle}>{plan.price}</span>
        <span style={pricePeriodStyle}>/month</span>
      </div>

      <div style={featuresStyle}>
        {features.map((feature, i) => (
          <div key={i} style={featureItemStyle}>
            <span style={checkColor}>
              <CheckIcon />
            </span>
            {feature}
          </div>
        ))}
      </div>

      <button
        style={buttonStyle}
        onClick={onSelect}
        onMouseOver={(e) => {
          if (!isPopular) {
            e.target.style.background = "rgba(34, 197, 94, 0.1)";
          }
        }}
        onMouseOut={(e) => {
          if (!isPopular) {
            e.target.style.background = "transparent";
          }
        }}
      >
        Start Free Trial
      </button>
    </div>
  );
}

function ComparisonTable() {
  const headerStyle = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 1fr",
    gap: "12px",
    padding: "16px 20px",
    background: "var(--surface)",
    borderRadius: "12px 12px 0 0",
    borderBottom: "1px solid var(--border)",
  };

  const cellStyle = {
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "var(--text-dim)",
  };

  const rowStyle = {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 1fr",
    gap: "12px",
    padding: "14px 20px",
    borderBottom: "1px solid var(--border)",
    alignItems: "center",
  };

  const featureCellStyle = {
    fontSize: "0.875rem",
    color: "var(--text)",
  };

  const valueCellStyle = {
    fontSize: "0.875rem",
    color: "var(--text-dim)",
    textAlign: "center",
  };

  return (
    <div style={{ marginTop: "64px", maxWidth: "1000px" }}>
      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: "700",
          marginBottom: "24px",
          textAlign: "center",
        }}
      >
        Compare Plans
      </h2>

      <div
        style={{
          background: "var(--surface2)",
          borderRadius: "12px",
          border: "1px solid var(--border)",
          overflow: "hidden",
        }}
      >
        <div style={headerStyle}>
          <span style={cellStyle}>Feature</span>
          <span
            style={{ ...cellStyle, textAlign: "center", color: "var(--text)" }}
          >
            Starter
          </span>
          <span
            style={{ ...cellStyle, textAlign: "center", color: "var(--green)" }}
          >
            Professional
          </span>
          <span
            style={{ ...cellStyle, textAlign: "center", color: "var(--text)" }}
          >
            Enterprise
          </span>
        </div>

        {COMPARISON_DATA.map((row, i) => (
          <div key={i} style={rowStyle}>
            <span style={featureCellStyle}>{row.feature}</span>
            <span style={valueCellStyle}>
              {typeof row.starter === "boolean" ? (
                row.starter ? (
                  <span style={{ color: "var(--green)" }}>
                    <CheckIcon />
                  </span>
                ) : (
                  <span style={{ color: "var(--text-muted)" }}>
                    <XIcon />
                  </span>
                )
              ) : (
                row.starter
              )}
            </span>
            <span style={valueCellStyle}>
              {typeof row.professional === "boolean" ? (
                row.professional ? (
                  <span style={{ color: "var(--green)" }}>
                    <CheckIcon />
                  </span>
                ) : (
                  <span style={{ color: "var(--text-muted)" }}>
                    <XIcon />
                  </span>
                )
              ) : (
                row.professional
              )}
            </span>
            <span style={valueCellStyle}>
              {typeof row.enterprise === "boolean" ? (
                row.enterprise ? (
                  <span style={{ color: "var(--green)" }}>
                    <CheckIcon />
                  </span>
                ) : (
                  <span style={{ color: "var(--text-muted)" }}>
                    <XIcon />
                  </span>
                )
              ) : (
                row.enterprise
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  const cardSkeletonStyle = {
    background: "var(--surface2)",
    border: "1px solid var(--border)",
    borderRadius: "16px",
    padding: "28px 24px",
    width: "300px",
    height: "420px",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
  };

  const shimmerStyle = {
    background:
      "linear-gradient(90deg, var(--surface3) 25%, var(--surface2) 50%, var(--surface3) 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.5s infinite",
    borderRadius: "8px",
  };

  return (
    <>
      {[1, 2, 3].map((i) => (
        <div key={i} style={cardSkeletonStyle}>
          <div style={{ ...shimmerStyle, height: "24px", width: "60%" }} />
          <div style={{ ...shimmerStyle, height: "60px", width: "80%" }} />
          <div style={{ ...shimmerStyle, height: "120px", width: "100%" }} />
          <div
            style={{
              ...shimmerStyle,
              height: "48px",
              width: "100%",
              marginTop: "auto",
            }}
          />
        </div>
      ))}
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </>
  );
}

export default function PricingPage() {
  const [plans, setPlans] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchPlans() {
      try {
        const response = await apiFetch("/billing/plans");
        const data = await response.json();
        setPlans(
          data.plans || [
            {
              id: "starter",
              name: "Starter",
              description: "For small teams getting started",
              price: "$29",
            },
            {
              id: "professional",
              name: "Professional",
              description: "For growing businesses",
              price: "$99",
            },
            {
              id: "enterprise",
              name: "Enterprise",
              description: "For large organizations",
              price: "$299",
            },
          ],
        );
      } catch (err) {
        setError(err.message || "Failed to load pricing plans");
        // Fallback to default plans on error
        setPlans([
          {
            id: "starter",
            name: "Starter",
            description: "For small teams getting started",
            price: "$29",
          },
          {
            id: "professional",
            name: "Professional",
            description: "For growing businesses",
            price: "$99",
          },
          {
            id: "enterprise",
            name: "Enterprise",
            description: "For large organizations",
            price: "$299",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }
    fetchPlans();
  }, []);

  const handleSelectPlan = (planId) => {
    navigate("/onboarding", { state: { selectedPlan: planId } });
  };

  const containerStyle = {
    minHeight: "100vh",
    background: "var(--bg)",
    padding: "80px 24px",
  };

  const headerStyle = {
    textAlign: "center",
    marginBottom: "48px",
  };

  const titleStyle = {
    fontSize: "2.5rem",
    fontWeight: "800",
    color: "var(--text)",
    marginBottom: "16px",
    letterSpacing: "-0.02em",
  };

  const subtitleStyle = {
    fontSize: "1.125rem",
    color: "var(--text-dim)",
    maxWidth: "500px",
    margin: "0 auto",
  };

  const cardsContainerStyle = {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "24px",
    flexWrap: "wrap",
    marginBottom: "32px",
  };

  const errorStyle = {
    textAlign: "center",
    padding: "20px",
    background: "rgba(239, 68, 68, 0.1)",
    border: "1px solid var(--red-dim)",
    borderRadius: "12px",
    color: "var(--red)",
    marginBottom: "24px",
    maxWidth: "600px",
    margin: "0 auto 24px auto",
  };

  return (
    <div style={containerStyle}>
      <style>{`
        @media (max-width: 768px) {
          .pricing-cards {
            flex-direction: column !important;
          }
          .pricing-cards > div {
            width: 100% !important;
            max-width: 340px;
            transform: none !important;
          }
        }
      `}</style>

      <div style={headerStyle}>
        <h1 style={titleStyle}>Simple, Transparent Pricing</h1>
        <p style={subtitleStyle}>
          Choose the plan that fits your organization. All plans include a
          14-day free trial.
        </p>
      </div>

      {error && <div style={errorStyle}>{error}</div>}

      {loading ? (
        <div className="pricing-cards" style={cardsContainerStyle}>
          <LoadingSkeleton />
        </div>
      ) : (
        <div className="pricing-cards" style={cardsContainerStyle}>
          {plans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isPopular={plan.id === "professional"}
              onSelect={() => handleSelectPlan(plan.id)}
            />
          ))}
        </div>
      )}

      <ComparisonTable />
    </div>
  );
}
