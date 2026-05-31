import { GameStatus, ReplayData, GameStats } from '../types';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

export const api = {
  startGame: () =>
    request<{ game_id: number }>('/games/start', { method: 'POST' }),

  getGameStatus: (gameId: number) =>
    request<GameStatus>(`/games/${gameId}/status`),

  getReplay: (gameId: number) =>
    request<ReplayData>(`/games/${gameId}/replay`),

  getGameEvents: (gameId: number) =>
    request<ReplayData>(`/games/${gameId}/events`),

  getGameStats: (gameId: number) =>
    request<GameStats>(`/games/${gameId}/stats`),
};
