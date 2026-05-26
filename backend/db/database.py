from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import Config

engine = create_async_engine(Config.DATABASE_URL, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    from models.room import Room
    from models.game import Game
    from models.game_player import GamePlayer
    from models.game_event import GameEvent

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
