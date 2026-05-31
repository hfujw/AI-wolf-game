from agents.base_agent import BaseAgent
from prompts.system_prompts import get_system_prompt
from prompts.templates import build_speech_prompt, build_vote_prompt, NIGHT_WITCH_TEMPLATE
from schemas.game_schemas import AgentContext, AgentDecision


class WitchAgent(BaseAgent):
    def __init__(self, player_id: int, personality: str, llm_client=None):
        super().__init__(player_id, "witch", personality, llm_client)

    async def decide(self, context: AgentContext) -> AgentDecision:
        return await self._decide_with_react(context)

    async def _decide_potion(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("witch", self.personality)
        wi = context.witch_info
        victim_id = wi.get("victim_id")
        victim_info = f"今晚被狼人袭击：{victim_id}号" if victim_id else "今晚是平安夜"
        antidote_status = "可用" if wi.get("has_antidote", True) else "已用完"
        poison_status = "可用" if wi.get("has_poison", True) else "已用完"
        user_message = NIGHT_WITCH_TEMPLATE.format(
            round_number=context.round_number, seat_number=context.my_seat_number,
            victim_info=victim_info,
            antidote_status=antidote_status, poison_status=poison_status,
            alive_players=self._build_alive_str(context), valid_targets=self._build_valid_str(context),
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.5)

        use_poison = result.get("use_poison", False)
        poison_target = result.get("poison_target")
        if use_poison and poison_target:
            try:
                seat = int(str(poison_target).strip())
                for p in context.alive_players:
                    if p.seat_number == seat:
                        poison_target = str(p.id)
                        break
            except (ValueError, TypeError):
                use_poison = False
                poison_target = None
        else:
            poison_target = None
        return AgentDecision(action="witch_action", use_antidote=result.get("use_antidote", False),
                             use_poison=use_poison, poison_target=poison_target,
                             internal_thought=result.get("internal_thought", ""), reasoning=result.get("reasoning"))

    async def _decide_speech(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("witch", self.personality)
        my_player = next((p for p in context.alive_players if p.id == context.player_id), None)
        seat = my_player.seat_number if my_player else context.player_id
        user_message = build_speech_prompt(
            round_number=context.round_number, role="witch", seat_number=seat,
            alive_players=[{"seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.8)
        return AgentDecision(action="speech", speech=result.get("speech", result.get("content", "")),
                             internal_thought=result.get("internal_thought", ""), reasoning=result.get("reasoning"))

    async def _decide_vote(self, context: AgentContext) -> AgentDecision:
        system_prompt = get_system_prompt("witch", self.personality)
        user_message = build_vote_prompt(
            round_number=context.round_number,
            alive_players=[{"id": p.id, "seat_number": p.seat_number, "name": p.name, "is_alive": p.is_alive} for p in context.alive_players],
            valid_targets=context.valid_targets, game_history=self._build_history(context), conversation_history=context.conversation_history,
        )
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        result = await self._chat(messages, temperature=0.6)
        return self._parse_target(context, result, "vote")
