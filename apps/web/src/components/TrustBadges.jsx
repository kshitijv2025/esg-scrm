import React, { useState } from "react";

const BADGE_DEFS = [
  {
    key: "csrd_compliant",
    label: "CSRD Compliant",
    svg: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path
          d="M8 1L10 6H15L11 9.5L12.5 15L8 11.5L3.5 15L5 9.5L1 6H6L8 1Z"
          fill="currentColor"
        />
      </svg>
    ),
    /** Shown when badge is active — describes how it was verified */
    activeHint: "CSRD/ESRS framework mappings exist for this org",
    /** Shown when badge is inactive — check could not be satisfied */
    inactiveHint: "No CSRD/ESRS framework mappings found",
  },
  {
    key: "ghg_protocol_source",
    label: "GHG Protocol Source",
    svg: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
        <path
          d="M5 8L7 10L11 6"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    activeHint: "GHG Protocol emission factors are in use",
    inactiveHint: "No GHG Protocol emission factors found",
  },
  {
    key: "audit_ready",
    label: "Audit Ready",
    svg: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect
          x="2"
          y="4"
          width="12"
          height="9"
          rx="2"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="M5 4V3C5 1.9 5.9 1 7 1h2C10.1 1 11 1.9 11 3v1"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <circle cx="8" cy="9" r="1.5" fill="currentColor" />
      </svg>
    ),
    activeHint: "All evidence chain hashes are valid",
    inactiveHint: "Evidence chain integrity check failed",
  },
  {
    key: "scope3_verified",
    label: "Scope 3 Verified",
    svg: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path
          d="M8 2C5.24 2 3 4.24 3 7c0 3 3 7 5 9 2-2 5-6 5-9 0-2.76-2.24-5-5-5z"
          fill="currentColor"
          fillOpacity="0.2"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <circle cx="8" cy="7" r="2" fill="currentColor" />
      </svg>
    ),
    activeHint: "Supplier questionnaire responses exist (>0% coverage)",
    inactiveHint: "Scope 3 coverage is 0% — no supplier responses",
  },
];

export default function TrustBadges({ badges = {} }) {
  const [tooltip, setTooltip] = useState(null);

  return (
    <div className="trust-badges">
      {BADGE_DEFS.map(({ key, label, svg, activeHint, inactiveHint }) => {
        const active = !!badges[key];
        return (
          <div
            key={key}
            className={`trust-badge${active ? " trust-badge--active" : " trust-badge--inactive"}`}
            title={active ? activeHint : inactiveHint}
            style={{ cursor: "help" }}
          >
            {svg}
            {label}
          </div>
        );
      })}
    </div>
  );
}
