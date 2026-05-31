import os

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


DEFAULT_AGENT_CONFIG = {
    "api_key": _env("LLM_API_KEY"),
    "base_url": _env("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
    "model": _env("LLM_MODEL", "GLM-4-Flash"),
}

AGENT_CONFIGS: dict[str, dict] = {}

for i in range(1, 10):
    key = f"player_{i}"
    env_prefix = f"P{i}_"
    cfg = {
        "api_key": _env(f"{env_prefix}API_KEY") or DEFAULT_AGENT_CONFIG["api_key"],
        "base_url": _env(f"{env_prefix}BASE_URL") or DEFAULT_AGENT_CONFIG["base_url"],
        "model": _env(f"{env_prefix}MODEL") or DEFAULT_AGENT_CONFIG["model"],
    }
    if cfg["api_key"] != DEFAULT_AGENT_CONFIG["api_key"] or cfg["base_url"] != DEFAULT_AGENT_CONFIG["base_url"] or cfg["model"] != DEFAULT_AGENT_CONFIG["model"]:
        AGENT_CONFIGS[key] = cfg


class Config:
    DATABASE_URL = "sqlite+aiosqlite:///./data/game.db"

    LLM_TIMEOUT = int(_env("LLM_TIMEOUT", "60"))
    LLM_MAX_RETRIES = int(_env("LLM_MAX_RETRIES", "2"))

    PLAYER_COUNT = 9
    ROLES = ["werewolf", "werewolf", "werewolf", "seer", "witch", "hunter", "villager", "villager", "villager"]
    MAX_ROUNDS = 15
    PERSONALITIES = {
        "werewolf": ["煽动型", "深水倒钩型", "冷静分析型"],
        "seer": ["耿直技术流"],
        "witch": ["高冷掌控型"],
        "hunter": ["暴民领袖型"],
        "villager": ["萌新表水型", "冷静分析型", "暴民领袖型"],
    }
