from agents.base_agent import BaseAgent
from prompts.system_prompts import get_system_prompt
from prompts.templates import build_speech_prompt, build_vote_prompt, NIGHT_HUNTER_TEMPLATE
from schemas.game_schemas import AgentContext, AgentDecision


class HunterAgent(BaseAgent):
    def __init__(self, player_id: int, personality: str, llm_client=None):
        super().__init__(player_id, "hunter", personality, llm_client)

    async def decide(self, context: AgentContext) -> AgentDecision:
        return await self._decide_with_react(context)

    async def _decide_shoot(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("hunter", self.personality)
        user_message = NIGHT_HUNTER_TEMPLATE.format(
            round_number=context.round_number,
            alive_players=self._build_alive_str(context),
            valid_targets=self._build_valid_str(context),
            game_history=self._build_history(context),
            conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.5)
        return self._parse_target(context, result, "shoot")

    async def _decide_speech(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("hunter", self.personality)
        my_player = next((p for p in context.alive_players if p.id == context.player_id), None)
        seat = my_player.seat_number if my_player else context.player_id
        user_message = build_speech_prompt(
            round_number=context.round_number, role="hunter", seat_number=seat,
            alive_players=[{"seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.8)
        return AgentDecision(action="speech", speech=result.get("speech", result.get("content", "")),
                             internal_thought=result.get("internal_thought", ""), reasoning=result.get("reasoning"))

    async def _decide_vote(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("hunter", self.personality)
        user_message = build_vote_prompt(
            round_number=context.round_number,
            alive_players=[{"id": p.id, "seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            valid_targets=context.valid_targets, game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.6)
        return self._parse_target(context, result, "vote")
