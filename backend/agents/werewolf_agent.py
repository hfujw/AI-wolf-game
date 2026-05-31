from agents.base_agent import BaseAgent
from prompts.system_prompts import get_system_prompt
from prompts.templates import build_speech_prompt, build_vote_prompt, NIGHT_WEREWOLF_TEMPLATE
from schemas.game_schemas import AgentContext, AgentDecision


class WerewolfAgent(BaseAgent):
    def __init__(self, player_id: int, personality: str, llm_client=None):
        super().__init__(player_id, "werewolf", personality, llm_client)

    async def decide(self, context: AgentContext) -> AgentDecision:
        return await self._decide_with_react(context)

    def _get_partners_str(self, context: AgentContext) -> str:
        partners = [str(p) for p in context.werewolf_partners]
        return ", ".join(partners) if partners else "无"

    async def _decide_kill(self, context: AgentContext) -> AgentDecision:
        partners_str = self._get_partners_str(context)
        system_prompt = get_system_prompt("werewolf", self.personality, partners=partners_str)
        user_message = NIGHT_WEREWOLF_TEMPLATE.format(
            round_number=context.round_number, alive_players=self._build_alive_str(context),
            valid_targets=self._build_valid_str(context), partners=partners_str,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.5)
        return self._parse_target(context, result, "kill")

    async def _decide_speech(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("werewolf", self.personality, partners=self._get_partners_str(context))
        my_player = next((p for p in context.alive_players if p.id == context.player_id), None)
        seat = my_player.seat_number if my_player else context.player_id
        user_message = build_speech_prompt(
            round_number=context.round_number, role="werewolf", seat_number=seat,
            alive_players=[{"seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            game_history=self._build_history(context), conversation_history=context.conversation_history,
            partners=self._get_partners_str(context),
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.8)
        return AgentDecision(action="speech", speech=result.get("speech", result.get("content", "")),
                             internal_thought=result.get("internal_thought", ""), reasoning=result.get("reasoning"))

    async def _decide_vote(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("werewolf", self.personality, partners=self._get_partners_str(context))
        user_message = build_vote_prompt(
            round_number=context.round_number,
            alive_players=[{"id": p.id, "seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            valid_targets=context.valid_targets, game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.6)
        return self._parse_target(context, result, "vote")
