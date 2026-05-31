import json
import logging

from schemas.game_schemas import AgentContext, AgentDecision
from core.react_loop import react_loop, ReActTrace
from core.drift_guard import DriftGuard

logger = logging.getLogger("agent")


class BaseAgent:
    def __init__(self, player_id: int, role: str, personality: str, llm_client=None):
        self.player_id = player_id
        self.role = role
        self.personality = personality
        self.llm_client = llm_client
        self.drift_guard = DriftGuard()

    async def decide(self, context: AgentContext) -> AgentDecision:
        raise NotImplementedError

    async def _decide_with_react(self, context: AgentContext) -> AgentDecision:
        decision, trace = await react_loop(
            phase=context.phase,
            role=self.role,
            context=context,
            decide_fn=self._single_decide,
        )

        if trace.terminated_early:
            self._log_react_trace(context.phase, trace)

        return decision

    async def _single_decide(self, context: AgentContext) -> AgentDecision:
        try:
            if context.phase == "night_werewolf":
                return await self._decide_kill(context)
            elif context.phase == "night_seer":
                return await self._decide_check(context)
            elif context.phase == "night_witch":
                return await self._decide_potion(context)
            elif context.phase == "hunter_shoot":
                return await self._decide_shoot(context)
            elif context.phase == "day_speech":
                return await self._decide_speech(context)
            elif context.phase == "day_vote":
                return await self._decide_vote(context)
            else:
                return AgentDecision(action="pass", internal_thought="等待下一阶段。")
        except Exception as e:
            logger.warning(f"Agent {self.player_id}({self.role}) decide failed: {e}")
            return self.llm_client.get_fallback(context.phase, self.role, context.valid_targets)

    async def _decide_kill(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="kill", target_id=None, internal_thought="未实现")

    async def _decide_check(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="check", target_id=None, internal_thought="未实现")

    async def _decide_potion(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="witch_action", use_antidote=False, use_poison=False)

    async def _decide_shoot(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="shoot", target_id=None, internal_thought="未实现")

    async def _decide_speech(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="speech", speech="过。", internal_thought="未实现")

    async def _decide_vote(self, context: AgentContext) -> AgentDecision:
        return AgentDecision(action="vote", target_id=None, internal_thought="未实现")

    async def _chat(self, messages: list[dict], temperature: float = 0.8) -> dict:
        return await self.llm_client.chat(messages, player_id=self.player_id, temperature=temperature)

    def _build_alive_str(self, context: AgentContext) -> str:
        parts = []
        for p in context.alive_players:
            if p.is_alive:
                parts.append(f"{p.seat_number}号")
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

    def _validate_and_parse(self, context: AgentContext, result: dict, phase: str) -> AgentDecision:
        role = self.role
        context_dict = {
            "valid_targets": context.valid_targets,
            "witch_info": context.witch_info,
        }
        ok, reason = self.drift_guard.check_after(result, phase, role, context_dict)
        if not ok:
            logger.warning(f"EvidenceJudge: 玩家{self.player_id}({role})在{phase}响应异常: {reason}")
            if self.drift_guard.should_rollback():
                logger.warning(f"DriftGuard: 玩家{self.player_id}({role})触发回滚，连续{self.drift_guard.drift_count}次异常")

        return self._parse_target(context, result, result.get("action", phase))

    def _log_react_trace(self, phase: str, trace: ReActTrace):
        steps_desc = "; ".join(
            f"Step{s.step}: Thought={s.thought[:40]}... → {s.action}(target={s.target_id or '无'})"
            for s in trace.steps
        )
        logger.info(f"[ReAct] 玩家{self.player_id}({self.role})在{phase}: {trace.termination_reason} | {steps_desc}")
