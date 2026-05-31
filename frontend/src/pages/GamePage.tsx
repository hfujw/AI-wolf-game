import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useGameState } from './GamePage/useGameState';
import { useWSEventHandler } from './GamePage/useWSEventHandler';
import { usePhaseTransition } from './GamePage/usePhaseTransition';
import { GameLayout } from './GamePage/GameLayout';
import { useWebSocket } from '../hooks/useWebSocket';
import { initAudio } from '../utils/sound';

export default function GamePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const gid = Number(gameId);

  const [isGodView, setIsGodView] = useState(false);
  const [mvpVisible, setMvpVisible] = useState(false);
  const [gameFinished, setGameFinished] = useState(false);

  const state = useGameState(gid);

  const handleWSEvent = useWSEventHandler(
    gid, state, isGodView, gameFinished, setGameFinished, setMvpVisible,
  );

  usePhaseTransition(
    state.status?.phase, state.status?.winner, gameFinished, setGameFinished, setMvpVisible,
  );

  const { connected } = useWebSocket(gid, 'god', handleWSEvent);

  useEffect(() => { initAudio(); }, []);

  useEffect(() => {
    state.fetchAndSetStatus(gid);
    const poll = setInterval(() => state.fetchAndSetStatus(gid), 3000);
    return () => clearInterval(poll);
  }, [gid]);

  if (!state.status) {
    return (
      <div className="lobby-container">
        <h1 className="lobby-title">Loading...</h1>
      </div>
    );
  }

  return (
    <GameLayout
      status={state.status}
      logs={state.logs}
      chatItems={state.chatItems}
      thinkingPlayers={state.thinkingPlayers}
      isGodView={isGodView}
      setIsGodView={setIsGodView}
      mvpVisible={mvpVisible}
      setMvpVisible={setMvpVisible}
      onNavigateHome={() => navigate('/')}
    />
  );
}
