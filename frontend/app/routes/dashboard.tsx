import { useNavigate } from "react-router"
import { useState, useEffect } from "react"
import { PageLayout, TopBar, SummaryBar } from "../components/Layout";
import Graph from "../components/Graphs";
import { fetchSchedule, type ScheduleGame } from "../api/schedule";
import { fetchDashboardMatches, type DashboardMatch } from "../api/simulations";
import React from 'react';
import { teamNameToAbbr, teamMeta } from "../data/teamMeta";
import { type Game } from "../data/game";

function probFill(p: number) {
  if (p >= 60) return "#16873a"
  if (p <= 40) return "#b3093a"
  return "#c49710"
}

function TeamCell({ name }: { name: string }) {
  const [imgError, setImgError] = useState(false)

  const meta = teamMeta[name] ?? {
    abbr: teamNameToAbbr[name] ?? null,
    color: "#888",
  }

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

// Helper to find a simulation match for a schedule game
function findSimulationMatch(
  scheduleGame: ScheduleGame,
  simulations: DashboardMatch[]
): DashboardMatch | undefined {
  return simulations.find(
    (sim) =>
      sim.home_team === scheduleGame.homeTeamName &&
      sim.away_team === scheduleGame.awayTeamName
  );
}

// Merge schedule and simulation data into a Game object
function mergeToGame(
  scheduleGame: ScheduleGame,
  simulationMatch: DashboardMatch | undefined,
  index: number
): Game {
  // Default placeholders
  let homeWinProb = 0;
  let awayWinProb = 100;
  let innings: Game["innings"] = [];
  let wholeGameStats = { hits: [0,0], homeruns: [0,0], strikeouts: [0,0] };

  if (simulationMatch) {
    homeWinProb = Math.round(simulationMatch.home_wp * 100);
    awayWinProb = Math.round(simulationMatch.away_wp * 100);
    // Convert cumulative inning averages to per-inning values
    innings = simulationMatch.innings.map((inning, i) => {
      const prev = i === 0 ? null : simulationMatch.innings[i-1];
      return {
        inning: inning.inning_number,
        home_runs: inning.avg_home_runs - (prev?.avg_home_runs ?? 0),
        away_runs: inning.avg_away_runs - (prev?.avg_away_runs ?? 0),
        home_hits: inning.avg_home_hits - (prev?.avg_home_hits ?? 0),
        away_hits: inning.avg_away_hits - (prev?.avg_away_hits ?? 0),
        home_hr: inning.avg_home_hr - (prev?.avg_home_hr ?? 0),
        away_hr: inning.avg_away_hr - (prev?.avg_away_hr ?? 0),
        home_strikeouts: inning.avg_home_strikeouts - (prev?.avg_home_strikeouts ?? 0),
        away_strikeouts: inning.avg_away_strikeouts - (prev?.avg_away_strikeouts ?? 0),
      };
    });
    wholeGameStats = {
      hits: [simulationMatch.whole_game.avg_home_hits, simulationMatch.whole_game.avg_away_hits],
      homeruns: [simulationMatch.whole_game.avg_home_hr, simulationMatch.whole_game.avg_away_hr],
      strikeouts: [simulationMatch.whole_game.avg_home_strikeouts, simulationMatch.whole_game.avg_away_strikeouts],
    };
  }

  return {
    id: index,
    homeTeam: scheduleGame.homeTeamName,
    awayTeam: scheduleGame.awayTeamName,
    homeWinProb,
    awayWinProb,
    date: scheduleGame.gameDate,
    time: scheduleGame.gameTime,
    isLive: scheduleGame.isLive,
    isFinal: scheduleGame.isFinal,
    innings,
    winner: null,
    status: scheduleGame.isLive ? "Live" : scheduleGame.isFinal ? "Final" : "Scheduled",
    hits: wholeGameStats.hits,
    homeruns: wholeGameStats.homeruns,
    strikeouts: wholeGameStats.strikeouts,
  };
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [scheduleGames, setScheduleGames] = useState<ScheduleGame[]>([]);
  const [simulations, setSimulations] = useState<DashboardMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [scheduleData, simData] = await Promise.all([
          fetchSchedule(),
          fetchDashboardMatches(),
        ]);
        setScheduleGames(scheduleData.games);
        setSimulations(simData);
        setError(null);
      } catch (err: any) {
        console.error("Error loading data:", err);
        console.error("Error message:", err.message);
        console.error("Error stack:", err.stack);
        setError(err.message || 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Merge schedule and simulations
  const games: Game[] = scheduleGames.map((scheduleGame, idx) => {
    const simMatch = findSimulationMatch(scheduleGame, simulations);
    return mergeToGame(scheduleGame, simMatch, idx);
  });

  const sorted = [...games].sort((a, b) => b.homeWinProb - a.homeWinProb);

  const totalLiveGames = scheduleGames.filter(g => g.isLive).length;
  const summaryItems = [
    { label: "Games this week", value: scheduleGames.length.toString() },
    { label: "Live games", value: totalLiveGames.toString() },
    { label: "Model accuracy", value: "~59%" },
    { label: "Games analyzed", value: "2,430" },
  ];

  // Always render the full layout – table structure remains visible
  return (
    <PageLayout activePath="/" backgroundImage="/images/bg-dashboard.jpg">
      <TopBar title="This week's predictions" />

      {/* Table */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 28px" }}>
        <div style={{ background: "rgba(42, 42, 44, 0.69)", borderRadius: 10, border: "0.5px solid rgba(255,255,255,0.07)", overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }} aria-label="Game predictions">
            <thead>
              <tr style={{ background: "rgba(255,255,255,0.02)", borderBottom: "0.5px solid rgba(255,255,255,0.07)" }}>
                {["Away", "Win Probability", "Date", "Time", "Home", "Win Probability", "Info"].map((h, i) => (
                  <th key={i} scope="col" style={{ padding: "12px 14px", fontSize: 16, fontWeight: 600, color: "rgb(255, 255, 255)", textAlign: i >= 6 ? "center" : "left", letterSpacing: ".1em", textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                // Loading placeholder row - keeps table height
                <tr>
                  <td colSpan={7} style={{ padding: "32px 14px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontSize: 16 }}>
                    Loading schedule...
                  </td>
                </tr>
              ) : error ? (
                // Error row with retry button
                <tr>
                  <td colSpan={7} style={{ padding: "32px 14px", textAlign: "center" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                      <span style={{ color: "#ff6b6b", fontSize: 16 }}>{error}</span>
                      <button
                        onClick={() => window.location.reload()}
                        style={{ padding: "6px 16px", background: "#89082d", border: "none", borderRadius: 4, color: "white", cursor: "pointer" }}
                      >
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "32px 14px", textAlign: "center", color: "rgba(255,255,255,0.5)", fontSize: 16 }}>
                    No games scheduled this week.
                  </td>
                </tr>
              ) : (
                sorted.map(game => {
                  const isExpanded = expandedId === game.id
                  return (
                    <React.Fragment key={game.id}>
                      <tr style={{ borderBottom: isExpanded ? "none" : "0.5px solid rgba(255,255,255,0.04)" }}>
                        <td style={{ padding: "14px 14px" }}><TeamCell name={game.awayTeam} /></td>
                        <td style={{ padding: "14px 14px" }}><ProbCell prob={game.awayWinProb} name={game.awayTeam} /></td>
                        <td style={{ padding: "14px 14px", fontSize: 14, fontWeight: 700, color: "#f0ede6" }}>{game.date}</td>
                        <td style={{ padding: "14px 14px", fontSize: 15, color: "rgba(255, 255, 255, 0.89)", fontWeight: 700 }}>{game.time}</td>
                        <td style={{ padding: "14px 14px" }}><TeamCell name={game.homeTeam} /></td>
                        <td style={{ padding: "14px 14px" }}><ProbCell prob={game.homeWinProb} name={game.homeTeam} /></td>
                        <td style={{ padding: "14px 14px", textAlign: "center" }}>
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : game.id)}
                            aria-label={isExpanded ? "Collapse predictions" : "Expand predictions"}
                            style={{ width: 30, height: 30, display: "inline-flex", alignItems: "center", justifyContent: "center", background: isExpanded ? "rgba(192,30,46,0.15)" : "rgba(255,255,255,0.04)", border: isExpanded ? "0.5px solid rgba(192,30,46,0.4)" : "2px solid rgba(255,255,255,0.1)", borderRadius: "50%", color: isExpanded ? "#f07080" : "rgba(255, 255, 255, 0.78)", fontSize: 14, fontFamily: "'DM Sans', sans-serif", cursor: "pointer" }}>
                            {isExpanded ? "▲" : "▼"}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={{ padding: 0 }}>
                            <Graph
                              game={game}
                              fullWidth={true}
                              isEmbedded={true}
                              backgroundColor="rgba(0,0,0,0.3)"
                            />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary bar */}
      <SummaryBar items={summaryItems} />
    </PageLayout>
  )
}
