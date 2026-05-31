import asyncio
import random
import logging

from agents.base_agent import BaseAgent
from schemas.game_schemas import AgentContext, AgentDecision
from core.concurrency import LLM_SEMAPHORE

logger = logging.getLogger("agent_manager")


class AgentManager:
    def __init__(self, agents: dict[int, BaseAgent]):
        self.agents = agents

    async def _safe_decide(self, agent: BaseAgent, context: AgentContext) -> AgentDecision:
        async with LLM_SEMAPHORE:
            try:
                return await asyncio.wait_for(agent.decide(context), timeout=120)
            except asyncio.TimeoutError:
                logger.warning(f"Agent {agent.player_id}({agent.role}) total timeout after 120s")
                return self._fallback_for(context)
            except Exception as e:
                logger.warning(f"Agent {agent.player_id}({agent.role}) failed: {e}")
                return self._fallback_for(context)

    def _fallback_for(self, context: AgentContext) -> AgentDecision:
        phase = context.phase
        valid = context.valid_targets
        if phase == "night_werewolf":
            return AgentDecision(action="kill", target_id=str(random.choice(valid)) if valid else None, internal_thought="Fallback: 随机击杀。")
        elif phase == "night_seer":
            return AgentDecision(action="check", target_id=str(random.choice(valid)) if valid else None, internal_thought="Fallback: 随机查验。")
        elif phase == "night_witch":
            return AgentDecision(action="witch_action", use_antidote=True, use_poison=False, internal_thought="Fallback: 默认使用解药。")
        elif phase in ("day_vote", "hunter_shoot"):
            return AgentDecision(action=phase, target_id=str(random.choice(valid)) if valid else None, internal_thought="Fallback: 随机选择。")
        elif phase == "day_speech":
            return AgentDecision(action="speech", speech="过。", internal_thought="Fallback。")
        return AgentDecision(action="pass", internal_thought="Fallback。")

    async def ask_wolves(self, wolf_ids: list[int], contexts: dict[int, AgentContext]) -> tuple[str | None, list[AgentDecision]]:
        tasks = []
        for wid in wolf_ids:
            if wid in self.agents and wid in contexts:
                tasks.append(self._safe_decide(self.agents[wid], contexts[wid]))
            else:
                tasks.append(self._make_default(wid, contexts.get(wid)))
        decisions = await asyncio.gather(*tasks)
        valid_decisions = [d for d in decisions if d.target_id is not None]
        chosen = random.choice(valid_decisions) if valid_decisions else None
        return chosen.target_id if chosen else None, decisions

    async def ask_seer(self, seer_id: int, context: AgentContext) -> AgentDecision:
        if seer_id not in self.agents:
            return self._fallback_for(context)
        return await self._safe_decide(self.agents[seer_id], context)

    async def ask_witch(self, witch_id: int, context: AgentContext) -> AgentDecision:
        if witch_id not in self.agents:
            return self._fallback_for(context)
        return await self._safe_decide(self.agents[witch_id], context)

    async def ask_hunter(self, hunter_id: int, context: AgentContext) -> AgentDecision:
        if hunter_id not in self.agents:
            return self._fallback_for(context)
        return await self._safe_decide(self.agents[hunter_id], context)

    async def ask_speech(self, player_id: int, context: AgentContext) -> AgentDecision:
        if player_id not in self.agents:
            return self._fallback_for(context)
        return await self._safe_decide(self.agents[player_id], context)

    async def ask_votes(self, contexts: dict[int, AgentContext]) -> dict[int, AgentDecision]:
        async def vote_one(pid: int, ctx: AgentContext) -> tuple[int, AgentDecision]:
            if pid not in self.agents:
                return pid, self._fallback_for(ctx)
            decision = await self._safe_decide(self.agents[pid], ctx)
            return pid, decision

        tasks = [vote_one(pid, ctx) for pid, ctx in contexts.items()]
        results = await asyncio.gather(*tasks)
        return dict(results)

    def _make_default(self, player_id: int, context: AgentContext = None) -> AgentDecision:
        return AgentDecision(action="pass", target_id=None, internal_thought="Agent缺失。")
