import { useState, useEffect, useRef } from "react"
import { PageLayout, TopBar, SummaryBar } from "../components/Layout";
import type { Batter, Pitcher } from "../data/mockPlayers"
import Graph from "../components/Graphs";
import type { Game, InningScore as GameInningScore } from "../data/mockData"
import type { Route } from "./+types/sandbox"
import { requireAuth } from "../utils/auth"
import { fetchPlayerStats, type PlayerStats as APIPlayerStats } from "../api/playerStats"
import { teamNameToAbbr } from "../data/teamMeta";

export async function loader({ request }: Route.LoaderArgs) {
  return await requireAuth(request)
}

// ─── Types ───────────────────────────────────────────────────────────────────

type PlayerSlot = Batter | Pitcher | null
type TeamSide = "home" | "away"

interface TeamLineup {
  batters: (Batter | null)[]   // always 9 slots
  pitchers: (Pitcher | null)[] // at least 1 slot
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
  batters: Batter[]
  pitchers: Pitcher[]
}

function PlayerPool({ search, onSearchChange, tab, onTabChange, onDragStart, batters: battersProp, pitchers: pitchersProp }: PlayerPoolProps) {
    const batters = battersProp.filter(p =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.team.toLowerCase().includes(search.toLowerCase())
    )
    const pitchers = pitchersProp.filter(p =>
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

// ─── Team Lineup Table (with reset button) ───────────────────────────────────

interface TeamTableProps {
  side: TeamSide
  lineup: TeamLineup
  onDrop: (e: React.DragEvent, side: TeamSide, section: "batters" | "pitchers", index: number) => void
  onRemove: (side: TeamSide, section: "batters" | "pitchers", index: number) => void
  onReorder: (side: TeamSide, section: "batters" | "pitchers", from: number, to: number) => void
  onAddPitcherSlot: (side: TeamSide) => void
  onRemovePitcherSlot: (side: TeamSide) => void
  onResetTeam: (side: TeamSide) => void  // New prop
  dragOverSlot: { side: TeamSide; section: "batters" | "pitchers"; index: number } | null
  setDragOverSlot: (v: { side: TeamSide; section: "batters" | "pitchers"; index: number } | null) => void
}

function TeamTable({ side, lineup, onDrop, onRemove, onReorder, onAddPitcherSlot, onRemovePitcherSlot, onResetTeam, dragOverSlot, setDragOverSlot }: TeamTableProps) {
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
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      background: "rgba(13,17,23,0.75)",
      border: `0.5px solid rgba(255,255,255,0.1)`,
      borderRadius: 10,
      overflow: "hidden"
    }}>
      {/* Team header with reset button */}
      <div style={{
        padding: "14px 16px",
        borderBottom: "0.5px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0
      }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: accentColor, letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 2 }}>
            {label}
          </div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>
            {battersFilled}/9 batters · {pitchersFilled}/{lineup.pitchers.length} pitchers
          </div>
        </div>

        {/* Reset button for this team */}
        <button
          onClick={() => onResetTeam(side)}
          aria-label={`Reset ${label} lineup`}
          style={{
            padding: "6px 12px",
            background: "rgba(255,255,255,0.05)",
            border: "0.5px solid rgba(255,255,255,0.15)",
            borderRadius: 6,
            color: "rgba(255,255,255,0.7)",
            cursor: "pointer",
            fontFamily: "'DM Sans', sans-serif",
            fontSize: 12,
            fontWeight: 500,
            transition: "all .15s",
            display: "flex",
            alignItems: "center",
            gap: 6
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.1)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)";
            e.currentTarget.style.color = "rgba(255,255,255,0.9)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
            e.currentTarget.style.color = "rgba(255,255,255,0.7)";
          }}
        >
          <span>⟳</span> Reset
        </button>
      </div>

      {/* Two column layout - EQUAL WIDTH */}
      <div style={{
        flex: 1,
        display: "flex",
        gap: 12,
        padding: "12px 12px",
        overflow: "hidden",
        minHeight: 0
      }}>
        {/* Batters Column */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          background: "rgba(255,255,255,0.02)",
          borderRadius: 8,
          border: "0.5px solid rgba(255,255,255,0.05)"
        }}>
          <div style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(255, 255, 255, 0.75)",
            letterSpacing: ".1em",
            textTransform: "uppercase",
            padding: "10px 12px",
            borderBottom: "0.5px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.03)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Batting Order</span>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>
              9 slots
            </span>
          </div>
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "8px 8px"
          }}>
            {lineup.batters.map((player, i) => (
              <SlotRow
                key={i}
                index={i}
                label={String(i + 1)}
                player={player}
                onDrop={(e, idx) => handleDrop(e, "batters", idx)}
                onRemove={idx => onRemove(side, "batters", idx)}
                onDragStartSlot={(e, idx) => handleDragStartSlot(e, "batters", idx)}
                onDragOverSlot={(e, idx) => handleDragOverSlot(e, "batters", idx)}
                onDragEndSlot={() => setDragOverSlot(null)}
                isDragOver={dragOverSlot?.side === side && dragOverSlot?.section === "batters" && dragOverSlot?.index === i}
              />
            ))}
          </div>
        </div>

        {/* Pitchers Column with controls in header */}
        <div style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          background: "rgba(255,255,255,0.02)",
          borderRadius: 8,
          border: "0.5px solid rgba(255,255,255,0.05)"
        }}>
          <div style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(255, 255, 255, 0.75)",
            letterSpacing: ".1em",
            textTransform: "uppercase",
            padding: "10px 12px",
            borderBottom: "0.5px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.03)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Pitching Staff</span>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginRight: 4 }}>
                {lineup.pitchers.length} slot{lineup.pitchers.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemovePitcherSlot(side);
                }}
                disabled={lineup.pitchers.length <= 1}
                aria-label="Remove pitcher slot"
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.08)",
                  border: "0.5px solid rgba(255,255,255,0.15)",
                  color: lineup.pitchers.length <= 1 ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.8)",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: lineup.pitchers.length <= 1 ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'DM Sans', sans-serif",
                  transition: "all .15s"
                }}
                onMouseEnter={(e) => {
                  if (lineup.pitchers.length > 1) {
                    e.currentTarget.style.background = "rgba(255,255,255,0.15)";
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                }}
              >
                −
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddPitcherSlot(side);
                }}
                aria-label="Add pitcher slot"
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 4,
                  background: "rgba(255,255,255,0.08)",
                  border: "0.5px solid rgba(255,255,255,0.15)",
                  color: "rgba(255,255,255,0.8)",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'DM Sans', sans-serif",
                  transition: "all .15s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.15)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                }}
              >
                +
              </button>
            </div>
          </div>
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "8px 8px"
          }}>
            {lineup.pitchers.map((player, i) => (
              <SlotRow
                key={i}
                index={i}
                label="P"
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
      </div>
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

// Helper to generate mock game data for the Graph component
function generateMockGame(homeLineup: TeamLineup, awayLineup: TeamLineup): Game | null {
  // Get team names from first batter or fallback
  const homeBatter = homeLineup.batters.find(b => b !== null)
  const awayBatter = awayLineup.batters.find(b => b !== null)

  if (!homeBatter || !awayBatter) return null

  const homeTeam = homeBatter.team
  const awayTeam = awayBatter.team

  // Generate mock innings (9 innings)
  const innings: GameInningScore[] = Array.from({ length: 9 }, (_, i) => ({
    inning: i + 1,
    team1: Math.random() < 0.35 ? Math.floor(Math.random() * 3) : 0,
    team2: Math.random() < 0.35 ? Math.floor(Math.random() * 3) : 0,
    hits1: Math.floor(Math.random() * 4),
    hits2: Math.floor(Math.random() * 4),
    hrs1: Math.floor(Math.random() * 2),
    hrs2: Math.floor(Math.random() * 2),
    ks1: Math.floor(Math.random() * 3),
    ks2: Math.floor(Math.random() * 3),
  }))

  // Calculate totals
  const totalHits1 = innings.reduce((sum, inn) => sum + inn.hits1, 0)
  const totalHits2 = innings.reduce((sum, inn) => sum + inn.hits2, 0)
  const totalHrs1 = innings.reduce((sum, inn) => sum + inn.hrs1, 0)
  const totalHrs2 = innings.reduce((sum, inn) => sum + inn.hrs2, 0)
  const totalKs1 = innings.reduce((sum, inn) => sum + inn.ks1, 0)
  const totalKs2 = innings.reduce((sum, inn) => sum + inn.ks2, 0)

  return {
    id: 1,
    team1: awayTeam, // Note: Graph expects team1 as first argument
    team2: homeTeam,
    innings: innings,
    hits: [totalHits1, totalHits2] as [number, number],
    homeruns: [totalHrs1, totalHrs2] as [number, number],
    strikeouts: [totalKs1, totalKs2] as [number, number],
    prob1: 45,
    prob2: 55,
    date: "June 10",
    time: "8:00 PM"
  }
}

export default function Sandbox() {
  const [home, setHome] = useState<TeamLineup>(emptyLineup())
  const [away, setAway] = useState<TeamLineup>(emptyLineup())
  const [poolSearch, setPoolSearch] = useState("")
  const [poolTab, setPoolTab] = useState<"batter" | "pitcher">("batter")
  const [realBatters, setRealBatters] = useState<Batter[]>([])
  const [realPitchers, setRealPitchers] = useState<Pitcher[]>([])
  const [loadingPlayers, setLoadingPlayers] = useState(true)
  const [dragOverSlot, setDragOverSlot] = useState<{ side: TeamSide; section: "batters" | "pitchers"; index: number } | null>(null)
  const [gameData, setGameData] = useState<Game | null>(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [hasSimulated, setHasSimulated] = useState(false)
  const dragPayload = useRef<{ player: Batter | Pitcher; type: "batter" | "pitcher" } | null>(null)

    // Fetch real player data
  useEffect(() => {
    const loadPlayers = async () => {
      try {
        setLoadingPlayers(true);
        const data = await fetchPlayerStats();
        console.log("Total players loaded:", data.length);
        
        // Transform batters (same as Statistics page)
        const battersData: Batter[] = data
          .filter(player => player.is_batter === true)
          .map(player => ({
            id: player.id,
            name: player.name,
            mlbamId: player.id,
            pa: player.pa_count,
            avg: Number(player.avg.toFixed(3)),
            obp: Number(player.obp.toFixed(3)),
            slg: Number(player.slg.toFixed(3)),
            iso: Number(player.iso.toFixed(3)),
            k_rate: Number((player.k_rate * 100).toFixed(1)),
            bb_rate: Number((player.bb_rate * 100).toFixed(1)),
            hr_rate: Number((player.hr_rate * 100).toFixed(1)),
            stand: player.hand === "L" ? "L" : player.hand === "R" ? "R" : "S",
            team: "MLB",
            teamAbbr: teamNameToAbbr["MLB"] || "#888888",
            teamColor: "#888888",
            is_rookie: player.is_rookie === "1",
          }));
        
        // Transform pitchers
        const pitchersData: Pitcher[] = data
          .filter(player => player.is_batter === false)
          .map(player => ({
            id: player.id,
            name: player.name,
            mlbamId: player.id,
            pa: player.pa_count,
            avg: Number(player.avg.toFixed(3)),
            obp: Number(player.obp.toFixed(3)),
            slg: Number(player.slg.toFixed(3)),
            iso: Number(player.iso.toFixed(3)),
            k_rate: Number((player.k_rate * 100).toFixed(1)),
            bb_rate: Number((player.bb_rate * 100).toFixed(1)),
            hr_rate: Number((player.hr_rate * 100).toFixed(1)),
            throws: player.hand === "L" ? "L" : "R",
            team: "MLB",
            teamAbbr: teamNameToAbbr["MLB"] || "#888888",
            teamColor: "#888888",
            is_new: player.is_rookie === "1",
          }));
        
        setRealBatters(battersData);
        setRealPitchers(pitchersData);
        setLoadingPlayers(false);
      } catch (err) {
        console.error("Failed to load players:", err);
        setLoadingPlayers(false);
      }
    };
    
    loadPlayers();
  }, []);

  // Check if both teams have complete lineups
  const isLineupComplete = () => {
    const homeBattersCount = home.batters.filter(Boolean).length
    const awayBattersCount = away.batters.filter(Boolean).length
    const homePitchersCount = home.pitchers.filter(Boolean).length
    const awayPitchersCount = away.pitchers.filter(Boolean).length

    return homeBattersCount === 9 &&
           awayBattersCount === 9 &&
           homePitchersCount >= 1 &&
           awayPitchersCount >= 1
  }

  const lineupComplete = isLineupComplete()

  // Update game data whenever lineups change
  const updateGameData = () => {
    // Only auto-update if we haven't simulated yet, or reset simulation state
    if (!hasSimulated) {
      const mockGame = generateMockGame(home, away)
      setGameData(mockGame)
    }
  }

  // ── Reset individual team ───────────────────────────────────────────────────
  function handleResetTeam(side: TeamSide) {
    const empty = emptyLineup()
    if (side === "home") {
      setHome(empty)
    } else {
      setAway(empty)
    }
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
  }

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
    if (isReorder) return

    if (!dragPayload.current) return
    const { player, type } = dragPayload.current

    if (section === "batters" && type !== "batter") return
    if (section === "pitchers" && type !== "pitcher") return

    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      const updated = { ...prev, [section]: [...prev[section]] }
      updated[section][index] = player
      return updated
    })
    dragPayload.current = null
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
  }

  // ── Remove from slot ────────────────────────────────────────────────────────
  function handleRemove(side: TeamSide, section: "batters" | "pitchers", index: number) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      const updated = { ...prev, [section]: [...prev[section]] }
      updated[section][index] = null
      return updated
    })
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
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
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
  }

  // ── Add / remove pitcher slots ──────────────────────────────────────────────
  function handleAddPitcherSlot(side: TeamSide) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => ({ ...prev, pitchers: [...prev.pitchers, null] }))
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
  }

  function handleRemovePitcherSlot(side: TeamSide) {
    const setter = side === "home" ? setHome : setAway
    setter(prev => {
      if (prev.pitchers.length <= 1) return prev
      return { ...prev, pitchers: prev.pitchers.slice(0, -1) }
    })
    setHasSimulated(false) // Reset simulation flag when lineups change
    updateGameData()
  }

  // ── Run Simulation ──────────────────────────────────────────────────────────
  async function handleRunSimulation() {
    if (!lineupComplete) return

    setIsSimulating(true)

    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1500))

    // Generate fresh mock data for the simulation
    const simulatedGame = generateMockGame(home, away)
    setGameData(simulatedGame)
    setHasSimulated(true)
    setIsSimulating(false)
  }

  const homeBattersFilled = home.batters.filter(Boolean).length
  const awayBattersFilled = away.batters.filter(Boolean).length
  const homePitchersFilled = home.pitchers.filter(Boolean).length
  const awayPitchersFilled = away.pitchers.filter(Boolean).length

  if (loadingPlayers) {
    return (
      <PageLayout activePath="/sandbox" backgroundImage="/images/bg-sandbox.jpg">
        <TopBar title="Sandbox" />
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "400px" }}>
          <div style={{ color: "white", fontSize: 18 }}>Loading players...</div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout activePath="/sandbox" backgroundImage="/images/bg-sandbox.jpg">
      <TopBar title="Sandbox" />

      <div style={{ flex: 1, display: "flex", overflow: "hidden", padding: "16px 16px 16px 16px", gap: 12 }}>
        {/* Player Pool */}
        <div style={{ width: 220, flexShrink: 0 }}>
          <PlayerPool
            search={poolSearch}
            onSearchChange={setPoolSearch}
            tab={poolTab}
            onTabChange={setPoolTab}
            onDragStart={handlePoolDragStart}
            batters={realBatters}
            pitchers={realPitchers}
          />
        </div>

        {/* Center: lineups + graph */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12, overflow: "hidden" }}>

          {/* Team tables side by side */}
          <div style={{ flex: 1, display: "flex", gap: 12, overflow: "hidden", minHeight: 0 }}>
            <TeamTable
              side="away"
              lineup={away}
              onDrop={handleDrop}
              onRemove={handleRemove}
              onReorder={handleReorder}
              onAddPitcherSlot={handleAddPitcherSlot}
              onRemovePitcherSlot={handleRemovePitcherSlot}
              onResetTeam={handleResetTeam}
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
              onResetTeam={handleResetTeam}
              dragOverSlot={dragOverSlot}
              setDragOverSlot={setDragOverSlot}
            />
          </div>

          {/* Graph Area with Simulation Button */}
          <div style={{ flexShrink: 0 }}>
            {lineupComplete ? (
              <>
                {hasSimulated && gameData ? (
                  <Graph
                    game={gameData}
                    backgroundColor="rgba(13,17,23,0.85)"
                    fullWidth={true}
                    isEmbedded={false}  // Or omit this prop as it defaults to false
                  />
                ) : (
                  <div style={{
                    background: "rgba(13,17,23,0.74)",
                    border: "0.5px solid rgba(255,255,255,0.1)",
                    borderRadius: 10,
                    padding: "40px 20px",
                    textAlign: "center",
                  }}>
                    <div style={{ marginBottom: 20 }}>
                      <div style={{ fontSize: 18, fontWeight: 600, color: "rgba(255,255,255,0.8)", marginBottom: 8 }}>
                        Ready to Simulate!
                      </div>
                      <div style={{ fontSize: 14, color: "rgba(255,255,255,0.6)" }}>
                        Both teams have complete lineups. Click the button below to run the simulation.
                      </div>
                    </div>
                    <button
                      onClick={handleRunSimulation}
                      disabled={isSimulating}
                      style={{
                        padding: "12px 32px",
                        background: "linear-gradient(135deg, rgba(192,30,46,0.9) 0%, rgba(192,30,46,0.7) 100%)",
                        border: "0.5px solid rgba(192,30,46,0.5)",
                        borderRadius: 8,
                        color: "white",
                        cursor: isSimulating ? "wait" : "pointer",
                        fontFamily: "'DM Sans', sans-serif",
                        fontSize: 16,
                        fontWeight: 600,
                        transition: "all .2s",
                        opacity: isSimulating ? 0.7 : 1,
                        transform: isSimulating ? "none" : "translateY(-1px)",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSimulating) {
                          e.currentTarget.style.background = "linear-gradient(135deg, rgba(192,30,46,1) 0%, rgba(192,30,46,0.85) 100%)";
                          e.currentTarget.style.transform = "translateY(-2px)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSimulating) {
                          e.currentTarget.style.background = "linear-gradient(135deg, rgba(192,30,46,0.9) 0%, rgba(192,30,46,0.7) 100%)";
                          e.currentTarget.style.transform = "translateY(-1px)";
                        }
                      }}
                    >
                      {isSimulating ? (
                        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          Simulating...
                        </span>
                      ) : (
                        <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          Run Simulation
                        </span>
                      )}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div style={{
                background: "rgba(13,17,23,0.74)",
                border: "0.5px solid rgba(255,255,255,0.1)",
                borderRadius: 10,
                padding: "40px 20px",
                textAlign: "center",
              }}>
                <div style={{ fontSize: 15, color: "rgba(255,255,255,0.6)", marginBottom: 12 }}>
                  Complete both lineups to run simulation
                </div>
                <div style={{ display: "flex", gap: 20, justifyContent: "center", fontSize: 13 }}>
                  {homeBattersFilled !== 9 && (
                    <div style={{ color: "#f07080" }}>
                      Home needs {9 - homeBattersFilled} more batter{9 - homeBattersFilled !== 1 ? 's' : ''}
                    </div>
                  )}
                  {awayBattersFilled !== 9 && (
                    <div style={{ color: "#f07080" }}>
                      Away needs {9 - awayBattersFilled} more batter{9 - awayBattersFilled !== 1 ? 's' : ''}
                    </div>
                  )}
                  {homePitchersFilled === 0 && (
                    <div style={{ color: "#f07080" }}>
                      Home needs at least 1 pitcher
                    </div>
                  )}
                  {awayPitchersFilled === 0 && (
                    <div style={{ color: "#f07080" }}>
                      Away needs at least 1 pitcher
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
