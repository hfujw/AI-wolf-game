from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import create_tables
from api.game import router as game_router
from api.ws import router as ws_router
from llm.llm_client import LLMClient
from middleware.error_handler import register_exception_handlers
from middleware.logger import logger


app = FastAPI(title="AI 狼人杀")

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game_router, prefix="/api")
app.include_router(ws_router)


@app.on_event("startup")
async def startup():
    await create_tables()
    logger.info("  ========================================")
    logger.info("      AI Wolf Game - Backend Started")
    logger.info("  ========================================")
    cfg = LLMClient()._get_config(None)
    logger.info(f"  LLM Model : {cfg['model']}")
    logger.info(f"  LLM Base  : {cfg['base_url']}")
    logger.info("  Testing LLM connection...")
    try:
        import asyncio
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=10)
        await asyncio.wait_for(client.models.list(), timeout=10)
        logger.info("  [OK] LLM API 连接成功!")
    except Exception as e:
        logger.warning(f"  LLM API 连接测试失败: {e}")
        logger.warning("  所有AI玩家将使用 fallback 回复（不会调用LLM）")
    logger.info("  ========================================")


@app.get("/")
async def index():
    return {"message": "AI 狼人杀 API 服务运行中"} 
