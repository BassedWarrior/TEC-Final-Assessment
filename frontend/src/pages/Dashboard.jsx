import { useNavigate } from 'react-router-dom'
import { mockGames } from '../data/mockData'

function colorClass(p) {
  if (p >= 60) return 'text-green-400'
  if (p >= 55) return 'text-yellow-400'
  return 'text-gray-300'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const sorted = [...mockGames].sort((a, b) => b.prob1 - a.prob1)

  return (
    <div className="p-8">
      <h1 className="text-xl font-medium text-white mb-6">This week's predictions</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-500 uppercase border-b border-white/10">
            <th className="pb-3 text-left">Team</th>
            <th className="pb-3 text-center">Probability</th>
            <th className="pb-3 text-left">Date</th>
            <th className="pb-3 text-left">Time</th>
            <th className="pb-3 text-left">Opponent</th>
            <th className="pb-3 text-center">Opp. prob.</th>
            <th className="pb-3 text-center">Simulate</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(game => (
            <tr key={game.id} className="border-b border-white/5 hover:bg-white/5">
              <td className="py-3 font-medium text-white">{game.team1}</td>
              <td className={`py-3 text-center font-medium ${colorClass(game.prob1)}`}>
                {game.prob1}%
              </td>
              <td className="py-3 text-gray-400">{game.date}</td>
              <td className="py-3 text-gray-400">{game.time}</td>
              <td className="py-3 text-gray-400">{game.team2}</td>
              <td className={`py-3 text-center ${colorClass(game.prob2)}`}>
                {game.prob2}%
              </td>
              <td className="py-3 text-center">
                <button
                  onClick={() => navigate(`/game/${game.id}`)}
                  className="px-3 py-1 text-xs border border-red-500/40 text-red-400 rounded hover:bg-red-500/20"
                >
                  ▶ Run
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}