from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.game import Game


class GameRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, game_id: int) -> Game | None:
        result = await self.db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one_or_none()

    async def create(self, game: Game) -> Game:
        self.db.add(game)
        await self.db.flush()
        await self.db.refresh(game)
        return game

    async def update(self, game: Game) -> Game:
        await self.db.merge(game)
        await self.db.flush()
        return game
