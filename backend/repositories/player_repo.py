from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.game_player import GamePlayer


class PlayerRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_game(self, game_id: int) -> list[GamePlayer]:
        result = await self.db.execute(
            select(GamePlayer).where(GamePlayer.game_id == game_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, player_id: int) -> GamePlayer | None:
        return await self.db.get(GamePlayer, player_id)

    async def create(self, player: GamePlayer) -> GamePlayer:
        self.db.add(player)
        await self.db.flush()
        await self.db.refresh(player)
        return player

    async def mark_dead(self, player_id: int):
        player = await self.db.get(GamePlayer, player_id)
        if player:
            player.is_alive = False
