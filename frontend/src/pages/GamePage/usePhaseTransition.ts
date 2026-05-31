import { useRef, useEffect } from 'react';
import {
  playNightSound, playDawnSound, playVoteTicking,
  playVictorySound, playDefeatSound,
} from '../../utils/sound';

export function usePhaseTransition(
  phase: string | undefined,
  winner: string | null | undefined,
  gameFinished: boolean,
  setGameFinished: (v: boolean) => void,
  setMvpVisible: (v: boolean) => void,
) {
  const prevPhaseRef = useRef<string>('');
  const isFirstRef = useRef(true);

  useEffect(() => {
    if (!phase) return;
    if (isFirstRef.current) {
      isFirstRef.current = false;
      prevPhaseRef.current = phase;
      return;
    }
    const prev = prevPhaseRef.current;
    if (phase === prev) return;

    const oldWasNight = prev?.startsWith('night');
    const newIsDay = phase?.startsWith('day');
    if (oldWasNight && newIsDay) playDawnSound();

    const newIsNight = phase?.startsWith('night');
    if (newIsNight && !prev?.startsWith('night')) playNightSound();

    if (phase === 'day_vote') playVoteTicking();

    const isNowFinished = phase === 'finished' || phase === 'game_over' || !!winner;
    if (isNowFinished && !gameFinished) {
      setGameFinished(true);
      if (winner === 'werewolves') playVictorySound();
      else playDefeatSound();
      setTimeout(() => setMvpVisible(true), 2000);
    }

    prevPhaseRef.current = phase;
  }, [phase, winner, gameFinished, setGameFinished, setMvpVisible]);

  return { prevPhase: prevPhaseRef.current };
}
