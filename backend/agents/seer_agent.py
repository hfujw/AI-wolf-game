from agents.base_agent import BaseAgent
from prompts.system_prompts import get_system_prompt
from prompts.templates import build_speech_prompt, build_vote_prompt, NIGHT_SEER_TEMPLATE
from schemas.game_schemas import AgentContext, AgentDecision


class SeerAgent(BaseAgent):
    def __init__(self, player_id: int, personality: str, llm_client=None):
        super().__init__(player_id, "seer", personality, llm_client)

    async def decide(self, context: AgentContext) -> AgentDecision:
        try:
            if context.phase == "night_seer":
                return await self._decide_check(context)
            elif context.phase == "day_speech":
                return await self._decide_speech(context)
            elif context.phase == "day_vote":
                return await self._decide_vote(context)
            else:
                return AgentDecision(action="pass", internal_thought="等待下一阶段。")
        except Exception:
            return self.llm_client.get_fallback(context.phase, self.role, context.valid_targets)

    def _build_alive_str(self, context: AgentContext) -> str:
        parts = []
        for p in context.alive_players:
            if p.is_alive:
                parts.append(f"{p.seat_number}号({p.name})")
        return ", ".join(parts)

    def _build_valid_str(self, context: AgentContext) -> str:
        id_to_seat = {p.id: p.seat_number for p in context.alive_players}
        return ", ".join(str(id_to_seat.get(vid, vid)) for vid in context.valid_targets)

    def _build_history(self, context: AgentContext) -> str:
        lines = []
        for event in context.visible_events[-20:]:
            line = f"[第{event.round_number}轮][{event.phase}] "
            if event.public_content:
                line += event.public_content
            if event.private_content:
                line += f" (私密: {event.private_content})"
            lines.append(line)
        return "\n".join(lines) if lines else ""

    def _format_seer_checks(self, context: AgentContext) -> str:
        if not context.seer_checks:
            return "暂无查验记录"
        return " | ".join(
            f"第{e.get('round', '?')}晚查验{e.get('target_name', '')}" for e in context.seer_checks
        )

    async def _decide_check(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("seer", self.personality)
        user_message = NIGHT_SEER_TEMPLATE.format(
            round_number=context.round_number,
            alive_players=self._build_alive_str(context),
            valid_targets=self._build_valid_str(context),
            seer_checks=self._format_seer_checks(context),
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.5)
        return self._parse_target(context, result, "check")

    async def _decide_speech(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("seer", self.personality)
        my_player = next((p for p in context.alive_players if p.id == context.player_id), None)
        seat = my_player.seat_number if my_player else context.player_id
        user_message = build_speech_prompt(
            round_number=context.round_number, role="seer", seat_number=seat,
            alive_players=[{"seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            game_history=self._build_history(context), conversation_history=context.conversation_history,
            seer_checks=context.seer_checks,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.8)
        return AgentDecision(action="speech", speech=result.get("speech", result.get("content", "")),
                             internal_thought=result.get("internal_thought", ""), reasoning=result.get("reasoning"))

    async def _decide_vote(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("seer", self.personality)
        user_message = build_vote_prompt(
            round_number=context.round_number,
            alive_players=[{"id": p.id, "seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            valid_targets=context.valid_targets, game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.6)
        return self._parse_target(context, result, "vote")
