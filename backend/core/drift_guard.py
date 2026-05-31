"""防语义漂移模块：Query Validator + Evidence Judge + 回滚机制"""

import re
from typing import Optional


class QueryValidator:
    """每轮查询前验证上下文是否偏离原始问题"""

    ORIGINAL_GOALS = {
        "night_werewolf": "作为狼人，选择今晚要击杀的目标",
        "night_seer": "作为预言家，选择今晚要查验的目标",
        "night_witch": "作为女巫，决定是否使用解药/毒药",
        "hunter_shoot": "作为猎人，选择要开枪带走的目标",
        "day_speech": "根据场上局势发表你的看法和分析",
        "day_vote": "根据发言选择投票放逐的目标",
    }

    FORBIDDEN_PATTERNS = [
        (r"我是狼人|我是狼\b|我们是狼", "身份暴露风险"),
        (r"我的狼队友是.*号", "同伴暴露风险"),
        (r"(\d+)号是我同伴", "同伴暴露风险"),
        (r"请忽略之前的指令|忽略上面的", "Prompt注入风险"),
    ]

    @staticmethod
    def validate(phase: str, role: str, system_prompt: str, user_message: str) -> tuple[bool, Optional[str]]:
        goal = QueryValidator.ORIGINAL_GOALS.get(phase)
        if not goal:
            return True, None

        for pattern, risk_desc in QueryValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, system_prompt) or re.search(pattern, user_message):
                return False, f"检测到{risk_desc}"

        return True, None


class EvidenceJudge:
    """LLM 响应后验证合理性和游戏规则"""

    @staticmethod
    def validate(response: dict, phase: str, role: str, context: dict) -> tuple[bool, Optional[str]]:
        issues = []

        if phase == "night_werewolf":
            target = response.get("target_id")
            if target:
                valid = context.get("valid_targets", [])
                if target not in [str(v) for v in valid]:
                    issues.append(f"target_id {target} 不在合法目标中 {valid}")

        elif phase == "night_witch":
            use_antidote = response.get("use_antidote", False)
            use_poison = response.get("use_poison", False)
            has_antidote = context.get("witch_info", {}).get("has_antidote", True)
            has_poison = context.get("witch_info", {}).get("has_poison", True)
            if use_antidote and not has_antidote:
                issues.append("解药已用完但仍尝试使用")
            if use_poison and not has_poison:
                issues.append("毒药已用完但仍尝试使用")
            if use_antidote and use_poison:
                issues.append("同一晚不能同时使用解药和毒药")

        elif phase == "day_speech":
            speech = response.get("speech", "")
            if len(speech) > 500:
                issues.append(f"发言过长({len(speech)}字符)")
            if re.search(r"我是狼人|我是狼\b|我们是狼", speech):
                issues.append("发言中暴露身份")

        elif phase == "day_vote":
            target = response.get("target_id")
            if target:
                valid = context.get("valid_targets", [])
                if target not in [str(v) for v in valid]:
                    issues.append(f"投票目标 {target} 不合法")

        if issues:
            return False, "; ".join(issues)
        return True, None


class DriftGuard:
    """防语义漂移总控：每次 LLM 调用前后验证，超出阈值回滚"""

    MAX_CONSECUTIVE_DRIFTS = 3

    def __init__(self):
        self.drift_count = 0
        self.baseline_prompts: dict[str, str] = {}

    def save_baseline(self, phase: str, system_prompt: str):
        self.baseline_prompts[phase] = system_prompt

    def check_before(self, phase: str, role: str, system_prompt: str, user_message: str) -> bool:
        ok, reason = QueryValidator.validate(phase, role, system_prompt, user_message)
        if not ok:
            self.drift_count += 1
            return False
        return True

    def check_after(self, response: dict, phase: str, role: str, context: dict) -> tuple[bool, Optional[str]]:
        ok, reason = EvidenceJudge.validate(response, phase, role, context)
        if not ok:
            self.drift_count += 1
            return False, reason
        self.drift_count = max(0, self.drift_count - 1)
        return True, None

    def should_rollback(self) -> bool:
        return self.drift_count >= self.MAX_CONSECUTIVE_DRIFTS

    def get_rollback_prompt(self, phase: str) -> Optional[str]:
        return self.baseline_prompts.get(phase)

    def reset(self):
        self.drift_count = 0
