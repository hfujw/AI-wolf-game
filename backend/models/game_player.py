from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from db.database import Base


class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)
    personality = Column(String(100), nullable=True)
    is_alive = Column(Boolean, default=True)
    seat_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
