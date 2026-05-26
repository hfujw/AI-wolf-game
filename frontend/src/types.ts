export interface Player {
  id: number;
  name: string;
  role: string;
  seat_number: number;
  is_alive: boolean;
  personality?: string;
}

export interface GameEvent {
  id: number;
  round_number: number;
  phase: string;
  player_id: number | null;
  event_type: string;
  public_content: string | null;
  private_content: string | null;
  internal_thought: string | null;
  reasoning_content: string | null;
  created_at?: string;
}

export interface GameStatus {
  game_id: number;
  phase: string;
  round_number: number;
  alive_players: Player[];
  winner: string | null;
  events: GameEvent[];
}

export interface ReplayData {
  game_id: number;
  players: ReplayPlayer[];
  events: ReplayEvent[];
}

export interface ReplayEvent {
  round_number: number;
  phase: string;
  player_id: number | null;
  player_name: string | null;
  event_type: string;
  public_content: string | null;
  private_content: string | null;
  internal_thought: string | null;
  reasoning_content: string | null;
}

export interface WSEvent {
  event_type: string;
  game_id: number;
  round_number: number;
  phase: string;
  player_id: number | null;
  data: {
    public_content: string | null;
    private_content: string | null;
    internal_thought: string | null;
    reasoning_content: string | null;
    player_name: string | null;
  };
  timestamp: string | null;
}

export interface RoomInfo {
  room_id: number;
  room_code: string;
}

export const ROLE_LABELS: Record<string, string> = {
  werewolf: '狼人',
  seer: '预言家',
  witch: '女巫',
  villager: '村民',
};

export const ROLE_COLORS: Record<string, string> = {
  werewolf: '#e74c3c',
  seer: '#f39c12',
  witch: '#9b59b6',
  villager: '#3498db',
};

export interface GameStats {
  player_stats: Record<number, PlayerStats>;
  vote_records: VoteRecord[];
  ability_uses: AbilityUse[];
}

export interface PlayerStats {
  role: string;
  score: number;
  votes_correct: number;
  votes_total: number;
  speeches: number;
  skill_uses: number;
  survived_rounds: number;
}

export interface VoteRecord {
  voter_id: number;
  target_id: number | null;
  target_role: string | null;
  voter_role: string;
  is_correct: boolean;
}

export interface AbilityUse {
  player_id: number;
  ability: string;
  target_id: number | null;
  success: boolean;
}

export interface ReplayPlayer {
  id: number;
  name: string;
  role: string;
  seat_number: number;
  is_alive: boolean;
}
