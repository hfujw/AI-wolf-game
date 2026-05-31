import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from models.game import Game
from models.game_player import GamePlayer
from agents.werewolf_agent import WerewolfAgent
from agents.seer_agent import SeerAgent
from agents.witch_agent import WitchAgent
from agents.hunter_agent import HunterAgent
from agents.villager_agent import VillagerAgent
from core.agent_manager import AgentManager
from core.engine import GameEngine
from llm.llm_client import LLMClient

game_services: dict[int, GameEngine] = {}

_shared_llm_client: LLMClient = None


def get_llm_client() -> LLMClient:
    global _shared_llm_client
    if _shared_llm_client is None:
        _shared_llm_client = LLMClient()
    return _shared_llm_client


class GameService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_game(self, room_id: int) -> Game:
        game = Game(room_id=room_id)
        self.db.add(game)
        await self.db.flush()
        await self.db.refresh(game)

        roles = Config.ROLES.copy()
        random.shuffle(roles)

        personalities = Config.PERSONALITIES
        role_personality_count: dict[str, int] = {rk: 0 for rk in personalities}

        players = []
        for seat in range(1, Config.PLAYER_COUNT + 1):
            role = roles[seat - 1]
            personality_list = personalities.get(role, [""])
            idx = role_personality_count[role] % len(personality_list)
            personality = personality_list[idx]
            role_personality_count[role] = idx + 1

            player_name = f"Player_{seat}"
            player = GamePlayer(
                game_id=game.id, player_name=player_name, role=role,
                personality=personality, is_alive=True, seat_number=seat,
            )
            self.db.add(player)
            await self.db.flush()
            await self.db.refresh(player)
            players.append(player)

        engine = self._build_engine(game, players)
        game_services[game.id] = engine
        asyncio.create_task(engine.run())
        return game

    def _build_engine(self, game: Game, players: list[GamePlayer]) -> GameEngine:
        llm_client = get_llm_client()
        agents = {p.id: self._create_agent(p.id, p.role, p.personality or "", llm_client) for p in players}
        agent_manager = AgentManager(agents)
        engine = GameEngine(game, players, agent_manager)

        from api.ws import broadcast_game_event as _broadcast

        async def event_callback(event):
            await _broadcast(game.id, event)

        engine.on_event(event_callback)
        return engine

    def start_game_engine(self, game: Game, players: list[GamePlayer]) -> GameEngine:
        return self._build_engine(game, players)

    def _create_agent(self, player_id: int, role: str, personality: str, llm_client: LLMClient):
        if role == "werewolf":
            return WerewolfAgent(player_id, personality, llm_client)
        elif role == "seer":
            return SeerAgent(player_id, personality, llm_client)
        elif role == "witch":
            return WitchAgent(player_id, personality, llm_client)
        elif role == "hunter":
            return HunterAgent(player_id, personality, llm_client)
        elif role == "villager":
            return VillagerAgent(player_id, personality, llm_client)
        return VillagerAgent(player_id, personality, llm_client)
