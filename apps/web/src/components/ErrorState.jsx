export function ErrorState({ message, onRetry }) {
  return (
    <div className="error-state">
      <div className="error-state-icon">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      </div>
      <div className="error-state-message">
        {message || "Something went wrong"}
      </div>
      {onRetry && (
        <button className="error-state-retry" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
