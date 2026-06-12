const API_BASE_URL = import.meta.env.VITE_API_URL;

export interface InningAverages {
  inning_number: number;
  avg_home_runs: number;
  avg_away_runs: number;
  avg_home_hits: number;
  avg_away_hits: number;
  avg_home_hr: number;
  avg_away_hr: number;
  avg_home_strikeouts: number;
  avg_away_strikeouts: number;
}

export interface DashboardMatch {
  match_id: number;
  created_at: string | null;
  home_team: string;
  away_team: string;
  n_sims: number;
  home_wp: number;      // win probability as a decimal (0.00 – 1.00)
  away_wp: number;
  whole_game: {
    avg_home_runs: number;
    avg_away_runs: number;
    avg_home_hits: number;
    avg_away_hits: number;
    avg_home_hr: number;
    avg_away_hr: number;
    avg_home_strikeouts: number;
    avg_away_strikeouts: number;
  };
  innings: InningAverages[];
  match_date: string | null;
  match_time: string | null;
}

export async function fetchDashboardMatches(): Promise<DashboardMatch[]> {
  const response = await fetch(`${API_BASE_URL}/simulations/dashboard`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard matches: ${response.statusText}`);
  }

  return response.json();
}