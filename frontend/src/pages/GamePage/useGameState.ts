import { useState, useRef, useCallback } from 'react';
import type { GameStatus } from '../../types';
import { api } from '../../services/api';

export interface GamePlayer {
  id: number;
  player_name: string;
  seat_number: number;
  role?: string;
  personality?: string;
  is_alive: boolean;
}

export interface GameEvent {
  event_type: string;
  player_id: number;
  role?: string;
  content: string;
  phase: string;
  round_number: number;
}

export interface GameState {
  game_id: number;
  phase: string;
  round_number: number;
  winner: string | null;
  players: GamePlayer[];
  events: GameEvent[];
  current_speaker_id: number | null;
}

export interface LogEntry {
  id: number;
  type: 'system' | 'death' | 'action' | 'speech' | 'narrator';
  text: string;
  timestamp: number;
}

export interface ChatItem {
  id: string;
  text: string;
  speaker: string;
  type: 'speech' | 'thought' | 'system';
  typing?: boolean;
}

function mapGameStatus(raw: GameStatus): GameState {
  const players: GamePlayer[] = (raw.alive_players || []).map(p => ({
    id: p.id,
    player_name: p.name || '',
    seat_number: p.seat_number,
    role: p.role || '',
    personality: (p as any).personality || '',
    is_alive: p.is_alive,
  }));

  const events: GameEvent[] = (raw.events || []).map(e => ({
    event_type: e.event_type,
    player_id: e.player_id ?? 0,
    role: (e as any).role || '',
    content: e.public_content || '',
    phase: e.phase,
    round_number: e.round_number,
  }));

  return {
    game_id: raw.game_id,
    phase: raw.phase,
    round_number: raw.round_number,
    winner: raw.winner,
    players,
    events,
    current_speaker_id: (raw as any).current_speaker_id ?? null,
  };
}

function buildLogs(events: GameEvent[], players: GamePlayer[]): LogEntry[] {
  const seatMap = new Map<number, number>();
  players.forEach(p => seatMap.set(p.id, p.seat_number));

  return events.map((e, i) => {
    const seat = seatMap.get(e.player_id);
    const seatStr = seat ? `${seat}号` : '';
    let type: LogEntry['type'] = 'system';
    let text = '';

    if (e.event_type === 'system') {
      type = 'system';
      text = e.content;
    } else if (e.event_type === 'death') {
      type = 'death';
      text = e.content;
    } else if (e.event_type === 'action') {
      type = 'action';
      text = `${seatStr} ${e.content}`;
    } else if (e.event_type === 'speech') {
      type = 'speech';
      text = e.content;
    } else {
      type = 'system';
      text = e.content || e.event_type;
    }

    return { id: i, type, text, timestamp: Date.now() };
  });
}

export function useGameState(gameId: number) {
  const [status, setStatus] = useState<GameState | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [thinkingPlayers, setThinkingPlayers] = useState<Set<number>>(new Set());
  const statusRef = useRef<GameState | null>(null);
  const chatIdRef = useRef(0);
  const processedChatSet = useRef<Set<string>>(new Set());

  const fetchAndSetStatus = useCallback(async (gid: number) => {
    const res = await api.getGameStatus(gid);
    if (!res) return;
    const data = mapGameStatus(res);
    statusRef.current = data;
    setStatus(data);
    const newLogs = buildLogs(data.events || [], data.players || []);
    setLogs(newLogs);
  }, []);

  const addSystemChat = useCallback((text: string) => {
    chatIdRef.current++;
    const cid = `sys-${chatIdRef.current}`;
    const item: ChatItem = { id: cid, text, speaker: '', type: 'system', typing: false };
    setChatItems(prev => [...prev, item]);
  }, []);

  const addSpeechChat = useCallback((playerName: string, text: string) => {
    const speechKey = `${playerName}_${text}`;
    if (processedChatSet.current.has(speechKey)) return;
    processedChatSet.current.add(speechKey);
    chatIdRef.current++;
    const chatId = `speech-${chatIdRef.current}`;
    const newItem: ChatItem = { id: chatId, text, speaker: playerName, type: 'speech', typing: true };
    setChatItems(prev => [...prev, newItem]);
    const typingDuration = Math.min(text.length * 60, 4000);
    setTimeout(() => {
      setChatItems(prev => prev.map(c => c.id === chatId ? { ...c, typing: false } : c));
    }, typingDuration);
  }, []);

  const addThoughtChat = useCallback((playerName: string, thought: string, key: string) => {
    if (processedChatSet.current.has(key)) return;
    processedChatSet.current.add(key);
    chatIdRef.current++;
    const tId = `thought-${chatIdRef.current}`;
    const thoughtItem: ChatItem = { id: tId, text: thought, speaker: playerName, type: 'thought', typing: false };
    setChatItems(prev => [...prev, thoughtItem]);
  }, []);

  const setThinking = useCallback((pid: number) => {
    setThinkingPlayers(prev => new Set(prev).add(pid));
  }, []);

  const clearThinking = useCallback((pid: number) => {
    setThinkingPlayers(prev => {
      const next = new Set(prev);
      next.delete(pid);
      return next;
    });
  }, []);

  const clearAllThinking = useCallback(() => {
    setThinkingPlayers(new Set());
  }, []);

  return {
    status, setStatus, logs, setLogs, chatItems, setChatItems,
    thinkingPlayers, setThinkingPlayers, statusRef, chatIdRef, processedChatSet,
    fetchAndSetStatus, addSystemChat, addSpeechChat, addThoughtChat,
    setThinking, clearThinking, clearAllThinking,
  };
}

export { mapGameStatus, buildLogs };
