import { useNavigate } from "react-router"
import { teamMeta, mockGames, type Game } from "../../src/data/mockData"
import { useState } from "react"
import Sidebar from "../../src/components/Sidebar"

function probFill(p: number) {
  if (p >= 60) return "#16873a"
  if (p >= 55) return "#c49710"
  return "#b3093a"
}


function TeamCell({ name }: { name: string }) {
  const meta = teamMeta[name] ?? { abbr: null, color: "#888" }
  const [imgError, setImgError] = useState(false)

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius: "50%", background: "rgba(255, 255, 255, 1)", border: `0.5px solid ${meta.color}44`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        {meta.abbr && !imgError ? (
          <img
            src={`https://a.espncdn.com/i/teamlogos/mlb/500/${meta.abbr}.png`}
            alt={`${name} logo`}
            width={30}
            height={30}
            style={{ objectFit: "contain", borderRadius: "50%" }}
            onError={() => setImgError(true)}
          />
        ) : (
          <span style={{ fontSize: 15, fontWeight: 700, color: meta.color }}>
            {name.slice(0, 3).toUpperCase()}
          </span>
        )}
      </div>
      <div>
        <div style={{ fontSize: 16, fontWeight: 600, color: "#f0ede6" }}>{name}</div>
        <div style={{ fontSize: 14, color: "rgba(255, 255, 255, 0.84)" }}>MLB</div>
      </div>
    </div>
  )
}

function ProbCell({ prob, name }: { prob: number; name: string }) {
  return (
    <div style={{ minWidth: 90 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: "white" }} aria-label={`${prob} percent`}>{prob}%</span>
        <span style={{ fontSize: 16, color: "rgb(255, 255, 255)" }}>win</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: "rgba(255,255,255,0.07)", overflow: "hidden" }}
        role="progressbar" aria-valuenow={prob} aria-valuemin={0} aria-valuemax={100} aria-label={`${name} win probability`}>
        <div style={{ height: "100%", width: `${prob}%`, borderRadius: 2, background: probFill(prob), transition: "width .3s ease" }} />
      </div>
    </div>
  )
}

const navItems = [
  { label: "Dashboard", icon: "⊞", path: "/" },
  { label: "Simulate",  icon: "▶", path: "/simulate" },
  { label: "Statistics",icon: "≡", path: "/statistics" },
  { label: "History",   icon: "◷", path: "/history" },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const sorted = [...mockGames].sort((a, b) => b.prob1 - a.prob1)

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", backgroundImage: "url(https://sportshub.cbsistatic.com/i/2026/06/04/142ed39a-4787-4489-bdb4-83b19d3cbdb5/skenes-getty.png)", backgroundSize: "cover", backgroundPosition:"center-top"}}>

      {/* Sidebar */}
      <Sidebar activePath="/" username="Fausto" />

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "20px 28px", borderBottom: "0.5px solid rgba(255,255,255,0.31)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: 18, color: "rgba(255, 255, 255, 0.63)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 3 }}>MLB · 2025</div>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 35, fontWeight: 700, color: "#f0ede6" }}>This week's predictions</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 6, padding: "7px 12px", fontSize: 18, color: "rgba(255, 255, 255, 0.85)", fontWeight: 500}}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#2ecc71" }} aria-hidden="true" />
            May 24 – 30, 2025
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px" }}>
          <div style={{ background: "rgba(42, 42, 44, 0.69)", borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.07)", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }} aria-label="Game predictions">
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.07)" }}>
                  {["Team", "Probability", "Date", "Time", "Team 2", "Probability", "Simulate", "Info"].map((h, i) => (
                    <th key={i} scope="col" style={{ padding: "12px 14px", fontSize: 16, fontWeight: 600, color: "rgb(255, 255, 255)", textAlign: i >= 6 ? "center" : "left", letterSpacing: ".1em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map(game => (
                  <tr key={game.id} style={{ borderBottom: "0.5px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: "14px 14px" }}><TeamCell name={game.team1} /></td>
                    <td style={{ padding: "14px 14px" }}><ProbCell prob={game.prob1} name={game.team1} /></td>
                    <td style={{ padding: "14px 14px", fontSize: 14, fontWeight: 700, color: "#f0ede6" }}>{game.date}</td>
                    <td style={{ padding: "14px 14px", fontSize: 15, color: "rgba(255, 255, 255, 0.89)", fontWeight: 700 }}>{game.time}</td>
                    <td style={{ padding: "14px 14px" }}><TeamCell name={game.team2} /></td>
                    <td style={{ padding: "14px 14px" }}><ProbCell prob={game.prob2} name={game.team2} /></td>
                    <td style={{ padding: "14px 14px", textAlign: "center" }}>
                      <button onClick={() => navigate(`/game/${game.id}`)}
                        aria-label={`Run simulation for ${game.team1} vs ${game.team2}`}
                        style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "7px 13px", background: "rgba(192,30,46,0.12)", border: "0.5px solid rgba(192,30,46,0.45)", borderRadius: 6, color: "#f07080", fontSize: 14, fontWeight: 500, fontFamily: "'DM Sans', sans-serif", cursor: "pointer" }}>
                        ▶  Run
                      </button>
                    </td>
                    <td style={{ padding: "14px 14px", textAlign: "center" }}>
                      <button onClick={() => navigate(`/game/${game.id}/info`)}
                        aria-label={`View info for ${game.team1} vs ${game.team2}`}
                        style={{ width: 30, height: 30, display: "inline-flex", alignItems: "center", justifyContent: "center", background: "rgba(255,255,255,0.04)", border: "2px solid rgba(255,255,255,0.1)", borderRadius: "50%", color: "rgba(255, 255, 255, 0.78)", fontSize: 20, fontWeight: 1000, fontFamily: "'DM Sans', sans-serif", cursor: "pointer" }}>
                        i
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary bar */}
        <div style={{ display: "flex", borderTop: "0.5px solid rgba(255,255,255,0.06)", flexShrink: 0 }}>
          {[["6", "Games this week"], ["62%", "Top confidence"], ["~65%", "Model accuracy"], ["2,430", "Games analyzed"]].map(([val, lbl], i, arr) => (
            <div key={lbl} style={{ flex: 1, padding: "14px 20px", borderRight: i < arr.length - 1 ? "0.5px solid rgba(255,255,255,0.06)" : "none" }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 900, color: "white" }}>{val}</div>
              <div style={{ fontSize: 16, color: "rgb(255, 255, 255)", textTransform: "uppercase", letterSpacing: ".07em", fontWeight: 900}}>{lbl}</div>
            </div>
          ))}
        </div>
      </div>

      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap" />
    </div>
  )
}