export interface Batter {
  id: number
  mlbamId: number
  name: string
  team: string
  stand: "R" | "L" | "S"
  pa: number
  avg: number
  obp: number
  slg: number
  iso: number
  k_rate: number
  bb_rate: number
  hr_rate: number
  is_rookie: boolean
  teamColor: string
  teamAbbr: string
}

export interface Pitcher {
  id: number
  mlbamId: number
  name: string
  team: string
  throws: "R" | "L"
  pa: number
  avg: number
  obp: number
  slg: number
  iso: number
  k_rate: number
  bb_rate: number
  hr_rate: number
  is_new: boolean
  teamColor: string
  teamAbbr: string
}

export const MOCK_BATTERS: Batter[] = [
  { id: 1, mlbamId: 518692, name: "Freddie Freeman", team: "Dodgers",   stand: "L", pa: 320, avg: .298, obp: .389, slg: .521, iso: .223, k_rate: 18.2, bb_rate: 12.4, hr_rate: 5.8,  is_rookie: false, teamColor: "#005A9C", teamAbbr: "LAD" },
  { id: 2, mlbamId: 592450, name: "Aaron Judge",     team: "Yankees",   stand: "R", pa: 340, avg: .276, obp: .391, slg: .623, iso: .347, k_rate: 28.5, bb_rate: 14.2, hr_rate: 11.2, is_rookie: false, teamColor: "#003087", teamAbbr: "NYY" },
  { id: 3, mlbamId: 596019, name: "Xander Bogaerts", team: "Padres",    stand: "R", pa: 290, avg: .262, obp: .328, slg: .412, iso: .150, k_rate: 22.1, bb_rate: 8.3,  hr_rate: 3.4,  is_rookie: false, teamColor: "#2F241D", teamAbbr: "SD"  },
  { id: 4, mlbamId: 663728, name: "Kyle Tucker",     team: "Phillies",  stand: "L", pa: 180, avg: .310, obp: .401, slg: .558, iso: .248, k_rate: 19.8, bb_rate: 13.1, hr_rate: 6.1,  is_rookie: false, teamColor: "#E81828", teamAbbr: "PHI" },
  { id: 5, mlbamId: 681584, name: "Colt Keith",      team: "Dodgers",   stand: "L", pa: 95,  avg: .241, obp: .302, slg: .378, iso: .137, k_rate: 26.3, bb_rate: 7.2,  hr_rate: 2.1,  is_rookie: true,  teamColor: "#005A9C", teamAbbr: "LAD" },
  { id: 6, mlbamId: 685473, name: "Jackson Chourio", team: "Yankees",   stand: "R", pa: 88,  avg: .255, obp: .299, slg: .421, iso: .166, k_rate: 24.6, bb_rate: 5.8,  hr_rate: 3.4,  is_rookie: true,  teamColor: "#003087", teamAbbr: "NYY" },
  { id: 7, mlbamId: 547180, name: "Bryce Harper",    team: "Phillies",  stand: "L", pa: 310, avg: .295, obp: .384, slg: .543, iso: .248, k_rate: 20.1, bb_rate: 12.8, hr_rate: 6.8,  is_rookie: false, teamColor: "#E81828", teamAbbr: "PHI" },
  { id: 8, mlbamId: 666182, name: "Bo Bichette",     team: "Blue Jays", stand: "R", pa: 275, avg: .270, obp: .318, slg: .430, iso: .160, k_rate: 21.8, bb_rate: 6.9,  hr_rate: 4.1,  is_rookie: false, teamColor: "#134A8E", teamAbbr: "TOR" },
]

export const MOCK_PITCHERS: Pitcher[] = [
  { id: 1, mlbamId: 694973, name: "Paul Skenes",     team: "Pirates",   throws: "R", pa: 410, avg: .198, obp: .261, slg: .312, iso: .114, k_rate: 34.2, bb_rate: 6.1, hr_rate: 2.8, is_new: true,  teamColor: "#FDB827", teamAbbr: "PIT" },
  { id: 2, mlbamId: 554430, name: "Zack Wheeler",    team: "Phillies",  throws: "R", pa: 520, avg: .221, obp: .280, slg: .349, iso: .128, k_rate: 28.9, bb_rate: 5.4, hr_rate: 3.1, is_new: false, teamColor: "#E81828", teamAbbr: "PHI" },
  { id: 3, mlbamId: 657277, name: "Logan Webb",      team: "Padres",    throws: "R", pa: 490, avg: .238, obp: .291, slg: .371, iso: .133, k_rate: 22.4, bb_rate: 6.8, hr_rate: 3.6, is_new: false, teamColor: "#2F241D", teamAbbr: "SD"  },
  { id: 4, mlbamId: 682243, name: "Garrett Crochet", team: "Red Sox",   throws: "L", pa: 380, avg: .210, obp: .272, slg: .331, iso: .121, k_rate: 30.1, bb_rate: 7.2, hr_rate: 2.4, is_new: false, teamColor: "#BD3039", teamAbbr: "BOS" },
  { id: 5, mlbamId: 808982, name: "Roki Sasaki",     team: "Dodgers",   throws: "R", pa: 120, avg: .229, obp: .285, slg: .358, iso: .129, k_rate: 29.8, bb_rate: 8.1, hr_rate: 3.0, is_new: true,  teamColor: "#005A9C", teamAbbr: "LAD" },
  { id: 6, mlbamId: 669923, name: "Shane Baz",       team: "Blue Jays", throws: "R", pa: 95,  avg: .244, obp: .301, slg: .388, iso: .144, k_rate: 25.3, bb_rate: 7.4, hr_rate: 3.8, is_new: true,  teamColor: "#134A8E", teamAbbr: "TOR" },
]

export const TEAMS = ["Dodgers", "Yankees", "Red Sox", "Padres", "Phillies", "Blue Jays", "Pirates"]