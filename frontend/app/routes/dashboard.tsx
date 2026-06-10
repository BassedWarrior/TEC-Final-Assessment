import { useNavigate } from "react-router"
import { teamMeta, mockGames, type Game, type InningScore } from "../data/mockData"
import { useState } from "react"
import { PageLayout, TopBar, SummaryBar } from "../components/Layout";
import Graph from "../components/Graphs";

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

export default function Dashboard() {
  const navigate = useNavigate()
  const sorted = [...mockGames].sort((a, b) => b.prob1 - a.prob1)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const summaryItems = [
    { label: "Games this week", value: "6" },
    { label: "Top confidence", value: "62%" },
    { label: "Model accuracy", value: "~65%" },
    { label: "Games analyzed", value: "2,430" },
  ];

  return (
    <PageLayout activePath="/" backgroundImage="/images/bg-dashboard.jpg">
      <TopBar title = "This week's predictions" />

        {/* Table */}
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
                      {isExpanded && <Graph game={game} />}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

      {/* Summary bar */}
      <SummaryBar items={summaryItems} />
    </PageLayout>
  )
}
