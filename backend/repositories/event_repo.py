from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.game_event import GameEvent


class EventRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: GameEvent) -> GameEvent:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_game(self, game_id: int, limit: int = 500) -> list[GameEvent]:
        result = await self.db.execute(
            select(GameEvent)
            .where(GameEvent.game_id == game_id)
            .order_by(GameEvent.id)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest(self, game_id: int, limit: int = 20) -> list[GameEvent]:
        result = await self.db.execute(
            select(GameEvent)
            .where(GameEvent.game_id == game_id)
            .order_by(GameEvent.id.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
