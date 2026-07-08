import { useState, useEffect } from "react";
import { ComposableMap, Geographies, Geography, Line, Marker } from "react-simple-maps";
import { STATE_TO_REGION } from "./stateToRegion";
import { REGION_COORDS } from "./regionCoords";
import "./App.css";

const API = "https://power-grid-balancer.onrender.com";
const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

const MIN_HOUR = "2024-01-01T00";
const MAX_HOUR = "2024-02-01T00";
const NON_MAINLAND = new Set(["02", "15", "72", "78", "60", "66", "69"]);

function fillFor(mw) {
  if (mw === undefined) return "#182238";
  if (mw >= 0) return "#0d6b50";                 // surplus: teal
  return "#8a2f18";                              // short: amber-red
}

export default function App() {
  const [hour, setHour] = useState(MIN_HOUR);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/balance/${hour}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [hour]);

  const residuals = data?.residuals || {};
  const transfers = data?.national_transfers || [];

  // regions that RECEIVE power this hour (destinations of transfers) -> these blink
  const receiving = new Set(transfers.map(([, dst]) => dst));

  return (
    <div className="dashboard">
      <h1>US Power Grid Balancer</h1>
      <p className="subtitle">Live multi-agent grid balancing · real EIA data</p>

      <div className="controls">
        <label htmlFor="hour">Hour</label>
        <input
          id="hour"
          type="datetime-local"
          step="3600"
          min={MIN_HOUR + ":00"}
          max={MAX_HOUR + ":00"}
          value={hour + ":00"}
          onChange={(e) => { const v = e.target.value.slice(0, 13); if (v) setHour(v); }}
        />
        {loading && <span style={{ fontSize: 13, color: "#5c6a85" }}>loading…</span>}
      </div>

      {error && <p style={{ color: "#e2704a" }}>Error: {error}</p>}

      <div className="map-wrap" style={{ opacity: loading ? 0.6 : 1, transition: "opacity 0.2s" }}>
        <ComposableMap
          projection="geoAlbersUsa"
          width={1200}
          height={700}
          style={{ width: "100%", height: "auto" }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies
                .filter((geo) => !NON_MAINLAND.has(geo.id.slice(0, 2)))
                .map((geo) => {
                  const region = STATE_TO_REGION[geo.properties.name];
                  const mw = region ? residuals[region] : undefined;
                  const isReceiving = region && receiving.has(region);
                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      className={isReceiving ? "receiving-glow" : ""}
                      fill={fillFor(mw)}
                      stroke="#6f93cc"
                      strokeWidth={0.7}
                      style={{
                        default: { outline: "none" },
                        hover: { fill: "#2a3a5c", outline: "none" },
                        pressed: { outline: "none" },
                      }}
                    />
                  );
                })
            }
          </Geographies>

          {transfers.map(([src, dst], i) => {
            const from = REGION_COORDS[src];
            const to = REGION_COORDS[dst];
            if (!from || !to) return null;
            return (
              <Line
                key={i}
                className="flow-line"
                from={from}
                to={to}
                stroke="#5fd3ff"
                strokeWidth={2}
                strokeLinecap="round"
              />
            );
          })}

          {Object.entries(REGION_COORDS).map(([region, coord]) => (
            <Marker key={region} coordinates={coord}>
              <circle r={3} fill="#a8ccff" opacity={0.8} />
            </Marker>
          ))}
        </ComposableMap>
      </div>

      <div className="legend">
        <span><span className="dot" style={{ background: "#0d6b50" }}></span>surplus</span>
        <span><span className="dot" style={{ background: "#8a2f18" }}></span>short</span>
        <span><span className="dot" style={{ background: "#a8ccff", animation: "pulse 1.4s infinite" }}></span>receiving power (glowing)</span>
        <span><span className="dot" style={{ background: "#5fd3ff" }}></span>power flow</span>
      </div>
    </div>
  );
}