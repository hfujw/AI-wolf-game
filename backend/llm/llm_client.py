import asyncio
import json
import random
import re

from openai import AsyncOpenAI

from config import DEFAULT_AGENT_CONFIG, AGENT_CONFIGS, Config
from schemas.game_schemas import AgentDecision


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
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
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
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))

        raise Exception(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

    def _parse_json(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        result: dict = {}
        for key, pattern in [
            ("target_id", r'"target_id"\s*:\s*"?(\d+)"?'),
            ("speech", r'"speech"\s*:\s*"(.*?)"(?:\s*,|\s*\}|\s*$)',),
            ("content", r'"content"\s*:\s*"(.*?)"(?:\s*,|\s*\}|\s*$)'),
            ("internal_thought", r'"internal_thought"\s*:\s*"(.*?)"(?:\s*,|\s*\}|\s*$)'),
            ("action", r'"action"\s*:\s*"([^"]*)"'),
        ]:
            m = re.search(pattern, content, re.DOTALL)
            if m:
                result[key] = m.group(1)

        for key, pattern in [
            ("use_antidote", r'"use_antidote"\s*:\s*(true|false)'),
            ("use_poison", r'"use_poison"\s*:\s*(true|false)'),
        ]:
            m = re.search(pattern, content)
            if m:
                result[key] = m.group(1) == "true"

        m = re.search(r'"poison_target"\s*:\s*"?(\d+)"?', content)
        if m:
            result["poison_target"] = m.group(1)

        if "content" in result and "speech" not in result:
            result["speech"] = result["content"]

        if not result:
            result["speech"] = content.strip()

        return result

    def get_fallback(self, phase: str, role: str, valid_targets: list = None) -> AgentDecision:
        if valid_targets is None:
            valid_targets = []

        import logging
        logging.getLogger('llm_client').warning(f"⚠️ Using FALLBACK for {role} in {phase} (LLM API call failed)")

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
            return AgentDecision(action="kill", target_id=target_id, internal_thought="Fallback: random target.")
        elif phase == "night_seer":
            target_id = str(random.choice(valid_targets)) if valid_targets else None
            return AgentDecision(action="check", target_id=target_id, internal_thought="Fallback: random target.")
        elif phase == "night_witch":
            return AgentDecision(action="witch_action", use_antidote=True, use_poison=False, poison_target=None, internal_thought="Fallback: using antidote as default.")
        elif phase == "day_speech":
            return AgentDecision(action="speech", speech=random.choice(speeches), internal_thought="Fallback: random speech.")
        elif phase == "day_vote":
            target_id = str(random.choice(valid_targets)) if valid_targets else None
            return AgentDecision(action="vote", target_id=target_id, internal_thought="Fallback: random vote.")
        else:
            return AgentDecision(action="pass", internal_thought="No action available.")
