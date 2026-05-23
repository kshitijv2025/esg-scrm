import React from "react";

function Logo() {
  return (
    <div className="logo-wordmark">
      <svg
        width="32"
        height="32"
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="32" height="32" rx="8" fill="#22c55e" fillOpacity="0.15" />
        <path
          d="M8 24V12L16 8L24 12V24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M11 24V17H21V24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="13" r="2.5" fill="#22c55e" />
        <path
          d="M8 24H24"
          stroke="#22c55e"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span className="logo-text">Integro</span>
    </div>
  );
}

export default Logo;
