from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import create_tables
from api.game import router as game_router
from api.ws import router as ws_router
from llm.llm_client import LLMClient


app = FastAPI(title="AI 狼人杀")

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
    import sys
    print("", flush=True)
    print("  ========================================", flush=True)
    print("      AI Wolf Game - Backend Started", flush=True)
    print("  ========================================", flush=True)
    cfg = LLMClient()._get_config(None)
    print(f"  LLM Model : {cfg['model']}", flush=True)
    print(f"  LLM Base  : {cfg['base_url']}", flush=True)
    print(f"  API Key   : {cfg['api_key'][:20]}...", flush=True)
    print("", flush=True)
    print("  Testing LLM connection...", flush=True)
    try:
        import asyncio
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=10)
        await asyncio.wait_for(client.models.list(), timeout=10)
        print(f"  [OK] LLM API 连接成功!", flush=True)
    except Exception as e:
        print(f"  [WARN] LLM API 连接测试失败: {e}", flush=True)
        print(f"  [WARN] 所有AI玩家将使用 fallback 回复（不会调用LLM）", flush=True)
    print("  ========================================", flush=True)
    print("", flush=True)


@app.get("/")
async def index():
    return {"message": "AI 狼人杀 API 服务运行中"} 
