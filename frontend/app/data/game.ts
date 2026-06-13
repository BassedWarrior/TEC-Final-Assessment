export interface InningScore {
  inning: number
  homeRuns: number
  awayRuns: number
  homeHits: number
  awayHits: number
  homeHRs: number
  awayHRs: number
  homeStrikeouts: number
  awayStrikeouts: number
}

export interface Game {
  id: number
  homeTeam: string
  awayTeam: string
  homeWinProb: number
  awayWinProb: number
  date: string
  time: string
  isLive: boolean
  isFinal: boolean
  innings: InningScore[]
  winner: null
  status: string
  hits: [number, number]
  homeruns: [number, number]
  strikeouts: [number, number]
}
