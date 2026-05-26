from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from db.database import async_session
from models.game_player import GamePlayer
from models.game_event import GameEvent
from schemas.game_schemas import WSEvent

router = APIRouter()

ws_connections: dict[int, list[tuple[WebSocket, str]]] = {}


async def broadcast_game_event(game_id: int, event: GameEvent):
    if game_id not in ws_connections:
        return

    player_name = None
    async with async_session() as db:
        if event.player_id:
            result = await db.execute(
                select(GamePlayer).where(GamePlayer.id == event.player_id)
            )
            player = result.scalar_one_or_none()
            if player:
                player_name = player.player_name

    ws_event = WSEvent(
        event_type=event.event_type,
        game_id=event.game_id,
        round_number=event.round_number,
        phase=event.phase,
        player_id=event.player_id,
        data={
            "public_content": event.public_content,
            "private_content": event.private_content,
            "internal_thought": event.internal_thought,
            "reasoning_content": event.reasoning_content,
            "player_name": player_name,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    disconnected = []
    for ws, viewer_type in ws_connections[game_id]:
        try:
            payload = ws_event.model_dump()
            if viewer_type != "god":
                payload["data"]["private_content"] = None
                payload["data"]["internal_thought"] = None
                payload["data"]["reasoning_content"] = None
            await ws.send_json(payload)
        except Exception:
            disconnected.append((ws, viewer_type))

    for item in disconnected:
        if item in ws_connections.get(game_id, []):
            ws_connections[game_id].remove(item)


@router.websocket("/ws/game/{game_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: int,
    viewer: str = Query("normal"),
):
    await websocket.accept()

    if game_id not in ws_connections:
        ws_connections[game_id] = []
    ws_connections[game_id].append((websocket, viewer))

    async with async_session() as db:
        event_result = await db.execute(
            select(GameEvent)
            .where(GameEvent.game_id == game_id)
            .order_by(GameEvent.id)
        )
        events = event_result.scalars().all()

        player_result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game_id)
        )
        players = player_result.scalars().all()
        player_map = {p.id: p for p in players}

        for event in events:
            pname = None
            if event.player_id and event.player_id in player_map:
                pname = player_map[event.player_id].player_name

            payload = WSEvent(
                event_type=event.event_type,
                game_id=event.game_id,
                round_number=event.round_number,
                phase=event.phase,
                player_id=event.player_id,
                data={
                    "public_content": event.public_content,
                    "private_content": event.private_content if viewer == "god" else None,
                    "internal_thought": event.internal_thought if viewer == "god" else None,
                    "reasoning_content": event.reasoning_content if viewer == "god" else None,
                    "player_name": pname,
                },
                timestamp=event.created_at.isoformat() if event.created_at else None,
            ).model_dump()

            try:
                await websocket.send_json(payload)
            except Exception:
                return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if game_id in ws_connections:
            ws_connections[game_id] = [
                (ws, vt) for ws, vt in ws_connections[game_id] if ws != websocket
            ]
