import type { Game, InningScore } from "../data/game.ts";

const API_URL = import.meta.env.VITE_API_URL;

// ─── Request / Response shapes (mirror backend simulations.py) ────────────────

export interface SimulateRequest {
  home_batter_ids: number[]; // exactly 9
  away_batter_ids: number[]; // exactly 9
  home_pitcher_id: number;
  away_pitcher_id: number;
  home_bullpen_ids?: number[];
  away_bullpen_ids?: number[];
  reliever_entry_inning?: number;
  n_sims?: number;
  seed?: number;
  home_team?: string;
  away_team?: string;
}

interface WholeGameAverages {
  avg_home_runs: number;
  avg_away_runs: number;
  avg_home_hits: number;
  avg_away_hits: number;
  avg_home_hr: number;
  avg_away_hr: number;
  avg_home_strikeouts: number;
  avg_away_strikeouts: number;
}

interface InningAverages extends WholeGameAverages {
  inning_number: number;
}

export interface MatchResponse {
  match_id: number;
  created_at: string | null;
  home_team: string;
  away_team: string;
  n_sims: number;
  home_wp: number; // 0..1
  away_wp: number; // 0..1
  home_batter_ids: number[]; // MLBAM ids, batting order
  away_batter_ids: number[];
  home_pitcher_ids: number[]; // starter first, then bullpen
  away_pitcher_ids: number[];
  whole_game: WholeGameAverages;
  innings: InningAverages[];
}

// ─── API call ─────────────────────────────────────────────────────────────────

export async function runSimulation(body: SimulateRequest): Promise<MatchResponse> {
  const res = await fetch(`${API_URL}/simulations/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send auth cookie — endpoint requires a logged-in user
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    // Surface the backend detail (e.g. 422 missing player ids, 503 model down)
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {
      /* response had no JSON body */
    }
    throw new Error(`Simulation failed (${res.status}): ${detail}`);
  }

  return res.json();
}

// Fetch the logged-in user's saved simulation history (most-recent matches they ran).
export async function fetchHistory(): Promise<MatchResponse[]> {
  const res = await fetch(`${API_URL}/simulations/history`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include", // history is scoped to the authenticated user
  });

  if (!res.ok) {
    throw new Error(`Failed to load history (${res.status}): ${res.statusText}`);
  }

  return res.json();
}

// ─── Response → Graph adapter ─────────────────────────────────────────────────
//
// The backend returns *averages* over n_sims. Per the aggregator:
//   - innings[].avg_*_runs are CUMULATIVE (running scoreline)
//   - innings[].avg_*_hits / _hr / _strikeouts are PER-INNING
// The Graph component sums per-inning values to build cumulative lines, so we
// convert the cumulative runs back into per-inning deltas and leave the rest
// as-is. homeTeam = away, awayTeam = home (matches the sandbox layout / colours).

export function matchToGame(
  match: MatchResponse,
  awayName = "Away",
  homeName = "Home"
): Game {
  const ordered = [...match.innings].sort((a, b) => a.inning_number - b.inning_number);

  let prevAwayRuns = 0;
  let prevHomeRuns = 0;
  const innings: InningScore[] = ordered.map((inn) => {
    const awayRuns = inn.avg_away_runs - prevAwayRuns; // per-inning away runs
    const homeRuns = inn.avg_home_runs - prevHomeRuns; // per-inning home runs
    prevAwayRuns = inn.avg_away_runs;
    prevHomeRuns = inn.avg_home_runs;

    return {
      inning: inn.inning_number,
      homeRuns,
      awayRuns,
      awayHits: inn.avg_away_hits,
      homeHits: inn.avg_home_hits,
      awayHRs: inn.avg_away_hr,
      homeHRs: inn.avg_home_hr,
      awayStrikeouts: inn.avg_away_strikeouts,
      homeStrikeouts: inn.avg_home_strikeouts,
    };
  });

  const wg = match.whole_game;

  return {
    id: match.match_id,
    awayTeam: awayName,
    homeTeam: homeName,
    awayWinProb: Math.round(match.away_wp * 100),
    homeWinProb: Math.round(match.home_wp * 100),
    date: match.created_at ? new Date(match.created_at).toLocaleDateString() : "",
    time: match.created_at ? new Date(match.created_at).toLocaleTimeString() : "",
    innings,
    hits: [wg.avg_away_hits, wg.avg_home_hits],
    homeruns: [wg.avg_away_hr, wg.avg_home_hr],
    strikeouts: [wg.avg_away_strikeouts, wg.avg_home_strikeouts],
  };
}
