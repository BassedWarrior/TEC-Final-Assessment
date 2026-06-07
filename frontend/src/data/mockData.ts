export interface Game {
  id: number
  team1: string
  team2: string
  prob1: number
  prob2: number
  date: string
  time: string
}

export const teamMeta: Record<string, { abbr: string; color: string }> = {
  "Dodgers":   { abbr: "lad", color: "#005A9C" },
  "Angels":    { abbr: "laa", color: "#BA0021" },
  "Yankees":   { abbr: "nyy", color: "#003087" },
  "Red Sox":   { abbr: "bos", color: "#BD3039" },
  "Padres":    { abbr: "sd",  color: "#2F241D" },
  "Mets":      { abbr: "nym", color: "#002D72" },
  "Phillies":  { abbr: "phi", color: "#E81828" },
  "White Sox": { abbr: "chw", color: "#888" },
  "Blue Jays": { abbr: "tor", color: "#134A8E" },
  "Orioles":   { abbr: "bal", color: "#DF4601" },
  "Braves":    { abbr: "atl", color: "#CE1141" },
  "Pirates":   { abbr: "pit", color: "#FDB827" },
}
export const mockGames: Game[] = [
  { id: 1, team1: "Dodgers",   team2: "Angels",    prob1: 62, prob2: 38, date: "May 24", time: "1:30 PM" },
  { id: 2, team1: "Yankees",   team2: "Red Sox",   prob1: 60, prob2: 40, date: "May 25", time: "12:00 PM" },
  { id: 3, team1: "Padres",    team2: "Mets",      prob1: 55, prob2: 45, date: "May 25", time: "8:00 PM" },
  { id: 4, team1: "Phillies",  team2: "White Sox", prob1: 52, prob2: 48, date: "May 28", time: "3:00 PM" },
  { id: 5, team1: "Blue Jays", team2: "Orioles",   prob1: 51, prob2: 49, date: "May 29", time: "8:00 PM" },
  { id: 6, team1: "Braves",    team2: "Pirates",   prob1: 51, prob2: 49, date: "May 30", time: "9:00 PM" },
]