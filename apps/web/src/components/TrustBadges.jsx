import React from "react";

function TrustBadges() {
  return (
    <div className="trust-badges">
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 1L10 6H15L11 9.5L12.5 15L8 11.5L3.5 15L5 9.5L1 6H6L8 1Z"
            fill="#22c55e"
          />
        </svg>
        CSRD Compliant
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="#22c55e" strokeWidth="1.5" />
          <path
            d="M5 8L7 10L11 6"
            stroke="#22c55e"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        GHG Protocol Source
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect
            x="2"
            y="4"
            width="12"
            height="9"
            rx="2"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <path
            d="M5 4V3C5 1.9 5.9 1 7 1h2C10.1 1 11 1.9 11 3v1"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <circle cx="8" cy="9" r="1.5" fill="#22c55e" />
        </svg>
        Audit Ready
      </div>
      <div className="trust-badge">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path
            d="M8 2C5.24 2 3 4.24 3 7c0 3 3 7 5 9 2-2 5-6 5-9 0-2.76-2.24-5-5-5z"
            fill="#22c55e"
            fillOpacity="0.2"
            stroke="#22c55e"
            strokeWidth="1.5"
          />
          <circle cx="8" cy="7" r="2" fill="#22c55e" />
        </svg>
        Scope 3 Verified
      </div>
    </div>
  );
}

export default TrustBadges;
