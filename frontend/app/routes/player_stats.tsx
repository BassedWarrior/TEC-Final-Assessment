import { useState, useEffect, useMemo } from "react"
import Sidebar from "../../src/components/Sidebar"
import { MOCK_BATTERS, MOCK_PITCHERS, TEAMS } from "../../src/data/mockPlayers"
import type { Batter, Pitcher } from "../../src/data/mockPlayers"

type Tab = "batter" | "pitcher"
type SortKey = "name" | "pa" | "avg" | "obp" | "slg" | "iso" | "k_rate" | "bb_rate" | "status" | "stand"
type SortDir = "asc" | "desc"

// ─── Helpers ─────────────────────────────────────────────────────────────────

function mlbHeadshotUrl(mlbamId: number) {
  return `https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/${mlbamId}/headshot/67/current`
}

function initials(name: string) {
  return name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()
}

function fmt(v: number, d = 3) {
  return v.toFixed(d).replace(/^0/, "")
}

function avgColor(v: number) {
  if (v >= 0.29) return "#4ade80"
  if (v >= 0.25) return "#fbbf24"
  return "#f87171"
}

function avgColorInverted(v: number) {
  if (v <= 0.22) return "#4ade80"
  if (v <= 0.25) return "#fbbf24"
  return "#f87171"
}

function kColor(v: number, isPitcher = false) {
  if (isPitcher) return v >= 28 ? "#4ade80" : v >= 22 ? "#fbbf24" : "#f87171"
  return v <= 20 ? "#4ade80" : v <= 27 ? "#fbbf24" : "#f87171"
}

function bbColor(v: number) {
  return v >= 10 ? "#4ade80" : v >= 7 ? "#fbbf24" : "#f87171"
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PlayerPhoto({ mlbamId, name, color, size = 40 }: { mlbamId: number; name: string; color: string; size?: number }) {
  const [imgError, setImgError] = useState(false)

  if (imgError) {
    return (
      <div style={{
        width: size, height: size, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: size * 0.32, fontWeight: 700,
        background: `${color}22`, color,
        border: `0.5px solid ${color}55`,
      }}>
        {initials(name)}
      </div>
    )
  }

  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      overflow: "hidden", background: `${color}15`,
      border: `0.5px solid ${color}40`,
    }}>
      <img
        src={mlbHeadshotUrl(mlbamId)}
        alt={name}
        
        style={{ 
          width: "100%",
          height: "120%",          
          objectFit: "cover",
          objectPosition: "top 20%", 
          marginTop: "-10%" 
        }}
      />
    </div>
  )
}

function Badge({ children, color, bg }: { children: React.ReactNode; color: string; bg: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 4,
      fontSize: 13, fontWeight: 600,
      color, background: bg,
    }}>
      {children}
    </span>
  )
}

function RateBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.73)", width: 80, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.07)", borderRadius: 2, overflow: "hidden", margin: "0 10px" }}>
        <div style={{ height: "100%", width: `${Math.min((value / max) * 100, 100)}%`, background: color, borderRadius: 2, transition: "width .4s ease" }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color, minWidth: 40, textAlign: "right" }}>{value}%</span>
    </div>
  )
}

function StatBox({ value, label, color }: { value: string; label: string; color?: string }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.03)", border: "0.5px solid rgba(255,255,255,0.07)", borderRadius: 8, padding: "10px 12px" }}>
      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 20, fontWeight: 700, color: color ?? "#f0ede6", marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", textTransform: "uppercase", letterSpacing: ".06em" }}>{label}</div>
    </div>
  )
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  return (
    <span style={{ marginLeft: 4, opacity: active ? 1 : 0.3, fontSize: 12, color: "white" }}>
      {active ? (dir === "asc" ? "↑" : "↓") : "↕"}
    </span>
  )
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

function DetailPanel({ player, tab, onClose }: { player: Batter | Pitcher | null; tab: Tab; onClose: () => void }) {
  if (!player) return (
    <div style={{ width: 0, transition: "width .25s ease", overflow: "hidden", flexShrink: 0 }} />
  )

  const isBatter = tab === "batter"
  const b = player as Batter
  const p = player as Pitcher

  return (
    <div style={{
      width: 290, flexShrink: 0,
      background: "#0d1117",
      borderLeft: "0.5px solid rgba(255, 255, 255, 0.1)",
      display: "flex", flexDirection: "column",
      overflowY: "auto",
      transition: "width .25s ease",
    }}>
      {/* Header */}
      <div style={{ padding: 20, borderBottom: "0.5px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <PlayerPhoto mlbamId={player.mlbamId} name={player.name} color={player.teamColor} size={70} />
          <div>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 700, color: "rgba(255,255,255,1)", marginBottom: 3 }}>{player.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "rgba(255, 255, 255, 0.66)", marginBottom: 7 }}>
              {player.team} · {isBatter ? (b.is_rookie ? "Rookie Batter" : "Batter") : (p.is_new ? "New Pitcher" : "Pitcher")}
            </div>
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
              {(isBatter ? b.is_rookie : p.is_new) && (
                <Badge color="rgb(255, 225, 114)" bg="rgba(255, 200, 0, 0.1)">Rookie</Badge>
              )}
              {isBatter ? (
                <Badge
                  color={b.stand === "L" ? "#7099f0" : b.stand === "S" ? "#99f070" : "#f07080"}
                  bg={b.stand === "L" ? "rgba(30,100,192,0.15)" : b.stand === "S" ? "rgba(100,192,30,0.15)" : "rgba(192,30,46,0.15)"}>
                  Bats {b.stand}
                </Badge>
              ) : (
                <Badge
                  color={p.throws === "R" ? "#f07080" : "#7099f0"}
                  bg={p.throws === "R" ? "rgba(192,30,46,0.15)" : "rgba(30,100,192,0.15)"}>
                  Throws {p.throws}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <button onClick={onClose} aria-label="Close panel"
          style={{ background: "rgba(255,255,255,0.05)", border: "0.5px solid rgba(255, 255, 255, 0.34)", borderRadius: 6, width: 26, height: 26, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "rgba(255, 255, 255, 0.81)", fontSize: 13, flexShrink: 0 }}>
          ✕
        </button>
      </div>

      {/* Core stats — only uses fields that exist in mockPlayers.ts */}
      <div style={{ padding: 16, borderBottom: "0.5px solid rgba(255,255,255,0.05)" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.83)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 10 }}>Core Stats</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <StatBox value={fmt(player.avg)} label={isBatter ? "Batting Avg" : "AVG Allowed"} color={isBatter ? avgColor(player.avg) : avgColorInverted(player.avg)} />
          <StatBox value={fmt(player.obp)} label={isBatter ? "On-base %" : "OBP Allowed"} color={isBatter ? avgColor(player.obp) : avgColorInverted(player.obp)} />
          <StatBox value={fmt(player.slg)} label={isBatter ? "Slugging %" : "SLG Allowed"} />
          <StatBox value={fmt(player.iso)} label="Iso Power" />
        </div>
      </div>

      {/* Rates */}
      <div style={{ padding: 16, borderBottom: "0.5px solid rgba(255,255,255,0.05)" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.76)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 12 }}>Rates</div>
        <RateBar label="Strikeout %" value={player.k_rate} max={40} color={isBatter ? "#f87171" : "#4ade80"} />
        <RateBar label="Walk %" value={player.bb_rate} max={20} color="#fbbf24" />
        <RateBar label="HR rate" value={player.hr_rate} max={15} color="#f07080" />
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Statistics() {
  const [tab, setTab] = useState<Tab>("batter")
  const [search, setSearch] = useState("")
  const [teamFilter, setTeamFilter] = useState("")
  const [rookieFilter, setRookieFilter] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("avg")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [selected, setSelected] = useState<Batter | Pitcher | null>(null)

  useEffect(() => { setSelected(null) }, [tab])

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc")
    else { setSortKey(key); setSortDir("desc") }
  }

  const batters = useMemo(() => {
    let data = [...MOCK_BATTERS]
    if (search) data = data.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.team.toLowerCase().includes(search.toLowerCase()))
    if (teamFilter) data = data.filter(p => p.team === teamFilter)
    if (rookieFilter === "rookie") data = data.filter(p => p.is_rookie)
    if (rookieFilter === "vet") data = data.filter(p => !p.is_rookie)
    data.sort((a, b) => {
      if (sortKey === "status") {
        return sortDir === "asc"
          ? Number(a.is_rookie) - Number(b.is_rookie)
          : Number(b.is_rookie) - Number(a.is_rookie)
      }

      const av = a[sortKey as keyof Batter]
      const bv = b[sortKey as keyof Batter]

      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc"
          ? av.localeCompare(bv)
          : bv.localeCompare(av)
      }

      return sortDir === "asc"
        ? (av as number) - (bv as number)
        : (bv as number) - (av as number)
    })
    return data
  }, [search, teamFilter, rookieFilter, sortKey, sortDir])

  const pitchers = useMemo(() => {
    let data = [...MOCK_PITCHERS]
    if (search) data = data.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.team.toLowerCase().includes(search.toLowerCase()))
    if (teamFilter) data = data.filter(p => p.team === teamFilter)
    if (rookieFilter === "rookie") data = data.filter(p => p.is_new)
    if (rookieFilter === "vet") data = data.filter(p => !p.is_new)
     data.sort((a, b) => {
      if (sortKey === "status") {
        return sortDir === "asc"
          ? Number(a.is_new) - Number(b.is_new)
          : Number(b.is_new) - Number(a.is_new)
      }

      if (sortKey === "stand") {
      return sortDir === "asc"
        ? a.throws.localeCompare(b.throws)
        : b.throws.localeCompare(a.throws)
      }

      const av = a[sortKey as keyof Pitcher]
      const bv = b[sortKey as keyof Pitcher]

      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc"
          ? av.localeCompare(bv)
          : bv.localeCompare(av)
      }

      return sortDir === "asc"
        ? (av as number) - (bv as number)
        : (bv as number) - (av as number)
    })
    return data
  }, [search, teamFilter, rookieFilter, sortKey, sortDir])

  const currentData = tab === "batter" ? batters : pitchers
  const isPitcher = tab === "pitcher"

  const thStyle = (key: SortKey): React.CSSProperties => ({
    padding: "11px 14px",
    fontSize: 13, fontWeight: 1000,
    color: sortKey === key ? "rgb(255, 87, 87)" : "rgba(255, 255, 255, 0.92)",
    textAlign: "left",
    letterSpacing: ".08em",
    textTransform: "uppercase",
    whiteSpace: "nowrap",
    cursor: "pointer",
    userSelect: "none",
  })

  const tdStyle: React.CSSProperties = { padding: "13px 14px", fontSize: 15, verticalAlign: "middle" }

  // Summary stats
  const avgMean = currentData.length
    ? (currentData.reduce((s, p) => s + p.avg, 0) / currentData.length)
    : 0
  const rookieCount = tab === "batter"
    ? batters.filter(p => p.is_rookie).length
    : pitchers.filter(p => p.is_new).length

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'DM Sans', sans-serif", backgroundImage: "url(https://assets.goal.com/images/v3/bltc07718a3e3f2f638/Texas_Rangers_vs_Chicago_Cubs_MLB_game.png?auto=webp&format=pjpg&width=3840&quality=60)", backgroundSize: "cover", backgroundPosition: "center-top" }}>
      <Sidebar activePath="/statistics" />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Topbar */}
        <div style={{ padding: "18px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 600,color: "rgb(255, 255, 255)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 3 }}>MLB · 2025</div>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 40, fontWeight: 700, color: "#f0ede6" }}>Player Statistics</h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(255, 255, 255, 0.12)", border: "0.5px solid rgba(255, 255, 255, 0.23)", borderRadius: 6, padding: "7px 12px", fontSize: 14, color: "rgb(255, 255, 255)" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "rgb(96, 255, 16)" }} />
            2025 Season
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", flexShrink: 0, flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: 3, background: "rgba(255,255,255,0.04)", borderRadius: 6, padding: 3 }}>
            {(["batter", "pitcher"] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)}
                style={{ padding: "5px 14px", borderRadius: 4, fontSize: 16, fontWeight: 600, border: "0.5px solid rgba(255, 255, 255, 0.42)", cursor: "pointer", fontFamily: "'DM Sans', sans-serif", transition: "all .15s", background: tab === t ? "rgba(192,30,46,0.2)" : "transparent", color: tab === t ? "#f07080" : "rgba(255, 255, 255, 0.84)" }}>
                {t === "batter" ? "Batters" : "Pitchers"}
              </button>
            ))}
          </div>
          <div style={{ position: "relative", flex: 1, minWidth: 160 }}>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search player or team..."
              aria-label="Search players"
              style={{ width: "100%", color: "rgb(255, 255, 255)", background: "rgba(35, 5, 5, 0.13)", border: "0.5px solid rgba(255, 255, 255, 0.43)", borderRadius: 6, padding: "8px 12px", fontSize: 15, fontFamily: "'DM Sans', sans-serif", fontWeight: 600, outline: "none" }} />
          </div>
          <select value={teamFilter} onChange={e => setTeamFilter(e.target.value)} aria-label="Filter by team"
            style={{ background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "8px 10px", fontSize: 14, color: "rgb(255, 255, 255)", fontFamily: "'DM Sans', sans-serif", outline: "none", cursor: "pointer" }}>
            <option value="">All teams</option>
            {TEAMS.map(t => <option key={t}>{t}</option>)}
          </select>
          <select value={rookieFilter} onChange={e => setRookieFilter(e.target.value)} aria-label="Filter by experience"
            style={{ background: "rgba(255,255,255,0.04)", border: "0.5px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "8px 10px", fontSize: 14, color: "rgb(255, 255, 255)", fontFamily: "'DM Sans', sans-serif", outline: "none", cursor: "pointer" }}>
            <option value="">All players</option>
            <option value="rookie">Rookies only</option>
            <option value="vet">Veterans only</option>
          </select>
        </div>

        {/* Table + Detail panel */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
            <div style={{ background: "rgba(13, 17, 23, 0.63)", borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.07)", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }} aria-label="Player statistics">
                <thead>
                  <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.07)" }}>
                    <th style={{ ...thStyle("name"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("name")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        Player <SortIcon active={sortKey === "name"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("pa"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("pa")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        PA <SortIcon active={sortKey === "pa"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("avg"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("avg")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        {isPitcher ? "AVG Allowed" : "AVG"} <SortIcon active={sortKey === "avg"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("obp"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("obp")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        {isPitcher ? "OBP Allowed" : "OBP"} <SortIcon active={sortKey === "obp"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("slg"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("slg")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        {isPitcher ? "SLG Allowed" : "SLG"} <SortIcon active={sortKey === "slg"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("iso"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("iso")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        ISO <SortIcon active={sortKey === "iso"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("k_rate"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("k_rate")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        K% <SortIcon active={sortKey === "k_rate"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("bb_rate"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("bb_rate")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        BB% <SortIcon active={sortKey === "bb_rate"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("stand"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("stand")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        {isPitcher ? "Throws" : "Stand"} <SortIcon active={sortKey === "stand"} dir={sortDir} />
                      </button>
                    </th>
                    <th style={{ ...thStyle("status"), padding: 0 }}>
                      <button
                        onClick={() => handleSort("status")}
                        style={{
                          width: "100%",
                          textAlign: "left",
                          padding: "11px 14px",
                          background: "transparent",
                          border: "none",
                          fontSize: "inherit",
                          fontWeight: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        Status <SortIcon active={sortKey === "status"} dir={sortDir} />
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {currentData.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ padding: 32, textAlign: "center", color: "rgba(255,255,255,0.25)", fontSize: 13 }}>
                        No players match your filters
                      </td>
                    </tr>
                  ) : currentData.map(player => {
                    const isSelected = selected?.id === player.id
                    const isBat = tab === "batter"
                    const b = player as Batter
                    const p = player as Pitcher
                    return (
                      <tr key={player.id}
                        onClick={() => setSelected(isSelected ? null : player)}
                        style={{ borderBottom: "0.5px solid rgba(255,255,255,0.04)", cursor: "pointer", background: isSelected ? "rgba(204, 190, 192, 0.3)" : "transparent", transition: "background .12s" }}>
                        <td style={tdStyle}>
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <PlayerPhoto mlbamId={player.mlbamId} name={player.name} color={player.teamColor} size={50} />
                            <div>
                              <div style={{ fontSize: 16, fontWeight: 700, color: "#f0ede6" }}>{player.name}</div>
                              <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255, 255, 255, 0.84)" }}>{player.team}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ ...tdStyle, color: "rgba(255, 255, 255, 0.81)", fontVariantNumeric: "tabular-nums" }}>{player.pa}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: isPitcher ? avgColorInverted(player.avg) : avgColor(player.avg), fontVariantNumeric: "tabular-nums" }}>{fmt(player.avg)}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: isPitcher ? avgColorInverted(player.obp) : avgColor(player.obp), fontVariantNumeric: "tabular-nums" }}>{fmt(player.obp)}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: isPitcher ? avgColorInverted(player.slg) : avgColor(player.slg), fontVariantNumeric: "tabular-nums" }}>{fmt(player.slg)}</td>
                        <td style={{ ...tdStyle, color: "rgba(255, 255, 255, 0.81)", fontVariantNumeric: "tabular-nums" }}>{fmt(player.iso)}</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: kColor(player.k_rate, isPitcher), fontVariantNumeric: "tabular-nums" }}>{player.k_rate}%</td>
                        <td style={{ ...tdStyle, fontWeight: 600, color: bbColor(player.bb_rate), fontVariantNumeric: "tabular-nums" }}>{player.bb_rate}%</td>
                        <td style={tdStyle}>
                          {isBat
                            ? <Badge color={b.stand === "L" ? "#7099f0" : b.stand === "S" ? "#99f070" : "#f07080"} bg={b.stand === "L" ? "rgba(30,100,192,0.15)" : b.stand === "S" ? "rgba(100,192,30,0.15)" : "rgba(192,30,46,0.15)"}>{b.stand}</Badge>
                            : <Badge color={p.throws === "R" ? "#f07080" : "#7099f0"} bg={p.throws === "R" ? "rgba(192,30,46,0.15)" : "rgba(30,100,192,0.15)"}>{p.throws}</Badge>
                          }
                        </td>
                        <td style={tdStyle}>
                          {(isBat ? b.is_rookie : p.is_new)
                            ? <Badge color="rgb(255, 225, 114)" bg="rgba(255, 200, 0, 0.1)">Rookie</Badge>
                            :<Badge color="rgb(188, 213, 255)" bg="rgba(0, 51, 255, 0.19)">Veteran</Badge>
                          }
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <DetailPanel player={selected} tab={tab} onClose={() => setSelected(null)} />
        </div>

        {/* Summary bar */}
        <div style={{ display: "flex", background: "rgba(3, 3, 30, 0.33)", borderTop: "0.5px solid rgba(255, 255, 255, 0.29)", flexShrink: 0 }}>
          {[
            [String(currentData.length), "Players shown"],
            [fmt(avgMean), isPitcher ? "Avg AVG allowed" : "Avg batting avg"],
            [String(rookieCount), isPitcher ? "New pitchers" : "Rookies"],
            [currentData.length > 0 ? `${Math.max(...currentData.map(p => p.k_rate))}%` : "—", "Top K rate"],
          ].map(([val, lbl], i, arr) => (
            <div key={lbl} style={{ flex: 1, padding: "13px 20px", borderRight: i < arr.length - 1 ? "0.5px solid rgba(255, 255, 255, 0.34)" : "none" }}>
              <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: "white" }}>{val}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "rgba(255, 255, 255, 0.9)", textTransform: "uppercase", letterSpacing: ".07em" }}>{lbl}</div>
            </div>
          ))}
        </div>
      </div>

      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap" />
    </div>
  )
}
