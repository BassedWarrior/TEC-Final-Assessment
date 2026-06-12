export interface InningScore {
  inning: number
  team1: number
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