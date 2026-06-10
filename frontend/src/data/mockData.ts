export interface InningScore {
  inning: number
  team1: number      // runs
  team2: number
  hits1: number
  hits2: number
  hrs1: number
  hrs2: number
  ks1: number
  ks2: number
}

export interface Game {
  id: number
  team1: string
  team2: string
  prob1: number
  prob2: number
  date: string
  time: string
  innings: InningScore[]
  hits: [number, number]
  homeruns: [number, number]
  strikeouts: [number, number]
}

export const teamMeta: Record<string, { abbr: string; color: string }> = {
  "Dodgers":   { abbr: "lad", color: "#145bdb" },
  "Angels":    { abbr: "laa", color: "#BA0021" },
  "Yankees":   { abbr: "nyy", color: "#145bdb" },
  "Red Sox":   { abbr: "bos", color: "#BD3039" },
  "Padres":    { abbr: "sd",  color: "#888" },
  "Mets":      { abbr: "nym", color: "#145bdb" },
  "Phillies":  { abbr: "phi", color: "#E81828" },
  "White Sox": { abbr: "chw", color: "#888" },
  "Blue Jays": { abbr: "tor", color: "#145bdb" },
  "Orioles":   { abbr: "bal", color: "#DF4601" },
  "Braves":    { abbr: "atl", color: "#CE1141" },
  "Pirates":   { abbr: "pit", color: "#FDB827" },
}

export const mockGames: Game[] = [
  {
  id: 1, team1: "Dodgers", team2: "Angels", prob1: 62, prob2: 38, date: "May 24", time: "1:30 PM",
  innings: [
    { inning: 1, team1: 2, team2: 0, hits1: 3, hits2: 1, hrs1: 1, hrs2: 0, ks1: 1, ks2: 2 },
    { inning: 2, team1: 0, team2: 1, hits1: 1, hits2: 2, hrs1: 0, hrs2: 1, ks1: 2, ks2: 1 },
    { inning: 3, team1: 1, team2: 0, hits1: 2, hits2: 0, hrs1: 0, hrs2: 0, ks1: 0, ks2: 1 },
    { inning: 4, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
    { inning: 5, team1: 2, team2: 1, hits1: 2, hits2: 1, hrs1: 1, hrs2: 0, ks1: 1, ks2: 2 },
    { inning: 6, team1: 0, team2: 0, hits1: 0, hits2: 0, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
    { inning: 7, team1: 1, team2: 0, hits1: 1, hits2: 1, hrs1: 0, hrs2: 0, ks1: 0, ks2: 1 },
    { inning: 8, team1: 0, team2: 1, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
    { inning: 9, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 0, ks2: 1 },
    ],
    hits: [9, 6], homeruns: [2, 1], strikeouts: [7, 9],
    },
    {
    id: 2, team1: "Yankees", team2: "Pirates", prob1: 57, prob2: 43, date: "May 25", time: "7:05 PM",
    innings: [
      { inning: 1, team1: 1, team2: 0, hits1: 2, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 2 },
      { inning: 2, team1: 0, team2: 1, hits1: 1, hits2: 2, hrs1: 0, hrs2: 1, ks1: 2, ks2: 1 },
      { inning: 3, team1: 2, team2: 0, hits1: 3, hits2: 0, hrs1: 1, hrs2: 0, ks1: 0, ks2: 2 },
      { inning: 4, team1: 0, team2: 0, hits1: 1, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
      { inning: 5, team1: 1, team2: 1, hits1: 2, hits2: 2, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
      { inning: 6, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 2, ks2: 0 },
      { inning: 7, team1: 0, team2: 1, hits1: 1, hits2: 2, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
      { inning: 8, team1: 1, team2: 0, hits1: 2, hits2: 0, hrs1: 1, hrs2: 0, ks1: 0, ks2: 2 },
      { inning: 9, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
    ],
      hits: [12, 10], homeruns: [2, 1], strikeouts: [9, 10],
    },

    {
    id: 3, team1: "Blue Jays", team2: "Orioles", prob1: 54, prob2: 46, date: "May 26", time: "6:40 PM",
    innings: [
      { inning: 1, team1: 0, team2: 1, hits1: 1, hits2: 2, hrs1: 0, hrs2: 0, ks1: 2, ks2: 1 },
      { inning: 2, team1: 1, team2: 0, hits1: 2, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 2 },
      { inning: 3, team1: 0, team2: 0, hits1: 1, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
      { inning: 4, team1: 2, team2: 0, hits1: 3, hits2: 0, hrs1: 1, hrs2: 0, ks1: 0, ks2: 2 },
      { inning: 5, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
      { inning: 6, team1: 1, team2: 1, hits1: 2, hits2: 2, hrs1: 0, hrs2: 1, ks1: 1, ks2: 1 },
      { inning: 7, team1: 0, team2: 0, hits1: 1, hits2: 0, hrs1: 0, hrs2: 0, ks1: 1, ks2: 2 },
      { inning: 8, team1: 1, team2: 0, hits1: 2, hits2: 1, hrs1: 1, hrs2: 0, ks1: 0, ks2: 1 },
      { inning: 9, team1: 0, team2: 1, hits1: 0, hits2: 2, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
      ],
      hits: [12, 10], homeruns: [2, 1], strikeouts: [8, 10],
    },

  {
    id: 4, team1: "Braves", team2: "Padres", prob1: 52, prob2: 48, date: "May 27", time: "7:20 PM",
    innings: [
      { inning: 1, team1: 1, team2: 0, hits1: 2, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 2 },
      { inning: 2, team1: 0, team2: 2, hits1: 1, hits2: 3, hrs1: 0, hrs2: 1, ks1: 2, ks2: 0 },
      { inning: 3, team1: 2, team2: 0, hits1: 3, hits2: 0, hrs1: 1, hrs2: 0, ks1: 0, ks2: 2 },
      { inning: 4, team1: 0, team2: 0, hits1: 0, hits2: 1, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
      { inning: 5, team1: 1, team2: 1, hits1: 2, hits2: 2, hrs1: 0, hrs2: 0, ks1: 1, ks2: 1 },
      { inning: 6, team1: 1, team2: 0, hits1: 2, hits2: 0, hrs1: 0, hrs2: 0, ks1: 0, ks2: 2 },
      { inning: 7, team1: 0, team2: 0, hits1: 1, hits2: 1, hrs1: 0, hrs2: 0, ks1: 2, ks2: 1 },
      { inning: 8, team1: 1, team2: 0, hits1: 1, hits2: 0, hrs1: 1, hrs2: 0, ks1: 0, ks2: 1 },
      { inning: 9, team1: 0, team2: 1, hits1: 0, hits2: 2, hrs1: 0, hrs2: 0, ks1: 1, ks2: 0 },
      ],
      hits: [12, 10], homeruns: [2, 1], strikeouts: [8, 10],
    },
]