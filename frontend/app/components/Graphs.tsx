import { teamMeta, mockGames, type Game, type InningScore } from "../data/mockData"
import { useState } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"

type StatMode = "score" | "hits" | "hrs" | "ks"

export default function Graph({ game }: { game: Game }) {
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