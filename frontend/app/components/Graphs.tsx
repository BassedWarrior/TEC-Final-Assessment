import { teamMeta, mockGames, type Game, type InningScore } from "../data/mockData"
import { useState } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"

type StatMode = "score" | "hits" | "hrs" | "ks"

// Simulation values are averages over many sims, so they carry long decimal
// tails. Display them with two decimals (front-end only — the data is untouched).
const fmt2 = (n: number) => n.toFixed(2)

export default function Graph({
  game,
  backgroundColor,
  fullWidth = false,
  isEmbedded = false  // New prop to detect if it's embedded in a table
}: {
  game: Game;
  backgroundColor?: string;
  fullWidth?: boolean;
  isEmbedded?: boolean;
}) {
  const [mode, setMode] = useState<StatMode>("score")
  const homeTeamColor = teamMeta[game.homeTeam]?.color ?? "var(--home-blue)"
  const awayTeamColor = teamMeta[game.awayTeam]?.color ?? "var(--away-red)"
  const homeRuns = game.innings.reduce((s, i) => s + i.homeRuns, 0)
  const awayRuns = game.innings.reduce((s, i) => s + i.awayRuns, 0)

  // Build cumulative chart data depending on selected mode
  console.log(game.innings)
  const chartData = game.innings.map((ing, idx) => {
    const prev = game.innings.slice(0, idx)
    const cum = (key1: keyof InningScore, key2: keyof InningScore) => ({
      [game.awayTeam]: prev.reduce((s, x) => s + (x[key1] as number), 0) + (ing[key1] as number),
      [game.homeTeam]: prev.reduce((s, x) => s + (x[key2] as number), 0) + (ing[key2] as number),
    })
    return {
      name: `Inn ${ing.inning}`,
      ...(mode === "score" ? cum("awayRuns", "homeRuns") :
          mode === "hits"  ? cum("awayHits", "homeHits") :
          mode === "hrs"   ? cum("awayHRs",  "homeHRs")  :
                             cum("awayStrikeouts",   "homeStrikeouts")),
    }
  })
  console.log(chartData)

  function StatPill({ label, v1, v2, stat }: { label: string; v1: number; v2: number; stat: StatMode }) {
    const active = mode === stat
    return (
      <div
        onClick={() => setMode(stat)}
        style={{
          flex: 1,
          background: active ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.03)",
          border: active ? "0.5px solid rgba(192,30,46,0.5)" : "0.5px solid rgba(255,255,255,0.08)",
          borderRadius: 8,
          padding: isEmbedded ? "8px 12px" : "12px 16px",  // Smaller padding when embedded
          cursor: "pointer",
          transition: "all .15s",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isEmbedded ? 6 : 10 }}>
          <div style={{ fontSize: isEmbedded ? 10 : 12, fontWeight: 600, color: active ? "#f07080" : "white", textTransform: "uppercase", letterSpacing: ".08em" }}>{label}</div>
          {active && <div style={{ fontSize: isEmbedded ? 8 : 10, fontWeight: 600, color: "#f07080", letterSpacing: ".06em" }}>● ACTIVE</div>}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: isEmbedded ? 20 : 30, fontWeight: 700, color: awayTeamColor }}>{fmt2(v1)}</span>
          <span style={{ fontSize: isEmbedded ? 14 : 18, color: "white" }}>vs</span>
          <span style={{ fontSize: isEmbedded ? 20 : 30, fontWeight: 700, color: homeTeamColor }}>{fmt2(v2)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: isEmbedded ? 2 : 4 }}>
          <span style={{ fontSize: isEmbedded ? 9 : 11, fontWeight: 600, color: "white" }}>{game.awayTeam}</span>
          <span style={{ fontSize: isEmbedded ? 9 : 11, fontWeight: 600, color: "white" }}>{game.homeTeam}</span>
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

  // Embedded version (for dashboard table)
  if (isEmbedded) {
    return (
      <div style={{
        background: backgroundColor || "rgba(13, 17, 23, 0.85)",
        border: "0.5px solid rgba(255,255,255,0.08)",
        borderRadius: 8,
        padding: "16px 20px",
      }}>
        {/* Simplified layout for embedded view */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "white", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 12 }}>
            Prediction Details
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <StatPill label="Score" v1={awayRuns} v2={homeRuns} stat="score" />
            <StatPill label="Hits" v1={game.hits[0]} v2={game.hits[1]} stat="hits" />
            <StatPill label="HRs" v1={game.homeruns[0]} v2={game.homeruns[1]} stat="hrs" />
            <StatPill label="K's" v1={game.strikeouts[0]} v2={game.strikeouts[1]} stat="ks" />
          </div>
        </div>

        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "white", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 12 }}>
            {chartLabel[mode]}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <XAxis dataKey="name" tick={{ fontSize: 12, fontWeight: 700, fill: "white" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "white" }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: "rgba(27, 25, 46, 0.67)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 13 }}
                labelStyle={{ color: "white", marginBottom: 4, fontSize: 13, fontWeight: 600 }}
              />
              <Legend wrapperStyle={{ fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.7)", paddingTop: 8 }} />
              <Line type="monotone" dataKey={game.awayTeam} stroke={awayTeamColor} strokeWidth={2} dot={{ r: 3, fill: awayTeamColor }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey={game.homeTeam} stroke={homeTeamColor} strokeWidth={2} dot={{ r: 3, fill: homeTeamColor }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )
  }

  // Full version (for sandbox page)
  return (
    <div style={{
      width: fullWidth ? "100%" : "auto",
      background: backgroundColor || "rgba(152, 152, 152, 0.13)",
      border: "0.5px solid rgba(255,255,255,0.08)",
      borderRadius: 8,
      padding: "20px 24px",
      display: "flex",
      gap: 32,
      flexWrap: "wrap",
    }}>
      {/* Left: stats */}
      <div style={{
        flex: fullWidth ? "0 0 auto" : "0 0 420px",
        width: fullWidth ? "auto" : 420,
        minWidth: fullWidth ? 300 : 420,
      }}>
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
            <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 4 }}>{game.awayTeam}</div>
            <div style={{ fontSize: 45, fontWeight: 900, color: awayTeamColor }}>{fmt2(awayRuns)}</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{ fontSize: 22, color: "rgba(255,255,255,0.3)" }}>–</div>
            {mode === "score" && <div style={{ fontSize: 10, fontWeight: 600, color: "#f07080", letterSpacing: ".06em" }}>● ACTIVE</div>}
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: "white", marginBottom: 4 }}>{game.homeTeam}</div>
            <div style={{ fontSize: 45, fontWeight: 900, color: homeTeamColor }}>{fmt2(homeRuns)}</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <StatPill label="Hits" v1={game.hits[0]} v2={game.hits[1]} stat="hits" />
          <StatPill label="HRs" v1={game.homeruns[0]} v2={game.homeruns[1]} stat="hrs" />
          <StatPill label="K's" v1={game.strikeouts[0]} v2={game.strikeouts[1]} stat="ks" />
        </div>
      </div>

      {/* Right: chart */}
      <div style={{
        flex: fullWidth ? 1 : "0 1 600px",
        minWidth: fullWidth ? 300 : 600,
        borderRadius: 10,
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "white", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 12 }}>
          {chartLabel[mode]}
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <XAxis dataKey="name" tick={{ fontSize: 15, fontWeight: 700, fill: "white" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 15, fill: "white" }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              formatter={(value) => fmt2(Number(value))}
              contentStyle={{ background: "rgba(27, 25, 46, 0.67)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, fontSize: 15 }}
              labelStyle={{ color: "white", marginBottom: 4, fontSize: 15, fontWeight: 600 }}
            />
            <Legend wrapperStyle={{ fontSize: 19, fontWeight: 600, color: "rgba(255,255,255,0.7)", paddingTop: 8 }} />
            <Line type="monotone" dataKey={game.awayTeam} stroke={awayTeamColor} strokeWidth={2} dot={{ r: 4, fill: awayTeamColor }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey={game.homeTeam} stroke={homeTeamColor} strokeWidth={2} dot={{ r: 4, fill: homeTeamColor }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
