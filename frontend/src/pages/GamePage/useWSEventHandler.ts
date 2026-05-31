import { useCallback } from 'react';
import type { WSEvent } from '../../types';
import { api } from '../../services/api';
import {
  playNightSound, playDawnSound, playVoteTicking,
  playVictorySound, playDefeatSound, playVoteResultSound, playKnifeSound,
} from '../../utils/sound';
import { mapGameStatus, buildLogs } from './useGameState';

export function useWSEventHandler(
  gameId: number,
  gameState: ReturnType<typeof import('./useGameState').useGameState>,
  isGodView: boolean,
  gameFinished: boolean,
  setGameFinished: (v: boolean) => void,
  setMvpVisible: (v: boolean) => void,
) {
  const handleWSEvent = useCallback((event: WSEvent) => {
    const currentStatus = gameState.statusRef.current;
    if (!currentStatus) return;

    if (event.event_type === 'agent_thinking') {
      const pid = event.player_id;
      if (pid) gameState.setThinking(pid);
      return;
    }

    if (event.event_type === 'phase_change') {
      const prevPhase = currentStatus.phase;
      api.getGameStatus(gameId).then((res) => {
        if (res) {
          const data = mapGameStatus(res);
          gameState.statusRef.current = data;
          gameState.setStatus(data);
          const newLogs = buildLogs(data.events || [], data.players || []);
          gameState.setLogs(newLogs);

          const oldWasNight = prevPhase?.startsWith('night');
          const newIsDay = data.phase?.startsWith('day');
          if (oldWasNight && newIsDay) playDawnSound();
          const newIsNight = data.phase?.startsWith('night');
          if (newIsNight && !prevPhase?.startsWith('night')) playNightSound();
          if (data.phase === 'day_vote') playVoteTicking();

          const isNowFinished = data.phase === 'finished' || data.phase === 'game_over' || !!data.winner;
          if (isNowFinished && !gameFinished) {
            setGameFinished(true);
            if (data.winner === 'werewolves') playVictorySound();
            else playDefeatSound();
            setTimeout(() => setMvpVisible(true), 2000);
          }
          gameState.clearAllThinking();
        }
      }).catch(() => {});
      return;
    }

    const pid = event.player_id;
    if (pid) gameState.clearThinking(pid);

    if (event.event_type === 'speech') {
      const speechKey = `${event.player_id}_${event.round_number}_${event.data?.public_content || ''}`;
      const playerName = event.data?.player_name || `${event.player_id}号`;
      let text = event.data?.public_content || '';
      const prefixRegex = new RegExp(`^\\d+号\\s*${playerName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*[：:]\\s*`);
      text = text.replace(prefixRegex, '');
      gameState.addSpeechChat(playerName, text);
    }

    if (event.event_type === 'speech' && isGodView) {
      const thought = event.data?.internal_thought || event.data?.reasoning_content;
      if (thought) {
        const thoughtKey = `thought_${event.player_id}_${event.round_number}`;
        gameState.addThoughtChat(event.data?.player_name || `${event.player_id}号`, thought, thoughtKey);
      }
    }

    if (isGodView && ['action', 'seer_check', 'witch_use_antidote', 'witch_use_poison', 'witch_action', 'hunter_shoot'].includes(event.event_type || '')) {
      const thought = event.data?.internal_thought || event.data?.reasoning_content;
      if (thought) {
        const thoughtKey = `night_thought_${event.player_id}_${event.round_number}_${event.phase}`;
        gameState.addThoughtChat(event.data?.player_name || `${event.player_id}号`, thought, thoughtKey);
      }
    }

    if (event.event_type === 'action' && event.phase === 'night_werewolf') playKnifeSound();
    if (event.event_type === 'death' && event.phase === 'day_announce') playVoteResultSound();

    const newEvent = {
      event_type: event.event_type,
      player_id: event.player_id ?? 0,
      role: '',
      content: event.data?.public_content || event.data?.private_content || '',
      phase: event.phase || currentStatus.phase,
      round_number: event.round_number || currentStatus.round_number,
    };

    const updatedEvents = [...currentStatus.events, newEvent];
    const updatedStatus = { ...currentStatus, events: updatedEvents, phase: event.phase || currentStatus.phase };
    gameState.statusRef.current = updatedStatus;
    gameState.setStatus(updatedStatus);
    const newLogs = buildLogs(updatedEvents, currentStatus.players);
    gameState.setLogs(newLogs);
  }, [gameId, gameFinished, isGodView, gameState, setGameFinished, setMvpVisible]);

  return handleWSEvent;
}
