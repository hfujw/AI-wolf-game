from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.game_event import GameEvent
from models.game_player import GamePlayer
from schemas.game_schemas import AgentContext, AlivePlayerInfo, VisibleEvent
from memory.summarizer import ConversationSummarizer


class Memory:
    def __init__(self):
        self.conversations: list[dict] = []
        self.current_round_discussions: list[dict] = []
        self.summarizer = ConversationSummarizer(window_size=10, summary_interval=3)

    def add_conversation(self, round_number: int, phase: str, speaker: str, content: str, event_type: str = "discussion"):
        conv = {
            "round": round_number,
            "phase": phase,
            "speaker": speaker,
            "content": content,
            "type": event_type,
        }
        self.conversations.append(conv)
        self.summarizer.add(conv)
        if phase in ("day_speech", "day_vote"):
            self.current_round_discussions.append(conv)

    def clear_current_round(self):
        self.current_round_discussions = []

    def get_all_conversations(self) -> str:
        return self.summarizer.get_context(self.conversations[-1]["round"] if self.conversations else 0)


class MemoryManager:
    def __init__(self, db: AsyncSession, game_id: int, memory: Memory = None):
        self.db = db
        self.game_id = game_id
        self.memory = memory or Memory()

    async def build_context(self, player_id: int, role: str, personality: str, game_state: dict) -> AgentContext:
        phase = game_state.get("phase", "unknown")
        round_number = game_state.get("round_number", 0)

        player_result = await self.db.execute(
            select(GamePlayer).where(GamePlayer.game_id == self.game_id)
        )
        all_players = player_result.scalars().all()

        alive_players = []
        for p in all_players:
            alive_players.append(AlivePlayerInfo(id=p.id, name=p.player_name, seat_number=p.seat_number, is_alive=p.is_alive, role=None))  # 不暴露角色给任何玩家

        event_result = await self.db.execute(
            select(GameEvent).where(GameEvent.game_id == self.game_id).order_by(GameEvent.id)
        )
        all_events = event_result.scalars().all()

        visible_events = self._filter_events(all_events, player_id, role)

        werewolf_partners = []
        seer_checks = []
        witch_info = {}
        private_info = {}

        if role == "werewolf":
            wolf_partners_result = await self.db.execute(
                select(GamePlayer).where(
                    GamePlayer.game_id == self.game_id,
                    GamePlayer.role == "werewolf",
                    GamePlayer.id != player_id,
                )
            )
            partners = wolf_partners_result.scalars().all()
            werewolf_partners = [p.id for p in partners]
            private_info["werewolf_partners"] = [f"{p.seat_number}号 {p.player_name}" for p in partners]

        elif role == "seer":
            for event in all_events:
                if event.phase == "night_seer" and event.player_id == player_id and event.private_content:
                    seer_checks.append({"target_name": event.private_content, "round": event.round_number, "event_type": event.event_type})
            private_info["seer_checks"] = seer_checks

        elif role == "witch":
            witch_info = {"has_antidote": True, "has_poison": True, "victim_id": None}
            for event in all_events:
                if event.phase == "night_witch" and event.player_id == player_id:
                    if event.event_type == "witch_use_antidote":
                        witch_info["has_antidote"] = False
                    elif event.event_type == "witch_use_poison":
                        witch_info["has_poison"] = False
            private_info["witch_info"] = witch_info

        elif role == "hunter":
            private_info["hunter_info"] = {"can_shoot": True}

        valid_targets = self._get_valid_targets(phase, role, player_id, all_players, werewolf_partners)

        own_player = next((p for p in all_players if p.id == player_id), None)
        my_seat = own_player.seat_number if own_player else 0

        return AgentContext(
            phase=phase,
            round_number=round_number,
            player_id=player_id,
            my_seat_number=my_seat,
            role=role,
            personality=personality,
            alive_players=alive_players,
            valid_targets=valid_targets,
            visible_events=visible_events,
            private_info=private_info,
            werewolf_partners=werewolf_partners,
            seer_checks=seer_checks,
            witch_info=witch_info,
        )

    def _filter_events(self, events: list[GameEvent], player_id: int, role: str) -> list[VisibleEvent]:
        visible = []
        for event in events:
            # 过滤掉 UI 专用事件，AI 不需要这些
            if event.event_type in ("night_summary", "agent_thinking", "thinking_clear"):
                continue
            ve = VisibleEvent(
                id=event.id, round_number=event.round_number, phase=event.phase,
                player_id=event.player_id, event_type=event.event_type,
                public_content=event.public_content, private_content=None,
                reasoning_content=event.reasoning_content,
            )
            if role == "werewolf":
                if event.event_type == "werewolf_kill" and event.player_id == player_id:
                    ve.private_content = event.private_content
                if event.private_content and event.phase == "night_werewolf":
                    ve.private_content = event.private_content
            elif role == "seer":
                if event.player_id == player_id and event.phase == "night_seer":
                    ve.private_content = event.private_content
            elif role == "witch":
                if event.phase == "night_witch":
                    ve.private_content = event.private_content
            elif role == "hunter":
                if event.phase == "hunter_shoot" and event.player_id == player_id:
                    ve.private_content = event.private_content
            visible.append(ve)
        return visible

    def _get_valid_targets(self, phase: str, role: str, player_id: int, all_players: list[GamePlayer], werewolf_partners: list[int]) -> list[int]:
        alive_player_ids = []
        for p in all_players:
            if p.is_alive and p.id != player_id:
                alive_player_ids.append(p.id)

        if phase == "night_werewolf":
            return [pid for pid in alive_player_ids if pid not in werewolf_partners]
        elif phase in ("night_seer", "night_witch", "day_vote", "hunter_shoot"):
            return alive_player_ids
        return alive_player_ids
