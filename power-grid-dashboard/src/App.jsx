import { useState, useEffect } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { STATE_TO_REGION } from "./stateToRegion";

const API = "https://power-grid-balancer.onrender.com";
const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

function colorFor(mw) {
  if (mw === undefined) return "#e5e5e5";      // unknown region -> gray
  if (mw >= 0) return "#1D9E75";               // surplus -> teal
  return "#D85A30";                            // short -> orange/red
}

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

  const residuals = data.residuals;

  return (
    <div style={{ fontFamily: "system-ui", padding: "1.5rem", maxWidth: 900, margin: "0 auto" }}>
      <h1>US Power Grid Balancer</h1>
      <p style={{ color: "#666" }}>Hour: {data.timestamp}</p>

      <ComposableMap projection="geoAlbersUsa" style={{ width: "100%", height: "auto" }}>
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const stateName = geo.properties.name;
              const region = STATE_TO_REGION[stateName];
              const mw = region ? residuals[region] : undefined;
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={colorFor(mw)}
                  stroke="#fff"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: "none" },
                    hover: { fill: "#555", outline: "none" },
                    pressed: { outline: "none" },
                  }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>

      <div style={{ display: "flex", gap: 16, marginTop: 12, fontSize: 14 }}>
        <span style={{ background: "#1D9E75", padding: "2px 10px", borderRadius: 4, color: "#fff" }}>surplus</span>
        <span style={{ background: "#D85A30", padding: "2px 10px", borderRadius: 4, color: "#fff" }}>short</span>
      </div>
    </div>
  );
}