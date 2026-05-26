import { Routes, Route } from 'react-router-dom'
import LobbyPage from './pages/LobbyPage'
import RoomPage from './pages/RoomPage'
import GamePage from './pages/GamePage'
import ReplayPage from './pages/ReplayPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/room/:roomCode" element={<RoomPage />} />
      <Route path="/game/:gameId" element={<GamePage />} />
      <Route path="/replay/:gameId" element={<ReplayPage />} />
    </Routes>
  )
}
