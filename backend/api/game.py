import random
import string
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.room import Room
from models.game import Game
from models.game_player import GamePlayer
from models.game_event import GameEvent
from schemas.game_schemas import (
    RoomCreateResponse,
    JoinRoomRequest,
    GameStatusResponse,
    AlivePlayerInfo,
    VisibleEvent,
    ReplayResponse,
    ReplayEvent,
    EventsResponse,
    StatsResponse,
    PlayerStatItem,
    VoteRecordItem,
    AbilityUseItem,
)
from services.game_service import GameService, game_services

router = APIRouter()


def _generate_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase, k=4))


@router.get("/rooms")
async def list_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).order_by(Room.id.desc()).limit(50))
    rooms = result.scalars().all()
    return [{"id": r.id, "room_code": r.room_code, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rooms]


@router.post("/rooms", response_model=RoomCreateResponse)
async def create_room(db: AsyncSession = Depends(get_db)):
    for _ in range(10):
        code = _generate_room_code()
        result = await db.execute(select(Room).where(Room.room_code == code))
        existing = result.scalar_one_or_none()
        if not existing:
            break

    room = Room(room_code=code, status="waiting")
    db.add(room)
    await db.commit()
    await db.refresh(room)

    return RoomCreateResponse(room_id=room.id, room_code=room.room_code)


@router.post("/rooms/{room_id}/join")
async def join_room(room_id: int, req: JoinRoomRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room.status != "waiting":
        raise HTTPException(status_code=400, detail="房间已开始或已结束")

    return {"room_id": room.id, "room_code": room.room_code, "message": "加入成功"}


@router.post("/rooms/{room_id}/start")
async def start_game(room_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room.status != "waiting":
        raise HTTPException(status_code=400, detail="游戏已开始")

    room.status = "playing"
    await db.commit()

    service = GameService(db)
    game = await service.start_game(room_id)
    await db.commit()

    return {"game_id": game.id, "message": "游戏已开始"}


@router.post("/games/{game_id}/force-start")
async def force_start_game(game_id: int, db: AsyncSession = Depends(get_db)):
    """手动触发游戏开始（备用端点）"""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    if game_id in game_services:
        existing = game_services[game_id]
        return {
            "game_id": game_id,
            "phase": existing.phase,
            "round_number": existing.round,
            "winner": existing.winner,
            "message": "游戏已在运行中",
        }

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = player_result.scalars().all()

    if not players:
        raise HTTPException(status_code=400, detail="对局没有玩家，可能数据异常")

    service = GameService(db)
    engine = service.start_game_engine(game, list(players))

    game_services[game_id] = engine
    asyncio.create_task(engine.run())

    return {
        "game_id": game_id,
        "phase": engine.phase,
        "round_number": engine.round,
        "message": "游戏已手动启动",
    }


@router.get("/rooms/lookup/{room_code}")
async def lookup_room(room_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.room_code == room_code.upper()))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    return {"id": room.id, "room_code": room.room_code, "status": room.status}


@router.get("/rooms/{room_id}/status")
async def get_room_status(room_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")

    game_result = await db.execute(
        select(Game).where(Game.room_id == room_id).order_by(Game.id.desc()).limit(1)
    )
    game = game_result.scalar_one_or_none()

    if not game:
        return {"room_id": room.id, "room_code": room.room_code, "status": room.status}

    return await _build_game_status(game.id, db)


@router.get("/games/{game_id}/status", response_model=GameStatusResponse)
async def get_game_status(game_id: int, db: AsyncSession = Depends(get_db)):
    return await _build_game_status(game_id, db)


@router.get("/games/{game_id}/debug")
async def debug_game(game_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = player_result.scalars().all()

    event_result = await db.execute(
        select(GameEvent).where(GameEvent.game_id == game_id).order_by(GameEvent.id.desc()).limit(50)
    )
    events = event_result.scalars().all()

    engine = game_services.get(game_id)

    return {
        "game_id": game.id,
        "started_at": game.started_at.isoformat() if game.started_at else None,
        "ended_at": game.ended_at.isoformat() if game.ended_at else None,
        "total_rounds": game.total_rounds,
        "winner": game.winner,
        "engine_online": engine is not None,
        "engine_phase": engine.phase if engine else "N/A",
        "engine_round": engine.round if engine else 0,
        "engine_winner": engine.winner if engine else None,
        "witch_antidote": engine.witch_has_antidote if engine else None,
        "witch_poison": engine.witch_has_poison if engine else None,
        "players": [
            {
                "id": p.id,
                "name": p.player_name,
                "role": p.role,
                "personality": p.personality,
                "seat_number": p.seat_number,
                "is_alive": engine.players[i].is_alive if engine else p.is_alive if i < len(engine.players) else p.is_alive,
            }
            for i, p in enumerate(players)
        ] if engine else [
            {
                "id": p.id,
                "name": p.player_name,
                "role": p.role,
                "personality": p.personality,
                "seat_number": p.seat_number,
                "is_alive": p.is_alive,
            }
            for p in players
        ],
        "events_count": len(events),
        "engine_log": engine._log[-50:] if engine else [],
        "stats": {
            pid: stats for pid, stats in engine.stats.player_stats.items()
        } if engine else {},
        "latest_events": [
            {
                "round": e.round_number,
                "phase": e.phase,
                "type": e.event_type,
                "public": e.public_content,
                "private": e.private_content,
                "thought": e.internal_thought,
            }
            for e in reversed(events[:30])
        ],
    }


@router.get("/games/{game_id}/replay", response_model=ReplayResponse)
async def get_game_replay(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = player_result.scalars().all()

    event_result = await db.execute(
        select(GameEvent)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.id)
    )
    events = event_result.scalars().all()

    player_map = {p.id: p for p in players}
    replay_events = []
    for e in events:
        pname = None
        if e.player_id and e.player_id in player_map:
            pname = player_map[e.player_id].player_name
        replay_events.append(ReplayEvent(
            round_number=e.round_number,
            phase=e.phase,
            player_id=e.player_id,
            player_name=pname,
            event_type=e.event_type,
            public_content=e.public_content,
            private_content=e.private_content,
            internal_thought=e.internal_thought,
            reasoning_content=e.reasoning_content,
        ))

    players_data = [
        {
            "id": p.id,
            "name": p.player_name,
            "role": p.role,
            "seat_number": p.seat_number,
            "is_alive": p.is_alive,
        }
        for p in players
    ]

    return ReplayResponse(game_id=game.id, players=players_data, events=replay_events)


@router.get("/games/{game_id}/events", response_model=EventsResponse)
async def get_game_events(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = player_result.scalars().all()

    event_result = await db.execute(
        select(GameEvent)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.id)
    )
    events = event_result.scalars().all()

    player_map = {p.id: p for p in players}
    replay_events = []
    for e in events:
        pname = None
        if e.player_id and e.player_id in player_map:
            pname = player_map[e.player_id].player_name
        replay_events.append(ReplayEvent(
            round_number=e.round_number,
            phase=e.phase,
            player_id=e.player_id,
            player_name=pname,
            event_type=e.event_type,
            public_content=e.public_content,
            private_content=e.private_content,
            internal_thought=e.internal_thought,
            reasoning_content=e.reasoning_content,
        ))

    players_data = [
        {
            "id": p.id,
            "name": p.player_name,
            "role": p.role,
            "seat_number": p.seat_number,
            "is_alive": p.is_alive,
        }
        for p in players
    ]

    return EventsResponse(game_id=game.id, players=players_data, events=replay_events)


@router.get("/games/{game_id}/stats", response_model=StatsResponse)
async def get_game_stats(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    engine = game_services.get(game_id)

    if not engine or not hasattr(engine, 'stats'):
        return StatsResponse(
            player_stats={},
            vote_records=[],
            ability_uses=[],
        )

    stats = engine.stats
    player_stats = {}
    for pid, ps in stats.player_stats.items():
        player_stats[pid] = PlayerStatItem(
            role=ps.get("role", ""),
            score=ps.get("score", 0),
            votes_correct=ps.get("votes_correct", 0),
            votes_total=ps.get("votes_total", 0),
            speeches=ps.get("speeches", 0),
            skill_uses=ps.get("skill_uses", 0),
            survived_rounds=ps.get("survived_rounds", 0),
        )

    vote_records = [
        VoteRecordItem(
            voter_id=vr.get("voter_id", 0),
            target_id=vr.get("target_id"),
            target_role=vr.get("target_role"),
            voter_role=vr.get("voter_role", ""),
            is_correct=vr.get("is_correct", False),
        )
        for vr in stats.vote_records
    ]

    ability_uses = [
        AbilityUseItem(
            player_id=au.get("player_id", 0),
            ability=au.get("ability", ""),
            target_id=au.get("target_id"),
            success=au.get("success", False),
        )
        for au in stats.ability_uses
    ]

    return StatsResponse(
        player_stats=player_stats,
        vote_records=vote_records,
        ability_uses=ability_uses,
    )


async def _build_game_status(game_id: int, db: AsyncSession):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = player_result.scalars().all()

    alive = [
        AlivePlayerInfo(id=p.id, name=p.player_name, seat_number=p.seat_number, is_alive=p.is_alive, role=p.role)
        for p in players
    ]

    event_result = await db.execute(
        select(GameEvent)
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.id.desc())
        .limit(20)
    )
    events = event_result.scalars().all()
    visible_events = [
        VisibleEvent(
            id=e.id,
            round_number=e.round_number,
            phase=e.phase,
            player_id=e.player_id,
            event_type=e.event_type,
            public_content=e.public_content,
            private_content=None,
            reasoning_content=e.reasoning_content,
        )
        for e in reversed(events)
    ]

    phase = "waiting"
    round_number = 0
    if game_id in game_services:
        engine = game_services[game_id]
        phase = engine.phase
        round_number = engine.round
    elif game.started_at:
        phase = game.winner and "game_over" or "ended"
        round_number = game.total_rounds or 0

    return GameStatusResponse(
        game_id=game.id,
        phase=phase,
        round_number=round_number,
        alive_players=alive,
        winner=game.winner,
        events=visible_events,
    )
