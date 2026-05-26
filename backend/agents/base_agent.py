from abc import ABC, abstractmethod

from schemas.game_schemas import AgentContext, AgentDecision


class BaseAgent(ABC):
    def __init__(self, player_id: int, role: str, personality: str, llm_client=None):
        self.player_id = player_id
        self.role = role
        self.personality = personality
        self.llm_client = llm_client

    @abstractmethod
    async def decide(self, context: AgentContext) -> AgentDecision:
        pass

    async def _chat(self, messages: list[dict], temperature: float = 0.8) -> dict:
        return await self.llm_client.chat(messages, player_id=self.player_id, temperature=temperature)

    def _fmt_players(self, ctx: AgentContext) -> tuple[str, str]:
        alive_parts = []
        valid_parts = []
        id_to_seat = {p.id: p.seat_number for p in ctx.alive_players}
        for p in ctx.alive_players:
            if p.is_alive:
                alive_parts.append(f"{p.seat_number}号({p.name})")
        for vid in ctx.valid_targets:
            seat = id_to_seat.get(vid, vid)
            valid_parts.append(str(seat))
        return ", ".join(alive_parts), ", ".join(valid_parts)

    def _format_history(self, context: AgentContext) -> str:
        lines = []
        for event in context.visible_events[-20:]:
            line = f"[第{event.round_number}轮][{event.phase}] "
            if event.public_content:
                line += event.public_content
            if event.private_content:
                line += f" (私密: {event.private_content})"
            lines.append(line)
        return "\n".join(lines) if lines else "暂无历史记录。"

    def _parse_target(self, context: AgentContext, result: dict, action: str) -> AgentDecision:
        raw_target = result.get("target_id")
        target_id = None
        if raw_target is not None and str(raw_target).strip():
            try:
                seat = int(str(raw_target).strip())
                for p in context.alive_players:
                    if p.seat_number == seat:
                        target_id = str(p.id)
                        break
            except (ValueError, TypeError):
                pass
        return AgentDecision(
            action=action,
            target_id=target_id,
            internal_thought=result.get("internal_thought", ""),
            reasoning=result.get("reasoning"),
        )
