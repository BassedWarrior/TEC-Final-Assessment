export const mockGames = [
  { id: 1, team1: "Dodgers",   team2: "Angels",    prob1: 62, prob2: 38, date: "24/05", time: "13:30 pm" },
  { id: 2, team1: "Yankees",   team2: "Red Sox",   prob1: 60, prob2: 40, date: "25/05", time: "12:00 pm" },
  { id: 3, team1: "Padres",    team2: "Mets",      prob1: 55, prob2: 45, date: "25/05", time: "20:00 pm" },
  { id: 4, team1: "Phillies",  team2: "White Sox", prob1: 52, prob2: 48, date: "28/05", time: "15:00 pm" },
  { id: 5, team1: "Blue Jays", team2: "Orioles",   prob1: 51, prob2: 49, date: "29/05", time: "20:00 pm" },
  { id: 6, team1: "Braves",    team2: "Pirates",   prob1: 51, prob2: 49, date: "30/05", time: "21:00 pm" },
]

export interface Game {
  id: number
  team1: string
  team2: string
  prob1: number
  prob2: number
  date: string
  time: string
}