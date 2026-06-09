import { useState } from "react"
import Sidebar from "../../src/components/Sidebar"
import type { Batter, Pitcher } from "../../src/data/mockPlayers"
import { MOCK_HISTORY } from "../../src/data/mockSimulations"

// ─── Helpers ─────────────────────────────────────────────────────────────────

function initials(name: string) {
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
}

function mlbHeadshotUrl(mlbamId: number) {
  return `https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/${mlbamId}/headshot/67/current`
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PlayerPhoto({ mlbamId, name, color, size = 28 }: { mlbamId: number; name: string; color: string; size?: number }) {
  const [imgError, setImgError] = useState(false)
  if (imgError) {
    return (
      <div style={{ width: size, height: size, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: size * 0.32, fontWeight: 700, background: `${color}22`, color, border: `0.5px solid ${color}55` }}>
        {initials(name)}
      </div>
    )
  }
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", flexShrink: 0, overflow: "hidden", background: `${color}15`, border: `0.5px solid ${color}40` }}>
      <img
        src={mlbHeadshotUrl(mlbamId)}
        alt={name}
        style={{ width: "100%", height: "120%", objectFit: "cover", objectPosition: "top 20%", marginTop: "-10%"}}
        onError={() => setImgError(true)}
      />
    </div>
  )
}

// Stacked player avatars with overflow count
function PlayerStack({ players }: { players: (Batter | Pitcher)[] }) {
  const visible = players.slice(0, 5)
  const overflow = players.length - visible.length
  return (
    <div style={{ display: "flex", alignItems: "center" }}>
      {visible.map((p, i) => (
        <div key={p.id} style={{ marginLeft: i === 0 ? 0 : -8, zIndex: visible.length - i, position: "relative" }}
          title={p.name}>
          <PlayerPhoto mlbamId={p.mlbamId} name={p.name} color={p.teamColor} size={40} />
        </div>
      ))}
      {overflow > 0 && (
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "rgba(255,255,255,0.08)", border: "0.5px solid rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.5)", marginLeft: -8, zIndex: 0 }}>
          +{overflow}
        </div>
      )}
    </div>
  )
}

function StatCell({ val, win }: { val: number; win: boolean }) {
  return (
    <span style={{ fontSize: 1, fontWeight: 700, color: win ? "#4ade80" : "#f87171" }}>{val}</span>
  )
}

// ─── Expanded row ─────────────────────────────────────────────────────────────

function ExpandedRow({ result }: { result: SimulationResult }) {
  const allHomePlayers = [...result.home.batters, ...result.home.pitchers]
  const allAwayPlayers = [...result.away.batters, ...result.away.pitchers]

  function Section({ title, players, accent }: { title: string; players: (Batter | Pitcher)[]; accent: string }) {
    return (
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.71)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 10 }}>{title}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {players.map(p => (
            <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "6px 10px" }}>
              <PlayerPhoto mlbamId={p.mlbamId} name={p.name} color={p.teamColor} size={30} />
              <div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#f0ede6" }}>{p.name}</div>
                <div style={{ fontSize: 13, fontWeight:500,  color: "rgba(255, 255, 255, 0.64)" }}>
                  {p.team} · {"stand" in p ? `Bats ${(p as Batter).stand}` : `Throws ${(p as Pitcher).throws}`}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <tr>
      <td colSpan={9} style={{ padding: "0 0 2px 0", background: "transparent" }}>
        <div style={{ margin: "0 0 4px 0", background: "rgba(13,17,23,0.7)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "18px 20px", display: "flex", gap: 32 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#e84057", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 14 }}>Away Lineup</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Section title="Batters" players={result.away.batters} accent="#e84057" />
              <Section title="Pitchers" players={result.away.pitchers} accent="#e84057" />
            </div>
          </div>
          <div style={{ width: "0.5px", background: "rgba(255,255,255,0.07)", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#3b82f6", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 14 }}>Home Lineup</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Section title="Batters" players={result.home.batters} accent="#3b82f6" />
              <Section title="Pitchers" players={result.home.pitchers} accent="#3b82f6" />
            </div>
          </div>
        </div>
      </td>
    </tr>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function History() {
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [search, setSearch] = useState("")

  const filtered = MOCK_HISTORY.filter(r =>
    [...r.home.batters, ...r.home.pitchers, ...r.away.batters, ...r.away.pitchers]
      .some(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.team.toLowerCase().includes(search.toLowerCase()))
    || r.date.toLowerCase().includes(search.toLowerCase())
  )

  function toggleExpand(id: number) {
    setExpandedId(prev => prev === id ? null : id)
  }

  const thStyle: React.CSSProperties = {
    padding: "11px 14px", fontSize: 15, fontWeight: 600,
    color: "rgba(255, 255, 255, 0.6)", textAlign: "left",
    letterSpacing: ".08em", textTransform: "uppercase",
    whiteSpace: "nowrap",
  }

  const tdStyle: React.CSSProperties = {
    padding: "14px 14px", fontSize: 14, verticalAlign: "middle",
  }

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", backgroundImage: "url(https://pix11.com/wp-content/uploads/sites/25/2026/05/APTOPIX_Yankees_Mets_Baseball_26137758631951.jpg?w=2560&h=1440&crop=1)" }}>
      
      <Sidebar activePath="/history" username="Fausto" />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Topbar */}
        <div style={{ padding: "18px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 600, color: "rgba(255, 255, 255, 0.68)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 3 }}>MLB · 2025</div>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 35, fontWeight: 700, color: "#f0ede6" }}>Simulation History</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255, 255, 255, 0.32)", borderRadius: 6, padding: "7px 12px", fontSize: 16, color: "rgba(255, 255, 255, 0.88)" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#2ecc71" }} />
            {MOCK_HISTORY.length} simulations
          </div>
        </div>

        {/* Search */}
        <div style={{ padding: "12px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", flexShrink: 0 }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by date"
            aria-label="Search simulation history"
            style={{ width: "100%", maxWidth: 400, color: "rgba(255, 255, 255, 0.84)", background: "rgba(255, 255, 255, 0.14)", border: "0.5px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "8px 14px", fontSize: 15, fontWeight: 600, fontFamily: "'DM Sans', sans-serif", outline: "none" }}
          />
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
          {filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", fontSize: 14, color: "rgba(255,255,255,0.3)" }}>No simulations match your search</div>
          ) : (
            <div style={{ background: "rgba(13,17,23,0.85)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 10, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }} aria-label="Simulation history">
                <thead>
                  <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.08)" }}>
                    <th style={thStyle}>Date</th>
                    <th style={thStyle}>Away</th>
                    <th style={thStyle}>Home</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Score</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Hits</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Strikeouts</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>HRs</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Winner</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(result => {
                    const isExpanded = expandedId === result.id
                    const homeWon = result.home.score > result.away.score
                    const homePlayers = [...result.home.batters, ...result.home.pitchers]
                    const awayPlayers = [...result.away.batters, ...result.away.pitchers]

                    return (
                      <>
                        <tr
                          key={result.id}
                          style={{ borderBottom: isExpanded ? "none" : "0.5px solid rgba(255,255,255,0.05)", background: isExpanded ? "rgba(255,255,255,0.03)" : "transparent", transition: "background .12s" }}
                        >
                          {/* Date */}
                          <td style={tdStyle}>
                            <div style={{ fontSize: 16, fontWeight: 600, color: "#f0ede6" }}>{result.date}</div>
                            <div style={{ fontSize: 15, color: "rgba(255, 255, 255, 0.68)" }}>{result.time}</div>
                          </td>

                          {/* Away players */}
                          <td style={tdStyle}>
                            <PlayerStack players={awayPlayers} />
                          </td>

                          {/* Home players */}
                          <td style={tdStyle}>
                            <PlayerStack players={homePlayers} />
                          </td>

                          {/* Score */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "5px 12px" }}>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(232,64,87,1)" }}>{result.away.score}</span>
                              <span style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.69)" }}>–</span>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(59, 130, 246)" }}>{result.home.score}</span>
                            </div>
                          </td>

                          {/* Hits */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "5px 12px" }}>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(232,64,87,1)" }}>{result.away.hits}</span>
                              <span style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.69)" }}>–</span>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(59, 130, 246)" }}>{result.home.hits}</span>
                            </div>
                          </td>

                          {/* Strikeouts */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "5px 12px" }}>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(232,64,87,1)" }}>{result.away.strikeouts}</span>
                              <span style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.69)" }}>–</span>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(59, 130, 246)" }}>{result.home.strikeouts}</span>
                            </div>
                          </td>

                          {/* Home runs */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "5px 12px" }}>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(232,64,87,1)" }}>{result.away.homeruns}</span>
                              <span style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.69)" }}>–</span>
                              <span style={{ fontSize: 16, fontWeight: 800, color: "rgba(59, 130, 246)" }}>{result.home.homeruns}</span>
                            </div>
                          </td>

                          {/* Winner */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            {
                              <span style={{ fontSize: 15, fontWeight: 600, color: homeWon ? "rgba(59,130,246,1)" : "rgba(232,64,87,1)", background: "rgba(74,222,128,0.1)", border: "0.5px solid", borderRadius: 5, borderColor:  homeWon ? "rgba(59,130,246,1)" : "rgba(232,64,87,1)",padding: "3px 10px" }}>
                                {homeWon ? "Home" : "Away"}
                              </span>
                            }
                          </td>

                          {/* Expand */}
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <button
                              onClick={() => toggleExpand(result.id)}
                              aria-label={isExpanded ? "Collapse details" : "Expand details"}
                              style={{ width: 30, height: 30, borderRadius: 6, background: isExpanded ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.04)", border: isExpanded ? "0.5px solid rgba(192,30,46,0.4)" : "0.5px solid rgba(255,255,255,0.1)", color: isExpanded ? "#f07080" : "rgba(255,255,255,0.5)", fontSize: 14, cursor: "pointer", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif", transition: "all .15s" }}>
                              {isExpanded ? "▲" : "▼"}
                            </button>
                          </td>
                        </tr>

                        {/* Expanded player detail */}
                        {isExpanded && <ExpandedRow result={result} />}
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Summary bar */}
        <div style={{ display: "flex", flexShrink: 0, background:"rgba(35, 36, 37, 0.57)" }}>
          {[
            [String(MOCK_HISTORY.length), "Total simulations"],
            [String(MOCK_HISTORY.filter(r => r.away.score > r.home.score).length), "Away wins"],
            [String(MOCK_HISTORY.filter(r => r.home.score > r.away.score).length), "Home wins"],
          ].map(([val, lbl], i, arr) => (
            <div key={lbl} style={{ flex: 1, padding: "13px 20px", borderRight: i < arr.length - 1 ? "0.5px solid rgba(255,255,255,0.06)" : "none" }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 30, fontWeight: 700, color: "#f0ede6" }}>{val}</div>
              <div style={{ fontSize: 16, fontWeight:700, color: "rgba(255, 255, 255, 0.67)", textTransform: "uppercase", letterSpacing: ".07em" }}>{lbl}</div>
            </div>
          ))}
        </div>
      </div>

      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap" />
    </div>
  )
}