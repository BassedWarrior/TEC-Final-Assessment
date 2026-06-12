const API_BASE_URL = import.meta.env.VITE_API_URL;

export interface PlayerStats {
  id: number;
  name: string;
  hand: string;
  pa_count: number;
  avg: number;
  obp: number;
  slg: number;
  iso: number;
  k_rate: number;
  bb_rate: number;
  hr_rate: number;
  is_rookie: string;
  is_batter: boolean;
}

export async function fetchPlayerStats(): Promise<PlayerStats[]> {
  const url = `${API_BASE_URL}/players/player-stats`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  const data = await response.json();  
  return data;
}