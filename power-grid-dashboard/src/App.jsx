import { useState, useEffect } from "react";

const API = "https://power-grid-balancer.onrender.com";

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/balance/2024-01-01T00`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p>Error: {error}</p>;
  if (!data) return <p>Loading… (first call may take ~30s if the server was asleep)</p>;

  const regions = Object.entries(data.residuals);

  return (
    <div style={{ fontFamily: "system-ui", padding: "2rem", maxWidth: 600 }}>
      <h1>Power Grid Balancer</h1>
      <p>Hour: {data.timestamp}</p>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {regions.map(([region, mw]) => (
          <li
            key={region}
            style={{
              padding: "8px 12px",
              marginBottom: 6,
              borderRadius: 8,
              background: mw >= 0 ? "#d6f0e6" : "#f7d9cf",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <strong>{region}</strong>
            <span>{mw >= 0 ? `+${mw}` : mw} MW ({mw >= 0 ? "surplus" : "short"})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}