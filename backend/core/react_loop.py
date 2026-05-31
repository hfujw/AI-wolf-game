"""ReAct 循环：Thought → Action → Observation 模式

核心设计：
1. Thought: LLM 分析当前局势，输出推理过程（internal_thought）
2. Action: LLM 选择具体行动（target_id, speech, vote, etc.）
3. Observation: 验证行动合法性并记录结果

终止条件：
- LLM 自行声明 "final_answer"（主动结束）
- 达到步数上限（MAX_STEPS = 3）
- 连续重复动作检测（连续2次相同 target_id）
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional

from schemas.game_schemas import AgentDecision, AgentContext


MAX_STEPS = 3
MAX_REPEAT_ACTIONS = 2


@dataclass
class ReActStep:
    step: int
    thought: str
    action: str
    target_id: Optional[str]
    observation: str
    is_final: bool = False


@dataclass
class ReActTrace:
    steps: list[ReActStep] = field(default_factory=list)
    final_decision: Optional[AgentDecision] = None
    terminated_early: bool = False
    termination_reason: str = ""


async def react_loop(
    phase: str,
    role: str,
    context: AgentContext,
    decide_fn: Callable[[AgentContext], Awaitable[AgentDecision]],
    max_steps: int = MAX_STEPS,
) -> tuple[AgentDecision, ReActTrace]:
    """执行 ReAct 循环：Thought → Action → Observation

    Args:
        phase: 当前阶段
        role: 玩家角色
        context: 上下文
        decide_fn: 决策函数（异步，接收 context 返回 AgentDecision）
        max_steps: 最大步数

    Returns:
        (最终决策, ReAct追踪记录)
    """
    trace = ReActTrace()
    last_target: Optional[str] = None
    repeat_count = 0

    for step in range(1, max_steps + 1):
        decision = await decide_fn(context)

        thought = decision.internal_thought or "(无推理)"
        action = decision.action
        target_id = decision.target_id

        if decision.action == "final_answer" or decision.action == "stop":
            trace.steps.append(ReActStep(
                step=step, thought=thought, action="stop",
                target_id=None, observation="模型主动结束决策过程", is_final=True,
            ))
            trace.final_decision = decision
            trace.terminated_early = True
            trace.termination_reason = "模型主动结束"
            return decision, trace

        if target_id and target_id == last_target:
            repeat_count += 1
        else:
            repeat_count = 0
            last_target = target_id

        if repeat_count >= MAX_REPEAT_ACTIONS:
            obs = f"连续 {repeat_count} 次选择相同目标，强制终止循环"
            trace.steps.append(ReActStep(
                step=step, thought=thought, action=action,
                target_id=target_id, observation=obs, is_final=True,
            ))
            trace.final_decision = decision
            trace.terminated_early = True
            trace.termination_reason = f"重复动作检测: 连续{repeat_count}次 target_id={target_id}"
            return decision, trace

        obs = f"动作: {action}, 目标: {target_id or '无'}"
        trace.steps.append(ReActStep(
            step=step, thought=thought, action=action,
            target_id=target_id, observation=obs, is_final=(step == max_steps),
        ))

        if step == max_steps:
            trace.termination_reason = f"达到步数上限 {max_steps}"
            break

    trace.final_decision = decision
    return decision, trace
