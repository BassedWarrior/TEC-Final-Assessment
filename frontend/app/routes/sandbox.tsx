import { useState, useRef } from "react"
import Sidebar from "../../src/components/Sidebar"
import { MOCK_BATTERS, MOCK_PITCHERS } from "../../src/data/mockPlayers"
import type { Batter, Pitcher } from "../../src/data/mockPlayers"

// ─── Types ───────────────────────────────────────────────────────────────────

type PlayerSlot = Batter | Pitcher | null
type TeamSide = "home" | "away"

interface TeamLineup {
  batters: (Batter | null)[]   // always 9 slots
  pitchers: (Pitcher | null)[] // at least 1 slot
}

interface InningScore {
  inning: number
  home: number | null
  away: number | null
}

interface TeamStats {
  hits: number | null
  strikeouts: number | null
  homeruns: number | null
}

// ─── Mock scoreboard prediction ───────────────────────────────────────────────

function generateMockScore(): InningScore[] {
  return Array.from({ length: 9 }, (_, i) => ({
    inning: i + 1,
    home: null,
    away: null,
  }))
}

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
      <img src={mlbHeadshotUrl(mlbamId)} alt={name} style={{ width: "100%", height: "130%", objectFit: "cover", objectPosition: "top 15%", marginTop: "-10%", transform: "scale(0.85)", transformOrigin: "top center" }} onError={() => setImgError(true)} />
    </div>
  )
}

// ─── Player Pool (reusable, extracted component) ──────────────────────────────

interface PlayerPoolProps {
  search: string
  onSearchChange: (v: string) => void
  tab: "batter" | "pitcher"
  onTabChange: (t: "batter" | "pitcher") => void
  onDragStart: (e: React.DragEvent, player: Batter | Pitcher, type: "batter" | "pitcher") => void
}

function PlayerPool({ search, onSearchChange, tab, onTabChange, onDragStart }: PlayerPoolProps) {
  const batters = MOCK_BATTERS.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.team.toLowerCase().includes(search.toLowerCase())
  )
  const pitchers = MOCK_PITCHERS.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.team.toLowerCase().includes(search.toLowerCase())
  )
  const players = tab === "batter" ? batters : pitchers

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "rgba(13,17,23,0.85)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 10, overflow: "hidden" }}>
      {/* Pool header */}
      <div style={{ padding: "14px 16px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", flexShrink: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,0.82)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 10 }}>Player Pool</div>
        {/* Search */}
        <input
          value={search}
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search players..."
          aria-label="Search player pool"
          style={{ width: "100%", background: "rgba(255,255,255,0.05)", border: "0.5px solid rgba(255,255,255,0.15)", borderRadius: 6, padding: "8px 12px", fontSize: 14, color: "rgba(255,255,255,1)", fontFamily: "'DM Sans', sans-serif", outline: "none", marginBottom: 10 }}
        />
        {/* Tabs */}
        <div style={{ display: "flex", gap: 3, background: "rgba(255,255,255,0.04)", borderRadius: 6, padding: 3 }}>
          {(["batter", "pitcher"] as const).map(t => (
            <button key={t} onClick={() => onTabChange(t)}
              style={{ flex: 1, padding: "5px 0", borderRadius: 4, fontSize: 13, fontWeight: 600, border: "none", cursor: "pointer", fontFamily: "'DM Sans', sans-serif", transition: "all .15s", background: tab === t ? "rgba(192,30,46,0.25)" : "transparent", color: tab === t ? "#f07080" : "rgba(255,255,255,0.5)" }}>
              {t === "batter" ? "Batters" : "Pitchers"}
            </button>
          ))}
        </div>
      </div>

      {/* Player list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
        {players.length === 0 ? (
          <div style={{ padding: 20, textAlign: "center", fontSize: 13, color: "rgba(255,255,255,0.3)" }}>No players found</div>
        ) : players.map(player => (
          <div
            key={player.id}
            draggable
            onDragStart={e => onDragStart(e, player, tab)}
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 7, marginBottom: 4, background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", cursor: "grab", transition: "background .12s, border-color .12s" }}
            onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.07)"; (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.15)" }}
            onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)"; (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.07)" }}
          >
            <PlayerPhoto mlbamId={player.mlbamId} name={player.name} color={player.teamColor} size={32} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#f0ede6", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{player.name}</div>
              <div style={{ fontSize: 13, color: "rgba(255, 255, 255, 0.62)" }}>{player.team}</div>
            </div>
            <div style={{ fontSize: 12, color: "rgba(255, 255, 255, 0.5)", flexShrink: 0 }}>⠿</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Player Slot Row ──────────────────────────────────────────────────────────

interface SlotRowProps {
  index: number
  label: string
  player: Batter | Pitcher | null
  onDrop: (e: React.DragEvent, index: number) => void
  onRemove: (index: number) => void
  onDragStartSlot: (e: React.DragEvent, index: number) => void
  onDragOverSlot: (e: React.DragEvent, index: number) => void
  onDragEndSlot: () => void
  isDragOver: boolean
}

function SlotRow({ index, label, player, onDrop, onRemove, onDragStartSlot, onDragOverSlot, onDragEndSlot, isDragOver }: SlotRowProps) {
  return (
    <div
      onDragOver={e => { e.preventDefault(); onDragOverSlot(e, index) }}
      onDrop={e => onDrop(e, index)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "8px 12px",
        borderRadius: 7,
        marginBottom: 4,
        background: isDragOver ? "rgba(192,30,46,0.12)" : player ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
        border: isDragOver ? "0.5px solid rgba(192,30,46,0.5)" : player ? "0.5px solid rgba(255,255,255,0.1)" : "0.5px dashed rgba(255,255,255,0.12)",
        transition: "all .15s",
        minHeight: 48,
      }}
    >
      {/* Slot number */}
      <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.35)", flexShrink: 0 }}>
        {label}
      </div>

      {player ? (
        <>
          {/* Drag handle for reordering */}
          <div
            draggable
            onDragStart={e => onDragStartSlot(e, index)}
            onDragEnd={onDragEndSlot}
            style={{ cursor: "grab", color: "rgba(255,255,255,0.2)", fontSize: 14, flexShrink: 0, padding: "0 2px" }}
          >⠿</div>
          <PlayerPhoto mlbamId={player.mlbamId} name={player.name} color={player.teamColor} size={30} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 600, color: "#f0ede6", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{player.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.59)" }}>
              {player.team}
              {"stand" in player ? ` · Bats ${(player as Batter).stand}` : ` · Throws ${(player as Pitcher).throws}`}
            </div>
          </div>
          <button
            onClick={() => onRemove(index)}
            aria-label={`Remove ${player.name}`}
            style={{ background: "rgba(192,30,46,0.1)", border: "0.5px solid rgba(192,30,46,0.3)", borderRadius: 5, width: 24, height: 24, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#f07080", fontSize: 13, flexShrink: 0, fontFamily: "'DM Sans', sans-serif" }}>
            ✕
          </button>
        </>
      ) : (
        <div style={{ fontSize: 15, color: "rgba(255, 255, 255, 0.54)", fontStyle: "italic" }}>
          {isDragOver ? "Drop here" : "Drag a player here"}
        </div>
      )}
    </div>
  )
}

// ─── Team Lineup Table ────────────────────────────────────────────────────────

interface TeamTableProps {
  side: TeamSide
  lineup: TeamLineup
  onDrop: (e: React.DragEvent, side: TeamSide, section: "batters" | "pitchers", index: number) => void
  onRemove: (side: TeamSide, section: "batters" | "pitchers", index: number) => void
  onReorder: (side: TeamSide, section: "batters" | "pitchers", from: number, to: number) => void
  onAddPitcherSlot: (side: TeamSide) => void
  onRemovePitcherSlot: (side: TeamSide) => void
  dragOverSlot: { side: TeamSide; section: "batters" | "pitchers"; index: number } | null
  setDragOverSlot: (v: { side: TeamSide; section: "batters" | "pitchers"; index: number } | null) => void
}

function TeamTable({ side, lineup, onDrop, onRemove, onReorder, onAddPitcherSlot, onRemovePitcherSlot, dragOverSlot, setDragOverSlot }: TeamTableProps) {
  const reorderFrom = useRef<number | null>(null)
  const reorderSection = useRef<"batters" | "pitchers" | null>(null)

  const label = side === "home" ? "Home" : "Away"
  const accentColor = side === "home" ? "#3b82f6" : "#e84057"
  const battersFilled = lineup.batters.filter(Boolean).length
  const pitchersFilled = lineup.pitchers.filter(Boolean).length

  function handleDragOverSlot(e: React.DragEvent, section: "batters" | "pitchers", index: number) {
    e.preventDefault()
    setDragOverSlot({ side, section, index })
  }

  function handleDragStartSlot(e: React.DragEvent, section: "batters" | "pitchers", index: number) {
    reorderFrom.current = index
    reorderSection.current = section
    e.dataTransfer.setData("reorder", JSON.stringify({ side, section, index }))
  }

  function handleDrop(e: React.DragEvent, section: "batters" | "pitchers", index: number) {
    setDragOverSlot(null)
    const reorderData = e.dataTransfer.getData("reorder")
    if (reorderData) {
      const { side: fromSide, section: fromSection, index: fromIndex } = JSON.parse(reorderData)
      if (fromSide === side && fromSection === section) {
        onReorder(side, section, fromIndex, index)
        return
      }
    }
    onDrop(e, side, section, index)
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "rgba(13,17,23,0.75)", border: `0.5px solid rgba(255,255,255,0.1)`, borderRadius: 10, overflow: "hidden" }}>
      {/* Team header */}
      <div style={{ padding: "14px 16px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: accentColor, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>
            {battersFilled}/9 batters · {pitchersFilled}/{lineup.pitchers.length} pitchers
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={() => onRemovePitcherSlot(side)} disabled={lineup.pitchers.length <= 1}
            aria-label="Remove pitcher slot"
            style={{ width: 26, height: 26, borderRadius: 5, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.12)", color: lineup.pitchers.length <= 1 ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.6)", fontSize: 15, cursor: lineup.pitchers.length <= 1 ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif" }}>−</button>
          <button onClick={() => onAddPitcherSlot(side)}
            aria-label="Add pitcher slot"
            style={{ width: 26, height: 26, borderRadius: 5, background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.6)", fontSize: 15, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif" }}>+</button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 12px" }}>
        {/* Batters section */}
        <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.75)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 8, paddingLeft: 4 }}>Batting Order</div>
        {lineup.batters.map((player, i) => (
          <SlotRow
            key={i} index={i} label={String(i + 1)}
            player={player}
            onDrop={(e, idx) => handleDrop(e, "batters", idx)}
            onRemove={idx => onRemove(side, "batters", idx)}
            onDragStartSlot={(e, idx) => handleDragStartSlot(e, "batters", idx)}
            onDragOverSlot={(e, idx) => handleDragOverSlot(e, "batters", idx)}
            onDragEndSlot={() => setDragOverSlot(null)}
            isDragOver={dragOverSlot?.side === side && dragOverSlot?.section === "batters" && dragOverSlot?.index === i}
          />
        ))}

        {/* Pitchers section */}
        <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.75)", letterSpacing: ".1em", textTransform: "uppercase", margin: "14px 0 8px", paddingLeft: 4 }}>Pitching Staff</div>
        {lineup.pitchers.map((player, i) => (
          <SlotRow
            key={i} index={i} label="P"
            player={player}
            onDrop={(e, idx) => handleDrop(e, "pitchers", idx)}
            onRemove={idx => onRemove(side, "pitchers", idx)}
            onDragStartSlot={(e, idx) => handleDragStartSlot(e, "pitchers", idx)}
            onDragOverSlot={(e, idx) => handleDragOverSlot(e, "pitchers", idx)}
            onDragEndSlot={() => setDragOverSlot(null)}
            isDragOver={dragOverSlot?.side === side && dragOverSlot?.section === "pitchers" && dragOverSlot?.index === i}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Scoreboard ───────────────────────────────────────────────────────────────

interface ScoreboardProps {
  innings: InningScore[]
  homeTotal: number
  awayTotal: number
  simulated: boolean
  homeName: string
  awayName: string
}

function Scoreboard({ innings, homeTotal, awayTotal, simulated, homeName, awayName }: ScoreboardProps) {
  const cellStyle = (highlight?: boolean): React.CSSProperties => ({
    minWidth: 36, textAlign: "center", padding: "8px 6px",
    fontSize: 15, fontWeight: highlight ? 700 : 500,
    color: highlight ? "#f0ede6" : "rgba(255, 255, 255, 0.72)",
    borderRight: "0.5px solid rgba(255,255,255,0.07)",
  })

  return (
    <div style={{ background: "rgba(13, 17, 23, 0.74)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 10, overflow: "hidden", flexShrink: 0 }}>
      {/* Scoreboard title */}
      <div style={{ padding: "12px 18px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "rgba(255, 255, 255, 0.82)", letterSpacing: ".1em", textTransform: "uppercase" }}>Scoreboard</div>
        {simulated && <div style={{ fontSize: 13, fontWeight: 600, color: "#4ade80", letterSpacing: ".06em" }}>● SIMULATED</div>}
        {!simulated && <div style={{ fontSize: 13, color: "rgba(255, 255, 255, 0.6)", fontStyle: "italic" }}>Run simulation to see predictions</div>}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 500 }}>
          <thead>
            <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.07)" }}>
              <th style={{ padding: "8px 18px", fontSize: 15, fontWeight: 600, color: "rgba(255, 255, 255, 0.75)", textAlign: "left", minWidth: 80, borderRight: "0.5px solid rgba(255,255,255,0.07)" }}>Team</th>
              {innings.map(i => (
                <th key={i.inning} style={{ minWidth: 36, textAlign: "center", padding: "8px 6px", fontSize: 12, fontWeight: 600, color: "rgba(255, 255, 255, 0.66)", borderRight: "0.5px solid rgba(255,255,255,0.07)" }}>{i.inning}</th>
              ))}
              <th style={{ minWidth: 44, textAlign: "center", padding: "8px 10px", fontSize: 13, fontWeight: 700, color: "rgba(255, 255, 255, 0.76)" }}>R</th>
            </tr>
          </thead>
          <tbody>
            {/* Away row */}
            <tr style={{ borderBottom: "0.5px solid rgba(255,255,255,0.06)" }}>
              <td style={{ padding: "8px 18px", fontSize: 15, fontWeight: 600, color: "#e84057", borderRight: "0.5px solid rgba(255,255,255,0.07)", whiteSpace: "nowrap" }}> {awayName}</td>
              {innings.map(i => (
                <td key={i.inning} style={cellStyle()}>{simulated && i.away !== null ? i.away : <span style={{ color: "rgba(255,255,255,0.15)" }}>—</span>}</td>
              ))}
              <td style={{ textAlign: "center", padding: "8px 10px", fontSize: 15, fontWeight: 800, color: simulated ? (awayTotal > homeTotal ? "#4ade80" : "#f0ede6") : "rgba(255, 255, 255, 0.5)" }}>
                {simulated ? awayTotal : "—"}
              </td>
            </tr>
            {/* Home row */}
            <tr>
              <td style={{ padding: "8px 18px", fontSize: 15, fontWeight: 600, color: "#3b82f6", borderRight: "0.5px solid rgba(255,255,255,0.07)", whiteSpace: "nowrap" }}> {homeName}</td>
              {innings.map(i => (
                <td key={i.inning} style={cellStyle()}>{simulated && i.home !== null ? i.home : <span style={{ color: "rgba(255,255,255,0.15)" }}>—</span>}</td>
              ))}
              <td style={{ textAlign: "center", padding: "8px 10px", fontSize: 15, fontWeight: 800, color: simulated ? (homeTotal > awayTotal ? "#4ade80" : "#f0ede6") : "rgba(255, 255, 255, 0.5)" }}>
                {simulated ? homeTotal : "—"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────

interface StatsBarProps {
  homeStats: TeamStats
  awayStats: TeamStats
  simulated: boolean
  homeName: string
  awayName: string
}

function StatsBar({ homeStats, awayStats, simulated, homeName, awayName }: StatsBarProps) {
  const stats: { key: keyof TeamStats; label: string }[] = [
    { key: "hits",       label: "Hits" },
    { key: "strikeouts", label: "Strikeouts" },
    { key: "homeruns",   label: "Home Runs" },
  ]

  function statColor(home: number | null, away: number | null, key: keyof TeamStats, side: "home" | "away") {
    if (home === null || away === null) return "#f0ede6"
    const isHome = side === "home"
    const mine = isHome ? home : away
    const theirs = isHome ? away : home
    if (mine > theirs) return "#4ade80"
    if (mine < theirs) return "#f87171"
    return "#f0ede6"
  }

  return (
    <div style={{ background: "rgba(13,17,23,0.74)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 10, overflow: "hidden", flexShrink: 0 }}>
      <div style={{ padding: "10px 18px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,0.82)", letterSpacing: ".1em", textTransform: "uppercase" }}>Team Stats</div>
        {!simulated && <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", fontStyle: "italic" }}>Run simulation to see stats</div>}
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.07)" }}>
            <th style={{ padding: "8px 18px", fontSize: 15, fontWeight: 600, color: "rgba(255, 255, 255, 0.7)", textAlign: "left", borderRight: "0.5px solid rgba(255,255,255,0.07)" }}>Team</th>
            {stats.map(s => (
              <th key={s.key} style={{ padding: "8px 14px", fontSize: 15, fontWeight: 600, color: "rgba(255, 255, 255, 0.75)", textAlign: "center", borderRight: "0.5px solid rgba(255,255,255,0.07)" }}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(["away", "home"] as const).map(side => {
            const teamStats = side === "home" ? homeStats : awayStats
            const otherStats = side === "home" ? awayStats : homeStats
            const name = side === "home" ? homeName : awayName
            const color = side === "home" ? "#3b82f6" : "#e84057"
            return (
              <tr key={side} style={{ borderBottom: side === "away" ? "0.5px solid rgba(255,255,255,0.06)" : "none" }}>
                <td style={{ padding: "10px 18px", fontSize: 15, fontWeight: 600, color, borderRight: "0.5px solid rgba(255,255,255,0.07)", whiteSpace: "nowrap" }}>
                {name}
                </td>
                {stats.map(s => {
                  const val = teamStats[s.key]
                  const otherVal = otherStats[s.key]
                  return (
                    <td key={s.key} style={{ padding: "10px 14px", textAlign: "center", fontSize: 15, fontWeight: 700, color: simulated ? statColor(homeStats[s.key], awayStats[s.key], s.key, side) : "rgba(255,255,255,0.2)", borderRight: "0.5px solid rgba(255,255,255,0.07)" }}>
                      {simulated && val !== null ? val : <span style={{ fontSize: 13, color: "rgba(255,255,255,0.15)" }}>—</span>}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

function emptyLineup(): TeamLineup {
  return {
    batters: Array(9).fill(null),
    pitchers: [null],
  }
}

export default function Sandbox() {
  const [home, setHome] = useState<TeamLineup>(emptyLineup())
  const [away, setAway] = useState<TeamLineup>(emptyLineup())
  const [innings, setInnings] = useState<InningScore[]>(generateMockScore())
  const [simulated, setSimulated] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [poolSearch, setPoolSearch] = useState("")
  const [poolTab, setPoolTab] = useState<"batter" | "pitcher">("batter")
  const [dragOverSlot, setDragOverSlot] = useState<{ side: TeamSide; section: "batters" | "pitchers"; index: number } | null>(null)
  const [homeStats, setHomeStats] = useState<TeamStats>({ hits: null, strikeouts: null, homeruns: null })
  const [awayStats, setAwayStats] = useState<TeamStats>({ hits: null, strikeouts: null, homeruns: null })
  const dragPayload = useRef<{ player: Batter | Pitcher; type: "batter" | "pitcher" } | null>(null)

  // Team name derived from first filled batter's team, fallback to label
  const homeName = "Home"
  const awayName = "Away"

  // ── Drag from pool ──────────────────────────────────────────────────────────
  function handlePoolDragStart(e: React.DragEvent, player: Batter | Pitcher, type: "batter" | "pitcher") {
    dragPayload.current = { player, type }
    e.dataTransfer.setData("pool", "true")
  }

  // ── Drop onto slot ──────────────────────────────────────────────────────────
  function handleDrop(e: React.DragEvent, side: TeamSide, section: "batters" | "pitchers", index: number) {
    e.preventDefault()
    setDragOverSlot(null)

    const isReorder = e.dataTransfer.getData("reorder")
    if (isReorder) return // handled inside TeamTable

    if (!dragPayload.current) return
    const { player, type } = dragPayload.current

    // Type guard: only batters in batting order, only pitchers in pitching staff
    if (section === "batters" && type !== "batter") return
    if (section === "pitchers" && type !== "pitcher") return

    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      const updated = { ...prev, [section]: [...prev[section]] }
      updated[section][index] = player
      return updated
    })
    dragPayload.current = null
  }

  // ── Remove from slot ────────────────────────────────────────────────────────
  function handleRemove(side: TeamSide, section: "batters" | "pitchers", index: number) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      const updated = { ...prev, [section]: [...prev[section]] }
      updated[section][index] = null
      return updated
    })
    setSimulated(false)
  }

  // ── Reorder within a section ────────────────────────────────────────────────
  function handleReorder(side: TeamSide, section: "batters" | "pitchers", from: number, to: number) {
    if (from === to) return
    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      const arr = [...prev[section]]
      const item = arr[from]
      arr.splice(from, 1)
      arr.splice(to, 0, item)
      return { ...prev, [section]: arr }
    })
    setSimulated(false)
  }

  // ── Add / remove pitcher slots ──────────────────────────────────────────────
  function handleAddPitcherSlot(side: TeamSide) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => ({ ...prev, pitchers: [...prev.pitchers, null] }))
  }

  function handleRemovePitcherSlot(side: TeamSide) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      if (prev.pitchers.length <= 1) return prev
      return { ...prev, pitchers: prev.pitchers.slice(0, -1) }
    })
  }

  // ── Simulate ────────────────────────────────────────────────────────────────
  function canSimulate() {
    const homeBatters = home.batters.filter(Boolean).length
    const awayBatters = away.batters.filter(Boolean).length
    const homePitchers = home.pitchers.filter(Boolean).length
    const awayPitchers = away.pitchers.filter(Boolean).length
    return homeBatters >= 1 && awayBatters >= 1 && homePitchers >= 1 && awayPitchers >= 1
  }

  async function handleSimulate() {
    if (!canSimulate()) return
    setSimulating(true)
    setSimulated(false)

    // Mock delay simulating API call — replace with real model call
    await new Promise(r => setTimeout(r, 1200))

    const mockInnings: InningScore[] = Array.from({ length: 9 }, (_, i) => ({
      inning: i + 1,
      home: Math.random() < 0.35 ? Math.floor(Math.random() * 3) : 0,
      away: Math.random() < 0.35 ? Math.floor(Math.random() * 3) : 0,
    }))
    setInnings(mockInnings)
    setHomeStats({
      hits:       Math.floor(Math.random() * 10) + 3,
      strikeouts: Math.floor(Math.random() * 10) + 4,
      homeruns:   Math.floor(Math.random() * 4),
    })
    setAwayStats({
      hits:       Math.floor(Math.random() * 10) + 3,
      strikeouts: Math.floor(Math.random() * 10) + 4,
      homeruns:   Math.floor(Math.random() * 4),
    })
    setSimulated(true)
    setSimulating(false)
  }

  function handleReset() {
    setHome(emptyLineup())
    setAway(emptyLineup())
    setInnings(generateMockScore())
    setHomeStats({ hits: null, strikeouts: null, homeruns: null })
    setAwayStats({ hits: null, strikeouts: null, homeruns: null })
    setSimulated(false)
    dragPayload.current = null
  }

  const homeTotal = innings.reduce((s, i) => s + (i.home ?? 0), 0)
  const awayTotal = innings.reduce((s, i) => s + (i.away ?? 0), 0)

  const readyToSim = canSimulate()

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", backgroundImage: "url(https://p.potaufeu.asahi.com/9f43-p/picture/30110938/6ff98ecd602934fa9926cbf982a55015.jpg)" }}>
      <Sidebar activePath="/sandbox" username="Fausto" />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Topbar */}
        <div style={{ padding: "18px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "rgba(255, 255, 255, 0.71)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 3 }}>MLB · 2025</div>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 40, fontWeight: 700, color: "#f0ede6" }}>Sandbox</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button onClick={handleReset}
              style={{ padding: "8px 16px", borderRadius: 6, fontSize: 16, fontWeight: 500, background: "transparent", border: "0.6px solid rgba(255, 255, 255, 0.28)", color: "rgba(255, 255, 255, 0.76)", cursor: "pointer", fontFamily: "'DM Sans', sans-serif", transition: "all .15s" }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.35)"; (e.currentTarget as HTMLButtonElement).style.color = "#f0ede6" }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.15)"; (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.5)" }}>
              Reset
            </button>
            <button onClick={handleSimulate} disabled={!readyToSim || simulating}
              aria-label="Run simulation"
              style={{ padding: "8px 22px", borderRadius: 6, fontSize: 16, fontWeight: 600, background: readyToSim && !simulating ? "#c01e2e" : "rgba(192,30,46,0.25)", border: "0.6px solid rgba(255,0,0,1)", color: readyToSim && !simulating ? "#fff" : "rgba(241, 230, 230, 0.96)", cursor: readyToSim && !simulating ? "pointer" : "not-allowed", fontFamily: "'DM Sans', sans-serif", transition: "all .2s" }}>
              {simulating ? "Simulating…" : "▶ Run Simulation"}
            </button>
          </div>
        </div>

        {/* Hint bar */}
        {!readyToSim && (
          <div style={{ padding: "10px 24px", background: "rgba(192, 30, 46, 0.27)", borderBottom: "0.5px solid rgba(192,30,46,0.15)", fontSize: 15, color: "rgb(245, 233, 233)" }}>
            Add at least 1 batter and 1 pitcher to each team to run the simulation.
          </div>
        )}

        {/* Main content area */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden", padding: "16px 16px 16px 16px", gap: 12 }}>

          {/* Player Pool */}
          <div style={{ width: 220, flexShrink: 0 }}>
            <PlayerPool
              search={poolSearch}
              onSearchChange={setPoolSearch}
              tab={poolTab}
              onTabChange={setPoolTab}
              onDragStart={handlePoolDragStart}
            />
          </div>

          {/* Center: lineups + scoreboard */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, overflow: "hidden" }}>

            {/* Scoreboard */}
            <Scoreboard
              innings={innings}
              homeTotal={homeTotal}
              awayTotal={awayTotal}
              simulated={simulated}
              homeName={homeName}
              awayName={awayName}
            />

            {/* Team stats */}
            <StatsBar
              homeStats={homeStats}
              awayStats={awayStats}
              simulated={simulated}
              homeName={homeName}
              awayName={awayName}
            />

            {/* Team tables side by side */}
            <div style={{ flex: 1, display: "flex", gap: 12, overflow: "hidden" }}>
              <TeamTable
                side="away"
                lineup={away}
                onDrop={handleDrop}
                onRemove={handleRemove}
                onReorder={handleReorder}
                onAddPitcherSlot={handleAddPitcherSlot}
                onRemovePitcherSlot={handleRemovePitcherSlot}
                dragOverSlot={dragOverSlot}
                setDragOverSlot={setDragOverSlot}
              />
              <TeamTable
                side="home"
                lineup={home}
                onDrop={handleDrop}
                onRemove={handleRemove}
                onReorder={handleReorder}
                onAddPitcherSlot={handleAddPitcherSlot}
                onRemovePitcherSlot={handleRemovePitcherSlot}
                dragOverSlot={dragOverSlot}
                setDragOverSlot={setDragOverSlot}
              />
            </div>
          </div>
        </div>
      </div>

      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap" />
    </div>
  )
}