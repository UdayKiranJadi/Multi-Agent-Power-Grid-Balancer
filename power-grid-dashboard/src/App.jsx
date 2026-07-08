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
  if (mw === undefined) return "#22304e";
  if (mw >= 0) return "#1aa877";                 // surplus: bright teal-green
  return "#d24a28";                              // short: bright amber-red
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

  // The backend routes power multi-hop, so `transfers` contains per-hop edges.
  // A pass-through region is both a source and a destination. The TRUE end
  // receivers -- the states power is actually being delivered to -- are the
  // destinations that never forward power on: destinations minus sources.
  const sources = new Set(transfers.map(([src]) => src));
  const destinations = new Set(transfers.map(([, dst]) => dst));
  const receiving = new Set([...destinations].filter((d) => !sources.has(d)));

  const shortCount = Object.values(residuals).filter((v) => v < 0).length;
  const surplusCount = Object.values(residuals).filter((v) => v > 0).length;

  return (
    <div className="app">
      <nav className="navbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" fill="currentColor" />
            </svg>
          </span>
          <span className="brand-text">
            <span className="brand-title">Grid Balancer</span>
            <span className="brand-sub">Multi-agent · real EIA data</span>
          </span>
        </div>

        <div className="nav-controls">
          <span className={`live-badge${loading ? " is-loading" : ""}`}>
            <span className="live-dot" />
            {loading ? "SYNCING" : "LIVE"}
          </span>
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
        </div>
      </nav>

      <main className="content">
        {error && <p className="error">Error: {error}</p>}

        <div className="stats">
          <div className="stat">
            <span className="stat-num">{Object.keys(residuals).length}</span>
            <span className="stat-label">regions</span>
          </div>
          <div className="stat stat-short">
            <span className="stat-num">{shortCount}</span>
            <span className="stat-label">short</span>
          </div>
          <div className="stat stat-surplus">
            <span className="stat-num">{surplusCount}</span>
            <span className="stat-label">surplus</span>
          </div>
          <div className="stat stat-flow">
            <span className="stat-num">{receiving.size}</span>
            <span className="stat-label">receiving</span>
          </div>
        </div>

        <div className="map-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
          <ComposableMap
            projection="geoAlbersUsa"
            projectionConfig={{ scale: 1380 }}
            width={1200}
            height={640}
            style={{ width: "100%", height: "auto" }}
          >
            <Geographies geography={GEO_URL}>
              {({ geographies }) =>
                geographies
                  .filter((geo) => !NON_MAINLAND.has(geo.id.slice(0, 2)))
                  .map((geo) => {
                    const region = STATE_TO_REGION[geo.properties.name];
                    const mw = region ? residuals[region] : undefined;
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={fillFor(mw)}
                        stroke="#9fbce8"
                        strokeWidth={0.6}
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

            {/* small static node at every region */}
            {Object.entries(REGION_COORDS).map(([region, coord]) => (
              <Marker key={region} coordinates={coord}>
                <circle r={3} fill="#a8ccff" opacity={0.8} />
              </Marker>
            ))}

            {/* radar-ping beacon ONLY at the end states receiving power */}
            {[...receiving].map((region) => {
              const coord = REGION_COORDS[region];
              if (!coord) return null;
              return (
                <Marker key={`recv-${region}`} coordinates={coord}>
                  {/* soft disc that swells toward the state border */}
                  <circle r={6} fill="#5fd3ff">
                    <animate attributeName="r" from="6" to="55" dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.35" to="0" dur="1.8s" repeatCount="indefinite" />
                  </circle>
                  {/* expanding ring edge */}
                  <circle r={6} fill="none" stroke="#5fd3ff" strokeWidth={2.5}>
                    <animate attributeName="r" from="6" to="55" dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.9" to="0" dur="1.8s" repeatCount="indefinite" />
                  </circle>
                  {/* solid core */}
                  <circle r={5} fill="#9fe6ff" />
                </Marker>
              );
            })}
          </ComposableMap>
        </div>

        <div className="legend">
          <span><span className="dot" style={{ background: "#1aa877" }}></span>surplus</span>
          <span><span className="dot" style={{ background: "#d24a28" }}></span>short</span>
          <span><span className="dot dot-glow" style={{ background: "#5fd3ff" }}></span>receiving power</span>
          <span><span className="dot" style={{ background: "#5fd3ff" }}></span>power flow</span>
        </div>
      </main>
    </div>
  );
}
