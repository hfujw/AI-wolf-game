import { RoomInfo, GameStatus, ReplayData, GameStats } from '../types';

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
  createRoom: () => request<RoomInfo>('/rooms', { method: 'POST' }),

  joinRoom: (roomId: number, playerName: string) =>
    request<{ room_id: number; room_code: string; message: string }>(
      `/rooms/${roomId}/join`,
      { method: 'POST', body: JSON.stringify({ player_name: playerName }) }
    ),

  startGame: (roomId: number) =>
    request<{ game_id: number; message: string }>(
      `/rooms/${roomId}/start`,
      { method: 'POST' }
    ),

  getRoomStatus: (roomId: number) =>
    request<{
      room_id: number;
      room_code: string;
      status: string;
      game_id?: number;
    }>(`/rooms/${roomId}/status`),

  getGameStatus: (gameId: number) =>
    request<GameStatus>(`/games/${gameId}/status`),

  getReplay: (gameId: number) =>
    request<ReplayData>(`/games/${gameId}/replay`),

  getGameEvents: (gameId: number) =>
    request<ReplayData>(`/games/${gameId}/events`),

  getGameStats: (gameId: number) =>
    request<GameStats>(`/games/${gameId}/stats`),
};
