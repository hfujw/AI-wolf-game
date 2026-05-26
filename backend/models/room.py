from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from db.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(10), unique=True, nullable=False)
    status = Column(String(20), default="waiting")
    created_at = Column(DateTime, server_default=func.now())
