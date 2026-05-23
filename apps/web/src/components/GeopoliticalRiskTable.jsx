export default function GeopoliticalRiskTable({ countries }) {
  if (!countries || countries.length === 0) return null;

  return (
    <table className="geo-table">
      <thead>
        <tr>
          <th>Country</th>
          <th>Political Stability</th>
          <th>Trade Exposure</th>
          <th>Currency Volatility</th>
          <th>Overall Score</th>
        </tr>
      </thead>
      <tbody>
        {countries.map((c) => (
          <tr key={c.country_code}>
            <td>{c.country}</td>
            <td>
              <div className="geo-bar-container">
                <div
                  className="geo-bar-fill"
                  style={{
                    width: `${c.political_stability}%`,
                    background:
                      c.political_stability > 60
                        ? "#22c55e"
                        : c.political_stability > 40
                          ? "#f59e0b"
                          : "#ef4444",
                  }}
                />
                <span>{c.political_stability}</span>
              </div>
            </td>
            <td>
              <div className="geo-bar-container">
                <div
                  className="geo-bar-fill"
                  style={{
                    width: `${c.trade_exposure}%`,
                    background:
                      c.trade_exposure > 70
                        ? "#ef4444"
                        : c.trade_exposure > 50
                          ? "#f59e0b"
                          : "#22c55e",
                  }}
                />
                <span>{c.trade_exposure}</span>
              </div>
            </td>
            <td>
              <div className="geo-bar-container">
                <div
                  className="geo-bar-fill"
                  style={{
                    width: `${c.currency_volatility}%`,
                    background:
                      c.currency_volatility > 60
                        ? "#ef4444"
                        : c.currency_volatility > 40
                          ? "#f59e0b"
                          : "#22c55e",
                  }}
                />
                <span>{c.currency_volatility}</span>
              </div>
            </td>
            <td>
              <span
                className={`geo-score score-${c.overall_score > 60 ? "green" : c.overall_score > 40 ? "amber" : "red"}`}
              >
                {c.overall_score}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
