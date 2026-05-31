import { Routes, Route } from 'react-router-dom'
import LobbyPage from './pages/LobbyPage'
import GamePage from './pages/GamePage'
import ReplayPage from './pages/ReplayPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/game/:gameId" element={<GamePage />} />
      <Route path="/replay/:gameId" element={<ReplayPage />} />
    </Routes>
  )
}
