"""结构化日志配置"""
import sys
from pathlib import Path
from loguru import logger

_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs"
_LOG_PATH.mkdir(parents=True, exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

logger.add(
    _LOG_PATH / "game_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
)
