import { useState, useEffect } from "react"
import { PageLayout, TopBar, SummaryBar } from "../components/Layout"
import type { Batter, Pitcher } from "../data/mockPlayers"
import Graph from "../components/Graphs"
import type { SimulationResult } from "../data/mockSimulations"
import { fetchHistory, matchToGame, type MatchResponse } from "../api/simulate"
import { fetchPlayerStats, type PlayerStats as APIPlayerStats } from "../api/playerStats"
import { teamNameToAbbr } from "../data/teamMeta"
import type { Route } from "./+types/history"
import { requireAuth } from "../utils/auth"

export async function loader({ request }: Route.LoaderArgs) {
  return await requireAuth(request)
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
    <span style={{ fontSize: 16, fontWeight: 700, color: win ? "#4ade80" : "#f87171" }}>{val}</span>
  )
}

// ─── Expanded row ─────────────────────────────────────────────────────────────
function ExpandedRow({ result }: { result: SimulationResult }) {
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
                <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255, 255, 255, 0.64)" }}>
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
        <div style={{ margin: "0 0 4px 0", background: "rgba(13,17,23,0.7)", border: "0.5px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "18px 20px", display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Player lineups */}
          <div style={{ display: "flex", gap: 32 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#e84057", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 14 }}>Away Lineup</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <Section title="Batters"  players={result.away.batters}  accent="#e84057" />
                <Section title="Pitchers" players={result.away.pitchers} accent="#e84057" />
              </div>
            </div>
            <div style={{ width: "0.5px", background: "rgba(255,255,255,0.07)", flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#3b82f6", letterSpacing: ".08em", textTransform: "uppercase", marginBottom: 14 }}>Home Lineup</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <Section title="Batters"  players={result.home.batters}  accent="#3b82f6" />
                <Section title="Pitchers" players={result.home.pitchers} accent="#3b82f6" />
              </div>
            </div>
          </div>

          {/* Graph — uses the linked game from mockData */}
          <Graph
            game={result.game}
            isEmbedded={false}
            fullWidth={true}
            backgroundColor="rgba(13,17,23,0.6)"
          />
        </div>
      </td>
    </tr>
  )
}
// ─── API → view-model adapters ────────────────────────────────────────────────
//
// The history endpoint stores lineups as MLBAM id arrays. We resolve them
// against the player-stats endpoint (same mapping the sandbox / stats pages use)
// so each saved match can show its real rosters. team/colour aren't persisted,
// so they fall back to the neutral "MLB" placeholder.

function toBatter(p: APIPlayerStats): Batter {
  return {
    id: p.id,
    name: p.name,
    mlbamId: p.id,
    pa: p.pa_count,
    avg: Number(p.avg.toFixed(3)),
    obp: Number(p.obp.toFixed(3)),
    slg: Number(p.slg.toFixed(3)),
    iso: Number(p.iso.toFixed(3)),
    k_rate: Number((p.k_rate * 100).toFixed(1)),
    bb_rate: Number((p.bb_rate * 100).toFixed(1)),
    hr_rate: Number((p.hr_rate * 100).toFixed(1)),
    stand: p.hand === "L" ? "L" : p.hand === "R" ? "R" : "S",
    team: p.team,
    teamAbbr: teamNameToAbbr[p.team] ?? "MLB",
    teamColor: "#888888",
    is_rookie: p.is_rookie === "1",
  }
}

function toPitcher(p: APIPlayerStats): Pitcher {
  return {
    id: p.id,
    name: p.name,
    mlbamId: p.id,
    pa: p.pa_count,
    avg: Number(p.avg.toFixed(3)),
    obp: Number(p.obp.toFixed(3)),
    slg: Number(p.slg.toFixed(3)),
    iso: Number(p.iso.toFixed(3)),
    k_rate: Number((p.k_rate * 100).toFixed(1)),
    bb_rate: Number((p.bb_rate * 100).toFixed(1)),
    hr_rate: Number((p.hr_rate * 100).toFixed(1)),
    throws: p.hand === "L" ? "L" : "R",
    team: p.team,
    teamAbbr: teamNameToAbbr[p.team] ?? "MLB",
    teamColor: "#888888",
    is_new: p.is_rookie === "1",
  }
}

function matchToResult(match: MatchResponse, byId: Map<number, APIPlayerStats>): SimulationResult {
  const resolveBatters = (ids: number[]) =>
    ids.map(id => byId.get(id)).filter((p): p is APIPlayerStats => !!p).map(toBatter)
  const resolvePitchers = (ids: number[]) =>
    ids.map(id => byId.get(id)).filter((p): p is APIPlayerStats => !!p).map(toPitcher)

  const wg = match.whole_game
  const created = match.created_at ? new Date(match.created_at) : null

  return {
    id: match.match_id,
    date: created
      ? created.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
      : "—",
    time: created ? created.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : "",
    game: matchToGame(match, "Away", "Home"),
    away: {
      batters: resolveBatters(match.away_batter_ids),
      pitchers: resolvePitchers(match.away_pitcher_ids),
      hits: Math.round(wg.avg_away_hits),
      strikeouts: Math.round(wg.avg_away_strikeouts),
      homeruns: Math.round(wg.avg_away_hr),
      score: Math.round(wg.avg_away_runs),
    },
    home: {
      batters: resolveBatters(match.home_batter_ids),
      pitchers: resolvePitchers(match.home_pitcher_ids),
      hits: Math.round(wg.avg_home_hits),
      strikeouts: Math.round(wg.avg_home_strikeouts),
      homeruns: Math.round(wg.avg_home_hr),
      score: Math.round(wg.avg_home_runs),
    },
  }
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function History() {
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [search, setSearch] = useState("")
  const [results, setResults] = useState<SimulationResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const [matches, players] = await Promise.all([fetchHistory(), fetchPlayerStats()])
        if (cancelled) return
        const byId = new Map(players.map(p => [p.id, p]))
        // Most-recent first.
        const mapped = matches
          .map(m => matchToResult(m, byId))
          .sort((a, b) => b.id - a.id)
        setResults(mapped)
        setError(null)
      } catch (err: any) {
        if (!cancelled) setError(err?.message ?? "Failed to load history")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const filtered = results.filter(r =>
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
    <PageLayout activePath="/history" backgroundImage="/images/bg-history.jpg">
        {/* Topbar */}
        <TopBar title="Simulation History" />

        {/* Search */}
        <div style={{ padding: "12px 24px", borderBottom: "0.5px solid rgba(255,255,255,0.06)", flexShrink: 0 }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by date"
            aria-label="Search simulation history"
            style={{ width: "100%", maxWidth: 400, color: "rgba(255, 255, 255, 0.84)", background: "rgba(13, 17, 23, 0.85)", border: "0.5px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "8px 14px", fontSize: 15, fontWeight: 600, fontFamily: "'DM Sans', sans-serif", outline: "none" }}
          />
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: "left", fontSize: 16, color: "rgba(255,255,255,0.8)" }}>Loading your simulation history…</div>
          ) : error ? (
            <div style={{ padding: 40, textAlign: "left", fontSize: 16, color: "rgba(255,255,255,0.9)", background: "rgba(192,30,46,0.5)", borderRadius: 10 }}>{error}</div>
          ) : results.length === 0 ? (
            <div style={{ padding: 40, textAlign: "left", fontSize: 16, color: "rgba(255,255,255,0.8)" }}>No simulations yet — run one in the Sandbox and it will show up here.</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: 40, textAlign: "left", fontSize: 16, color: "rgba(255,255,255,0.8)", background: "rgba(192,30,46,0.5)", borderRadius: 10}}>No simulations match your search</div>
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
        <SummaryBar items={[
            { label: "Total simulations", value: String(results.length) },
            { label: "Away wins", value: String(results.filter(r => r.away.score > r.home.score).length) },
            { label: "Home wins", value: String(results.filter(r => r.home.score > r.away.score).length) },
            { label: "Home Win %", value: results.length ? String((results.filter(r => r.home.score > r.away.score).length / results.length * 100).toFixed(2)) : "—" },
        ]} />
    </PageLayout>
  )
}
