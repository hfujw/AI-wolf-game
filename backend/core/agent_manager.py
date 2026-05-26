import asyncio
import random

from agents.base_agent import BaseAgent
from schemas.game_schemas import AgentContext, AgentDecision


class AgentManager:
    def __init__(self, agents: dict[int, BaseAgent]):
        self.agents = agents

    async def ask_wolves(self, wolf_ids: list[int], contexts: dict[int, AgentContext]) -> tuple[str | None, list[AgentDecision]]:
        async def ask_one(wid: int) -> AgentDecision:
            if wid not in self.agents or wid not in contexts:
                return AgentDecision(action="kill", target_id=None, internal_thought="不在场。")
            try:
                return await asyncio.wait_for(
                    self.agents[wid].decide(contexts[wid]), timeout=30
                )
            except asyncio.TimeoutError:
                ctx = contexts.get(wid)
                valid = ctx.valid_targets if ctx else []
                return AgentDecision(
                    action="kill",
                    target_id=str(random.choice(valid)) if valid else None,
                    internal_thought="超时，随机选择目标。",
                )
            except Exception as e:
                ctx = contexts.get(wid)
                valid = ctx.valid_targets if ctx else []
                return AgentDecision(
                    action="kill",
                    target_id=str(random.choice(valid)) if valid else None,
                    internal_thought=f"异常({e})，随机选择。",
                )

        tasks = [ask_one(wid) for wid in wolf_ids]
        decisions = await asyncio.gather(*tasks)

        valid_decisions = [d for d in decisions if d.target_id is not None]
        if valid_decisions:
            chosen = random.choice(valid_decisions)
            return chosen.target_id, decisions
        return None, decisions

    async def ask_seer(self, seer_id: int, context: AgentContext) -> AgentDecision:
        if seer_id not in self.agents:
            return AgentDecision(action="check", target_id=None, internal_thought="预言家不在场。")
        try:
            return await asyncio.wait_for(
                self.agents[seer_id].decide(context), timeout=30
            )
        except asyncio.TimeoutError:
            target = str(random.choice(context.valid_targets)) if context.valid_targets else None
            return AgentDecision(action="check", target_id=target, internal_thought="超时，随机查验。")
        except Exception as e:
            target = str(random.choice(context.valid_targets)) if context.valid_targets else None
            return AgentDecision(action="check", target_id=target, internal_thought=f"异常({e})，随机查验。")

    async def ask_witch(self, witch_id: int, context: AgentContext) -> AgentDecision:
        if witch_id not in self.agents:
            return AgentDecision(action="witch_action", use_antidote=False, use_poison=False, internal_thought="女巫不在场。")
        try:
            return await asyncio.wait_for(
                self.agents[witch_id].decide(context), timeout=30
            )
        except asyncio.TimeoutError:
            return AgentDecision(action="witch_action", use_antidote=False, use_poison=False, internal_thought="超时，不使用药水。")
        except Exception as e:
            return AgentDecision(action="witch_action", use_antidote=False, use_poison=False, internal_thought=f"异常({e})，不使用药水。")

    async def ask_hunter(self, hunter_id: int, context: AgentContext) -> AgentDecision:
        if hunter_id not in self.agents:
            return AgentDecision(action="shoot", target_id=None, internal_thought="猎人不在场。")
        try:
            return await asyncio.wait_for(
                self.agents[hunter_id].decide(context), timeout=30
            )
        except asyncio.TimeoutError:
            target = str(random.choice(context.valid_targets)) if context.valid_targets else None
            return AgentDecision(action="shoot", target_id=target, internal_thought="超时，随机开枪。")
        except Exception as e:
            target = str(random.choice(context.valid_targets)) if context.valid_targets else None
            return AgentDecision(action="shoot", target_id=target, internal_thought=f"异常({e})，随机开枪。")

    async def ask_speech(self, player_id: int, context: AgentContext) -> AgentDecision:
        if player_id not in self.agents:
            return AgentDecision(action="speech", speech="我是好人，过。", internal_thought="不在场。")
        try:
            return await asyncio.wait_for(
                self.agents[player_id].decide(context), timeout=30
            )
        except asyncio.TimeoutError:
            return AgentDecision(action="speech", speech="我还没想好，过。", internal_thought="超时。")
        except Exception as e:
            return AgentDecision(action="speech", speech=f"异常: {e}", internal_thought="出错。")

    async def ask_votes(self, contexts: dict[int, AgentContext]) -> dict[int, AgentDecision]:
        async def vote_one(pid: int, ctx: AgentContext) -> tuple[int, AgentDecision]:
            if pid not in self.agents:
                return pid, AgentDecision(action="vote", target_id=None, internal_thought="不在场。")
            try:
                decision = await asyncio.wait_for(self.agents[pid].decide(ctx), timeout=20)
                return pid, decision
            except asyncio.TimeoutError:
                return pid, AgentDecision(action="vote", target_id=None, internal_thought="超时，弃权。")
            except Exception as e:
                return pid, AgentDecision(action="vote", target_id=None, internal_thought=f"异常({e})，弃权。")

        tasks = [vote_one(pid, ctx) for pid, ctx in contexts.items()]
        results = await asyncio.gather(*tasks)
        return dict(results)
