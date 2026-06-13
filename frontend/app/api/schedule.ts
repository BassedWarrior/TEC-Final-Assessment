const API_URL = import.meta.env.VITE_API_URL;
console.log("API URL: ", API_URL)

export interface ScheduleGame {
  gameDate: string;
  gameTime: string;
  isLive: boolean;
  isFinal: boolean;
  gameState: string;
  awayTeamId: number;
  awayTeamName: string;
  homeTeamId: number;
  homeTeamName: string;
}

export interface ScheduleResponse {
  totalGames: number;
  totalGamesInProgress: number;
  games: ScheduleGame[];
}

export async function fetchSchedule(startDate?: string, endDate?: string): Promise<ScheduleResponse> {
  // Default to current week if no dates provided
  const today = new Date();
  const defaultEndDate = new Date(today);
  defaultEndDate.setDate(today.getDate() + 6);
  
  const url = `${API_URL}/schedule`;
  
  const response = await fetch(`${API_URL}/schedule`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // Include cookies if your backend uses them
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch schedule: ${response.statusText}`);
  }
  return response.json();
}