import asyncio
import re
import random

from openai import AsyncOpenAI
import json_repair

from config import DEFAULT_AGENT_CONFIG, AGENT_CONFIGS, Config
from schemas.game_schemas import AgentDecision
from middleware.logger import logger


class LLMClient:
    def __init__(self):
        self.timeout = Config.LLM_TIMEOUT
        self.max_retries = Config.LLM_MAX_RETRIES
        self._clients: dict[str, AsyncOpenAI] = {}

    def _get_config(self, player_id):
        key = f"player_{player_id}"
        return AGENT_CONFIGS.get(key, DEFAULT_AGENT_CONFIG)

    def _get_client(self, config: dict) -> AsyncOpenAI:
        cache_key = f"{config['api_key'][:16]}|{config['base_url']}"
        if cache_key not in self._clients:
            self._clients[cache_key] = AsyncOpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
                timeout=self.timeout,
            )
        return self._clients[cache_key]

    async def chat(self, messages: list[dict], player_id=None,
                   temperature: float = 0.8) -> dict:
        cfg = self._get_config(player_id)
        client = self._get_client(cfg)
        model = cfg["model"]

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                    ),
                    timeout=45,
                )

                content = response.choices[0].message.content or ""
                reasoning = getattr(response.choices[0].message, 'reasoning_content', "")

                result = self._parse_json(content)
                if reasoning:
                    result['reasoning'] = reasoning
                if not result or (len(result) == 1 and 'reasoning' in result):
                    result['internal_thought'] = content[:500]
                return result

            except asyncio.TimeoutError:
                last_error = "LLM request timed out"
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{self.max_retries + 1})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM error (attempt {attempt + 1}/{self.max_retries + 1}): {e}")

            if attempt < self.max_retries:
                wait = 2 ** attempt
                await asyncio.sleep(wait)

        logger.error(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")
        raise Exception(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

    def _parse_json(self, content: str) -> dict:
        """使用 json_repair 鲁棒解析 LLM 返回的 JSON"""
        try:
            return json_repair.loads(content)
        except Exception:
            pass

        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json_repair.loads(json_match.group())
            except Exception:
                pass

        if not content.strip():
            return {"speech": "过。", "internal_thought": "无内容"}

        return {"speech": content.strip(), "internal_thought": content[:500]}

    def get_fallback(self, phase: str, role: str, valid_targets: list = None) -> AgentDecision:
        if valid_targets is None:
            valid_targets = []

        logger.warning(f"使用 FALLBACK for {role} in {phase} (LLM API call failed)")

        FALLBACK_SPEECHES = {
            "werewolf": [
                "我觉得前面几位的发言挺有意思的，4号的话里有点矛盾，大家可以注意一下。",
                "听了一圈，我感觉3号的发言逻辑不太通，我虽然是好人，但我建议大家多关注一下3号。",
                "这一轮信息还不多，大家可以不急着出人，多听听后面的发言再做决定。",
            ],
            "seer": [
                "我是预言家，昨晚验了一个人，但因为一些原因我现在先不说结果，请大家相信我。",
                "现在我报不了信息，但下一轮我会报出来的，请给我一点时间。",
            ],
            "witch": [
                "我觉得前面的发言都还行，我目前站边不明，大家再多分析分析吧。",
                "我暂时不跳身份，但我认为大家的发言里面有一些值得深挖的地方。",
            ],
            "villager": [
                "我是平民，听了大家的发言，我觉得2号和4号里面可能有问题。",
                "这一轮我倾向于先不出人，多观察一轮。",
                "我觉得3号最可疑，他的发言一直在回避关键问题。",
                "我是村民，表水完毕。我会把票投给最可疑的人。",
            ],
        }

        speeches = FALLBACK_SPEECHES.get(role, FALLBACK_SPEECHES["villager"])

        if phase == "night_werewolf":
            target_id = str(random.choice(valid_targets)) if valid_targets else None
            return AgentDecision(action="kill", target_id=target_id, internal_thought="LLM调用暂不可用，使用备用策略选择目标。")
        elif phase == "night_seer":
            target_id = str(random.choice(valid_targets)) if valid_targets else None
            return AgentDecision(action="check", target_id=target_id, internal_thought="LLM调用暂不可用，使用备用策略选择查验目标。")
        elif phase == "night_witch":
            return AgentDecision(action="witch_action", use_antidote=True, use_poison=False, poison_target=None, internal_thought="LLM调用暂不可用，默认使用解药救人。")
        elif phase == "day_speech":
            return AgentDecision(action="speech", speech=random.choice(speeches), internal_thought="LLM调用暂不可用，使用备用发言模板。")
        elif phase == "day_vote":
            target_id = str(random.choice(valid_targets)) if valid_targets else None
            return AgentDecision(action="vote", target_id=target_id, internal_thought="LLM调用暂不可用，使用备用投票策略。")
        else:
            return AgentDecision(action="pass", internal_thought="No action available.")
