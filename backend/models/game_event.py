from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

from db.database import Base


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    phase = Column(String(30), nullable=False)
    player_id = Column(Integer, ForeignKey("game_players.id"), nullable=True)
    event_type = Column(String(30), nullable=False)
    public_content = Column(Text, nullable=True)
    private_content = Column(Text, nullable=True)
    internal_thought = Column(Text, nullable=True)
    reasoning_content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
