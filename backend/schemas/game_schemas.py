from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AlivePlayerInfo(BaseModel):
    id: int
    name: str
    seat_number: int
    is_alive: bool
    role: Optional[str] = None


class VisibleEvent(BaseModel):
    id: int
    round_number: int
    phase: str
    player_id: Optional[int] = None
    event_type: str
    public_content: Optional[str] = None
    private_content: Optional[str] = None
    reasoning_content: Optional[str] = None


class AgentContext(BaseModel):
    phase: str
    round_number: int
    player_id: int
    role: str
    personality: str
    alive_players: list[AlivePlayerInfo]
    valid_targets: list[int]
    visible_events: list[VisibleEvent]
    private_info: dict = {}
    werewolf_partners: list[int] = []
    seer_checks: list[dict] = []
    witch_info: dict = {}
    conversation_history: str = ""


class AgentDecision(BaseModel):
    action: str
    target_id: Optional[str] = None
    speech: Optional[str] = None
    use_antidote: Optional[bool] = None
    use_poison: Optional[bool] = None
    poison_target: Optional[str] = None
    internal_thought: str = ""
    reasoning: Optional[str] = None


class RoomCreateResponse(BaseModel):
    room_id: int
    room_code: str


class JoinRoomRequest(BaseModel):
    player_name: str


class GameStatusResponse(BaseModel):
    game_id: int
    phase: str
    round_number: int
    alive_players: list[AlivePlayerInfo]
    winner: Optional[str] = None
    events: list[VisibleEvent] = []


class ReplayEvent(BaseModel):
    round_number: int
    phase: str
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    event_type: str
    public_content: Optional[str] = None
    private_content: Optional[str] = None
    internal_thought: Optional[str] = None
    reasoning_content: Optional[str] = None


class ReplayResponse(BaseModel):
    game_id: int
    players: list[dict]
    events: list[ReplayEvent]


class EventsResponse(BaseModel):
    game_id: int
    players: list[dict]
    events: list[ReplayEvent]


class PlayerStatItem(BaseModel):
    role: str
    score: int
    votes_correct: int
    votes_total: int
    speeches: int
    skill_uses: int
    survived_rounds: int


class VoteRecordItem(BaseModel):
    voter_id: int
    target_id: Optional[int] = None
    target_role: Optional[str] = None
    voter_role: str
    is_correct: bool = False


class AbilityUseItem(BaseModel):
    player_id: int
    ability: str
    target_id: Optional[int] = None
    success: bool = False


class StatsResponse(BaseModel):
    player_stats: dict[int, PlayerStatItem]
    vote_records: list[VoteRecordItem]
    ability_uses: list[AbilityUseItem] = []


class WSEvent(BaseModel):
    event_type: str
    game_id: int
    round_number: int
    phase: str
    player_id: Optional[int] = None
    data: dict = {}
    timestamp: Optional[str] = None
