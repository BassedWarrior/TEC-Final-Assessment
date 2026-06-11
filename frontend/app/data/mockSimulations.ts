import type { Batter, Pitcher } from "./mockPlayers"
import type { Game } from "./mockData"
import { mockGames } from "./mockData"
import { MOCK_BATTERS, MOCK_PITCHERS } from "./mockPlayers"

export interface SimulationResult {
  id: number
  date: string
  time: string
  game: Game           // ← link to mockData game for the graph
  home: {
    batters: Batter[]
    pitchers: Pitcher[]
    hits: number
    strikeouts: number
    homeruns: number
    score: number
  }
  away: {
    batters: Batter[]
    pitchers: Pitcher[]
    hits: number
    strikeouts: number
    homeruns: number
    score: number
  }
}

export const MOCK_HISTORY: SimulationResult[] = [
  {
    id: 1,
    date: "May 28, 2025",
    time: "3:42 PM",
    game: mockGames[0],   // Dodgers vs Angels
    home: {
      batters: [MOCK_BATTERS[0], MOCK_BATTERS[3], MOCK_BATTERS[6]],
      pitchers: [MOCK_PITCHERS[1]],
      hits: 9, strikeouts: 7, homeruns: 2, score: 5,
    },
    away: {
      batters: [MOCK_BATTERS[1], MOCK_BATTERS[2], MOCK_BATTERS[5]],
      pitchers: [MOCK_PITCHERS[0]],
      hits: 6, strikeouts: 11, homeruns: 1, score: 3,
    },
  },
  {
    id: 2,
    date: "May 29, 2025",
    time: "11:15 AM",
    game: mockGames[1],   // Yankees vs Red Sox
    home: {
      batters: [MOCK_BATTERS[4], MOCK_BATTERS[7]],
      pitchers: [MOCK_PITCHERS[2], MOCK_PITCHERS[3]],
      hits: 5, strikeouts: 9, homeruns: 0, score: 2,
    },
    away: {
      batters: [MOCK_BATTERS[0], MOCK_BATTERS[6]],
      pitchers: [MOCK_PITCHERS[4]],
      hits: 11, strikeouts: 6, homeruns: 3, score: 7,
    },
  },
  {
    id: 3,
    date: "May 30, 2025",
    time: "6:08 PM",
    game: mockGames[2],   // Padres vs Mets
    home: {
      batters: [MOCK_BATTERS[1], MOCK_BATTERS[3], MOCK_BATTERS[5], MOCK_BATTERS[7]],
      pitchers: [MOCK_PITCHERS[5]],
      hits: 8, strikeouts: 8, homeruns: 1, score: 4,
    },
    away: {
      batters: [MOCK_BATTERS[2], MOCK_BATTERS[4]],
      pitchers: [MOCK_PITCHERS[0], MOCK_PITCHERS[2]],
      hits: 8, strikeouts: 10, homeruns: 1, score: 4,
    },
  },
]
