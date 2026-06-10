import { useNavigate } from "react-router"
import { teamMeta, mockGames, type Game, type InningScore } from "../data/mockData"
import { useState } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"
import Sidebar from "../components/Sidebar"

function probFill(p: number) {
  if (p >= 60) return "#16873a"
  if (p <= 40) return "#b3093a"
  return "#c49710"
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

type StatMode = "score" | "hits" | "hrs" | "ks"

function ExpandedRow({ game }: { game: Game }) {
  const [mode, setMode] = useState<StatMode>("score")
  const team1Color = teamMeta[game.team1]?.color ?? "#888"
  const team2Color = teamMeta[game.team2]?.color ?? "#888"

  const score1 = game.innings.reduce((s, i) => s + i.team1, 0)
  const score2 = game.innings.reduce((s, i) => s + i.team2, 0)

  // Build cumulative chart data depending on selected mode
  const chartData = game.innings.map((ing, idx) => {
    const prev = game.innings.slice(0, idx)
    const cum = (key1: keyof InningScore, key2: keyof InningScore) => ({
      [game.team1]: prev.reduce((s, x) => s + (x[key1] as number), 0) + (ing[key1] as number),
      [game.team2]: prev.reduce((s, x) => s + (x[key2] as number), 0) + (ing[key2] as number),
    })
    return {
      name: `Inn ${ing.inning}`,
      ...(mode === "score" ? cum("team1", "team2") :
          mode === "hits"  ? cum("hits1", "hits2") :
          mode === "hrs"   ? cum("hrs1",  "hrs2")  :
                             cum("ks1",   "ks2")),
    }
  })

  function StatPill({
    label, v1, v2, stat,
  }: {
    label: string; v1: number; v2: number; stat: StatMode
  }) {
    const active = mode === stat
    return (
      <div
        onClick={() => setMode(stat)}
        style={{
          flex: 1,
          background: active ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.03)",
          border: active ? "0.5px solid rgba(192,30,46,0.5)" : "0.5px solid rgba(255,255,255,0.08)",
          borderRadius: 8, padding: "12px 16px",
          cursor: "pointer",
          transition: "all .15s",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: active ? "#f07080" : "white", textTransform: "uppercase", letterSpacing: ".08em" }}>{label}</div>
          {active && <div style={{ fontSize: 10, fontWeight: 600, color: "#f07080", letterSpacing: ".06em" }}>● ACTIVE</div>}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 30, fontWeight: 700, color: team1Color }}>{v1}</span>
          <span style={{ fontSize: 18, color: "white" }}>vs</span>
          <span style={{ fontSize: 30, fontWeight: 700, color: team2Color }}>{v2}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "white" }}>{game.team1}</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: "white" }}>{game.team2}</span>
        </div>
      </div>
    )
  }

  const chartLabel: Record<StatMode, string> = {
    score: "Score Progression",
    hits:  "Hits Progression",
    hrs:   "Home Runs Progression",
    ks:    "Strikeouts Progression",
  }

  return (
    <tr>
      <td colSpan={8} style={{ padding: "0 14px 10px" }}>
        <div style={{ background: "rgba(152, 152, 152, 0.13)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "20px 24px", display: "flex", gap: 32 }}>

          {/* Left: stats */}
          <div style={{ width: 420, flexShrink: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "white", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 12 }}>Predicted Stats</div>

            {/* Final score — also a clickable pill */}
            <div
              onClick={() => setMode("score")}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: 32,
                background: mode === "score" ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.04)",
                border: mode === "score" ? "0.5px solid rgba(192,30,46,0.5)" : "0.5px solid rgba(255,255,255,0.08)",
                borderRadius: 8, padding: "14px 20px", marginBottom: 12,
                cursor: "pointer", transition: "all .15s",
              }}
            >
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 4 }}>{game.team1}</div>
                <div style={{ fontSize: 45, fontWeight: 900, color: team1Color }}>{score1}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <div style={{ fontSize: 22, color: "rgba(255,255,255,0.3)" }}>–</div>
                {mode === "score" && <div style={{ fontSize: 10, fontWeight: 600, color: "#f07080", letterSpacing: ".06em" }}>● ACTIVE</div>}
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 4 }}>{game.team2}</div>
                <div style={{ fontSize: 45, fontWeight: 900, color: team2Color }}>{score2}</div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <StatPill label="Hits" v1={game.hits[0]}       v2={game.hits[1]}       stat="hits" />
              <StatPill label="HRs"  v1={game.homeruns[0]}   v2={game.homeruns[1]}   stat="hrs"  />
              <StatPill label="K's"  v1={game.strikeouts[0]} v2={game.strikeouts[1]} stat="ks"   />
            </div>
          </div>

          {/* Right: chart */}
          <div style={{ width: 600, flex: 1, borderRadius: 10 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "white", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 12 }}>
              {chartLabel[mode]}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 15, fontWeight: 700, fill: "white" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 15, fill: "white" }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: "rgba(27, 25, 46, 0.67)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 15 }}
                  labelStyle={{ color: "white", marginBottom: 4, fontSize: 15, fontWeight: 600 }}
                />
                <Legend wrapperStyle={{ fontSize: 19, fontWeight: 600, color: "rgba(255,255,255,0.7)", paddingTop: 8 }} />
                <Line type="monotone" dataKey={game.team1} stroke={team1Color} strokeWidth={2} dot={{ r: 4, fill: team1Color }} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey={game.team2} stroke={team2Color} strokeWidth={2} dot={{ r: 4, fill: team2Color }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

        </div>
      </td>
    </tr>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const sorted = [...mockGames].sort((a, b) => b.prob1 - a.prob1)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", backgroundImage: "url(/images/bg-dashboard.jpg)", backgroundSize: "cover", backgroundPosition:"center-top"}}>

      {/* Sidebar */}
      <Sidebar activePath="/" />

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
                {sorted.map(game => {
                  const isExpanded = expandedId === game.id
                  return (
                    <>
                      <tr key={game.id} style={{ borderBottom: isExpanded ? "none" : "0.5px solid rgba(255,255,255,0.04)" }}>
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
                            ▶ Run
                          </button>
                        </td>
                        <td style={{ padding: "14px 14px", textAlign: "center" }}>
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : game.id)}
                            aria-label={isExpanded ? "Collapse predictions" : "Expand predictions"}
                            style={{ width: 30, height: 30, display: "inline-flex", alignItems: "center", justifyContent: "center", background: isExpanded ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.04)", border: isExpanded ? "0.5px solid rgba(192,30,46,0.4)" : "2px solid rgba(255,255,255,0.1)", borderRadius: "50%", color: isExpanded ? "#f07080" : "rgba(255, 255, 255, 0.78)", fontSize: 14, fontFamily: "'DM Sans', sans-serif", cursor: "pointer" }}>
                            {isExpanded ? "▲" : "▼"}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && <ExpandedRow game={game} />}
                    </>
                  )
                })}
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
