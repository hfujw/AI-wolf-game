# AI狼人杀项目全面优化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 对AI狼人杀项目进行中度重构+UI重设计，拆大文件、消重复、加三层架构、全局异常/日志、暗黑剧场风UI

**Architecture:** 后端FastAPI+SQLAlchemy Async+loguru；前端React18+TS+Vite+Framer Motion+CSS Module。拆分臃肿文件为职责单一模块，引入repository模式分离数据访问

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy Async, loguru, Pydantic; React 18, TypeScript 5, Vite 5, Framer Motion, CSS Module

---

## Phase 1: 后端基础设施

### Task 1.1: 安装loguru并创建日志中间件

**Files:**
- Create: `backend/middleware/__init__.py`
- Create: `backend/middleware/logger.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加loguru依赖**

```txt
# backend/requirements.txt 追加
loguru>=0.7.0
json-repair>=0.25.0
```

- [ ] **Step 2: 创建日志配置**

```python
# backend/middleware/__init__.py
```

```python
# backend/middleware/logger.py
"""结构化日志配置"""
import sys
from pathlib import Path
from loguru import logger

_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs"
_LOG_PATH.mkdir(parents=True, exist_ok=True)

# 移除默认handler
logger.remove()

# 控制台输出（彩色）
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 文件输出（完整信息）
logger.add(
    _LOG_PATH / "game_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    compression="gz",
)
```

- [ ] **Step 3: Commit**

```bash
cd "C:\Users\22075\Desktop\AI-wolf-game-main"
git add backend/middleware/ backend/requirements.txt
git commit -m "feat: add loguru logger middleware"
```

### Task 1.2: 创建全局异常处理中间件

**Files:**
- Create: `backend/middleware/error_handler.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建异常处理器**

```python
# backend/middleware/error_handler.py
"""全局异常处理"""
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from middleware.logger import logger


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": f"HTTP_{exc.status_code}"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning(f"Validation error: {errors} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"detail": "请求参数校验失败", "error_code": "VALIDATION_ERROR", "errors": errors},
    )


async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc} | {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "error_code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app):
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
```

- [ ] **Step 2: 在main.py中注册**

修改 `backend/main.py`，在 `app = FastAPI(...)` 之后添加：

```python
from middleware.error_handler import register_exception_handlers

app = FastAPI(title="AI 狼人杀")

register_exception_handlers(app)  # 注册全局异常处理
```

- [ ] **Step 3: Commit**

```bash
git add backend/middleware/error_handler.py backend/main.py
git commit -m "feat: add global exception handler middleware"
```

### Task 1.3: 安全修复 — 移除硬编码API Key

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: 移除明文Key**

将 `backend/config.py` 第13行修改为：

```python
DEFAULT_AGENT_CONFIG = {
    "api_key": _env("LLM_API_KEY"),  # 必须从.env读取
    "base_url": _env("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
    "model": _env("LLM_MODEL", "GLM-4-Flash"),
}
```

注意：去掉默认的明文API Key，如果 `LLM_API_KEY` 未设置则 `api_key` 为空字符串，启动时LLM连通性检查会失败并提示。

- [ ] **Step 2: Commit**

```bash
git add backend/config.py
git commit -m "fix: remove hardcoded API key from config.py"
```

### Task 1.4: LLM Client JSON解析优化

**Files:**
- Modify: `backend/llm/llm_client.py`

- [ ] **Step 1: 用json_repair替代手写正则解析**

修改 `_parse_json` 方法：

```python
import json_repair

def _parse_json(self, content: str) -> dict:
    """使用json_repair鲁棒解析LLM返回的JSON"""
    try:
        return json_repair.loads(content)
    except Exception:
        pass

    # fallback: 提取第一个JSON对象
    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json_repair.loads(json_match.group())
        except Exception:
            pass

    # 最终fallback：将content作为speech
    return {"speech": content.strip(), "internal_thought": content[:500]}
```

- [ ] **Step 2: 替换所有print为logger**

在 `backend/llm/llm_client.py` 顶部添加：
```python
from middleware.logger import logger
```

将 `get_fallback` 方法中的 `logging.getLogger` 替换为 `logger.warning(...)`。

- [ ] **Step 3: Commit**

```bash
git add backend/llm/llm_client.py
git commit -m "refactor: use json_repair for LLM response parsing"
```

---

## Phase 2: 后端重构 — 拆分engine.py

### Task 2.1: 独立StatsTracker

**Files:**
- Create: `backend/core/stats_tracker.py`
- Modify: `backend/core/engine.py`

- [ ] **Step 1: 创建stats_tracker.py**

```python
# backend/core/stats_tracker.py
"""MVP/SVP 统计追踪器"""


class StatsTracker:
    def __init__(self):
        self.player_stats: dict[int, dict] = {}
        self.vote_records: list[dict] = []
        self.role_recognitions: list[dict] = []
        self.ability_uses: list[dict] = []
        self.speech_counts: dict[int, int] = {}

    def init_player(self, player_id: int, role: str):
        self.player_stats[player_id] = {
            "role": role, "score": 0, "votes_correct": 0,
            "votes_total": 0, "speeches": 0, "skill_uses": 0, "survived_rounds": 0,
        }
        self.speech_counts[player_id] = 0

    def record_speech(self, player_id: int):
        if player_id in self.player_stats:
            self.player_stats[player_id]["speeches"] += 1
        self.speech_counts[player_id] = self.speech_counts.get(player_id, 0) + 1

    def record_vote(self, voter_id: int, target_id: int | None, target_role: str | None, voter_role: str):
        is_correct = False
        if target_role:
            if voter_role == "werewolf" and target_role != "werewolf":
                is_correct = True
            elif voter_role != "werewolf" and target_role == "werewolf":
                is_correct = True
        self.vote_records.append({
            "voter_id": voter_id, "target_id": target_id,
            "target_role": target_role, "voter_role": voter_role, "is_correct": is_correct,
        })
        if voter_id in self.player_stats:
            self.player_stats[voter_id]["votes_total"] += 1
            if is_correct:
                self.player_stats[voter_id]["votes_correct"] += 1

    def record_ability_use(self, player_id: int, ability: str):
        self.ability_uses.append({"player_id": player_id, "ability": ability, "target_id": None, "success": True})
        if player_id in self.player_stats:
            self.player_stats[player_id]["skill_uses"] += 1

    def record_survival(self, player_id: int):
        if player_id in self.player_stats:
            self.player_stats[player_id]["survived_rounds"] += 1

    def calc_mvp_svp(self, winner: str) -> tuple[dict | None, dict | None]:
        if winner == "draw":
            return None, None
        for pid, stats in self.player_stats.items():
            score = 0
            role = stats["role"]
            is_winner = (winner == "werewolves" and role == "werewolf") or \
                        (winner == "villagers" and role != "werewolf")
            if is_winner:
                score += 20
            if stats["votes_total"] > 0:
                accuracy = stats["votes_correct"] / stats["votes_total"]
                score += int(accuracy * 10)
            score += min(stats["skill_uses"] * 4, 12)
            score += min(stats["speeches"], 5)
            stats["score"] = score

        winners = [(pid, s) for pid, s in self.player_stats.items()
                    if (winner == "werewolves" and s["role"] == "werewolf") or
                       (winner == "villagers" and s["role"] != "werewolf")]
        losers = [(pid, s) for pid, s in self.player_stats.items() if (pid, s) not in winners]
        mvp = max(winners, key=lambda x: x[1]["score"]) if winners else None
        svp = max(losers, key=lambda x: x[1]["score"]) if losers else None
        return mvp, svp
```

- [ ] **Step 2: 修改engine.py导入**

在 `backend/core/engine.py` 中：
1. 删除 `class StatsTracker` 整个类定义（第18-99行）
2. 添加导入：`from core.stats_tracker import StatsTracker`

- [ ] **Step 3: 验证导入正确**

```bash
cd "C:\Users\22075\Desktop\AI-wolf-game-main\backend"
python -c "from core.stats_tracker import StatsTracker; s=StatsTracker(); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/core/stats_tracker.py backend/core/engine.py
git commit -m "refactor: extract StatsTracker to separate module"
```

### Task 2.2: 拆分夜晚阶段为 night_phase.py

**Files:**
- Create: `backend/core/night_phase.py`
- Modify: `backend/core/engine.py`

- [ ] **Step 1: 创建night_phase.py**

从 `engine.py` 中提取以下方法到 `night_phase.py`：
- `_wolf_action`
- `_seer_action`
- `_witch_action`
- `_resolve_night_deaths`
- `_apply_deaths`
- `_trigger_hunter_shoot`（night trigger部分）
- `_announce_deaths`
- `_log_god_view_start`

```python
# backend/core/night_phase.py
"""夜晚阶段：狼人/预言家/女巫行动"""
import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from models.game import Game
from models.game_player import GamePlayer
from models.game_event import GameEvent
from core.stats_tracker import StatsTracker
from memory.memory_manager import MemoryManager, Memory
from db.database import async_session
from config import Config
from middleware.logger import logger


class NightPhase:
    def __init__(self, game: Game, players: list[GamePlayer], agent_manager, memory: Memory, stats: StatsTracker):
        self.game = game
        self.players = players
        self.agent_manager = agent_manager
        self.memory = memory
        self.stats = stats
        self.log_fn = None  # 由engine注入

    def set_log(self, log_fn):
        self.log_fn = log_fn

    def log(self, msg: str):
        if self.log_fn:
            self.log_fn(msg)

    async def wolf_action(self, round_number: int) -> int | None:
        """狼人选击杀目标"""
        wolf_players = [p for p in self.players if p.role == "werewolf" and p.is_alive]
        if not wolf_players:
            self.log("狼人全灭，跳过")
            return None
        # ... (从engine.py原样搬入_wolf_action的全部逻辑)
        pass  # 占位，实际搬运完整代码

    async def seer_action(self, round_number: int) -> dict:
        """预言家查验"""
        # ... (从engine.py原样搬入_seer_action)
        pass

    async def witch_action(self, round_number: int, wolf_target_id) -> "AgentDecision":
        """女巫用药"""
        # ... (从engine.py原样搬入_witch_action)
        pass

    def resolve_deaths(self, wolf_target_id, witch_decision, witch_has_antidote, witch_has_poison, hunter_can_shoot):
        """计算夜晚死亡"""
        # ... (从engine.py原样搬入_resolve_night_deaths)
        pass

    async def apply_deaths(self, deaths: list[int]):
        """应用死亡"""
        # ... (从engine.py原样搬入_apply_deaths)
        pass
```

**注意**：完整代码搬运自 engine.py，每个方法保留原有逻辑，只是从 `self.xxx` 改为通过构造函数传入的引用。

- [ ] **Step 2: 修改engine.py**

1. 删除已搬出的方法
2. 添加导入：`from core.night_phase import NightPhase`
3. 在 `__init__` 中创建 `self.night = NightPhase(game, players, agent_manager, memory, stats)`
4. 在 `night_phase` 方法中通过 `self.night.xxx()` 调用

- [ ] **Step 3: Commit**

```bash
git add backend/core/night_phase.py backend/core/engine.py
git commit -m "refactor: extract night phase logic to separate module"
```

### Task 2.3: 拆分白天阶段为 day_phase.py

**Files:**
- Create: `backend/core/day_phase.py`
- Modify: `backend/core/engine.py`

- [ ] **Step 1: 创建day_phase.py**

从 `engine.py` 中提取 `day_phase` 及其子逻辑（发言、投票、放逐）到 `day_phase.py`。

- [ ] **Step 2: 修改engine.py**

同样模式：删除搬出方法，添加 `DayPhase` 类引用。

- [ ] **Step 3: Commit**

```bash
git add backend/core/day_phase.py backend/core/engine.py
git commit -m "refactor: extract day phase logic to separate module"
```

### Task 2.4: 引入Repository层

**Files:**
- Create: `backend/repositories/__init__.py`
- Create: `backend/repositories/game_repo.py`
- Create: `backend/repositories/player_repo.py`
- Create: `backend/repositories/event_repo.py`
- Modify: `backend/services/game_service.py`
- Modify: `backend/api/game.py`

- [ ] **Step 1: 创建game_repo.py**

```python
# backend/repositories/game_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.game import Game


class GameRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, game_id: int) -> Game | None:
        result = await self.db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one_or_none()

    async def create(self, game: Game) -> Game:
        self.db.add(game)
        await self.db.flush()
        await self.db.refresh(game)
        return game

    async def update(self, game: Game) -> Game:
        await self.db.merge(game)
        await self.db.commit()
        return game
```

- [ ] **Step 2: 创建player_repo.py**（类似模式）
- [ ] **Step 3: 创建event_repo.py**（类似模式）

- [ ] **Step 4: 更新game_service.py使用repository**

将直接的 `db.execute(select(Game)...)` 替换为 `GameRepo(db).get_by_id(...)`。

- [ ] **Step 5: Commit**

```bash
git add backend/repositories/ backend/services/game_service.py backend/api/game.py
git commit -m "refactor: introduce repository pattern for data access"
```

### Task 2.5: 消除API层重复代码

**Files:**
- Modify: `backend/api/game.py`

- [ ] **Step 1: 提取公共函数**

在 `backend/api/game.py` 中添加：

```python
async def _get_game_with_data(game_id: int, db: AsyncSession) -> tuple[Game, list[GamePlayer], list[GameEvent]]:
    """三个端点的公共查询逻辑"""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="对局不存在")

    player_result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id)
    )
    players = list(player_result.scalars().all())

    event_result = await db.execute(
        select(GameEvent).where(GameEvent.game_id == game_id).order_by(GameEvent.id)
    )
    events = list(event_result.scalars().all())

    return game, players, events


def _build_player_map(players: list[GamePlayer]) -> dict[int, GamePlayer]:
    return {p.id: p for p in players}


def _events_to_replay_events(events: list[GameEvent], player_map: dict[int, GamePlayer]) -> list[ReplayEvent]:
    return [
        ReplayEvent(
            round_number=e.round_number, phase=e.phase, player_id=e.player_id,
            player_name=player_map[e.player_id].player_name if e.player_id and e.player_id in player_map else None,
            event_type=e.event_type, public_content=e.public_content,
            private_content=e.private_content, internal_thought=e.internal_thought,
            reasoning_content=e.reasoning_content,
        )
        for e in events
    ]
```

然后简化 `/replay`、`/events`、`/debug` 三个端点使用这些公共函数。

- [ ] **Step 2: Commit**

```bash
git add backend/api/game.py
git commit -m "refactor: eliminate duplicated query logic in API layer"
```

### Task 2.6: 全局替换print为logger

**Files:**
- Modify: `backend/core/engine.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 批量替换**

在 `engine.py` 和 `main.py` 中：
- 将所有 `print(..., flush=True)` 替换为 `logger.info(...)`
- 将所有 `traceback.print_exc()` 替换为 `logger.exception(...)`

```python
# 搜索替换模式
# print(f"...", flush=True) → logger.info("...")
# print("...", flush=True)  → logger.info("...")
# traceback.print_exc()     → logger.exception("...")
```

- [ ] **Step 2: Commit**

```bash
git add backend/
git commit -m "refactor: replace print with loguru logger globally"
```

---

## Phase 3: 前端重构

### Task 3.1: 安装CSS Module支持

**Files:**
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Vite原生支持CSS Module，无需额外配置。** 确认 `*.module.css` 文件可使用。

无代码变更，直接commit标记。

```bash
git commit --allow-empty -m "chore: confirm CSS Module support in Vite"
```

### Task 3.2: 拆分GamePage — 状态管理hook

**Files:**
- Create: `frontend/src/pages/GamePage/`
- Create: `frontend/src/pages/GamePage/useGameState.ts`
- Create: `frontend/src/pages/GamePage/useWSEventHandler.ts`
- Create: `frontend/src/pages/GamePage/usePhaseTransition.ts`
- Create: `frontend/src/pages/GamePage/GameLayout.tsx`
- Create: `frontend/src/pages/GamePage/GameLayout.module.css`
- Modify: `frontend/src/pages/GamePage.tsx`

- [ ] **Step 1: 创建useGameState.ts**

```typescript
// frontend/src/pages/GamePage/useGameState.ts
import { useState, useRef, useCallback } from 'react';
import type { GameStatus, Player } from '../../types';
import { api } from '../../services/api';

interface GameState {
  game_id: number;
  phase: string;
  round_number: number;
  winner: string | null;
  players: Player[];
  events: GameEvent[];
  current_speaker_id: number | null;
}

interface LogEntry {
  id: number;
  type: 'system' | 'death' | 'action' | 'speech' | 'narrator';
  text: string;
  timestamp: number;
}

interface ChatItem {
  id: string;
  text: string;
  speaker: string;
  type: 'speech' | 'thought' | 'system';
  typing?: boolean;
}

function mapGameStatus(raw: GameStatus): GameState {
  const players: Player[] = (raw.alive_players || []).map(p => ({
    id: p.id, player_name: p.name || '', seat_number: p.seat_number,
    role: p.role || '', personality: (p as any).personality || '', is_alive: p.is_alive,
  }));
  const events: GameEvent[] = (raw.events || []).map(e => ({
    event_type: e.event_type, player_id: e.player_id ?? 0,
    role: (e as any).role || '', content: e.public_content || '',
    phase: e.phase, round_number: e.round_number,
  }));
  return {
    game_id: raw.game_id, phase: raw.phase, round_number: raw.round_number,
    winner: raw.winner, players, events, current_speaker_id: (raw as any).current_speaker_id ?? null,
  };
}

function buildLogs(events: GameEvent[], players: Player[]): LogEntry[] {
  const seatMap = new Map<number, number>();
  players.forEach(p => seatMap.set(p.id, p.seat_number));
  return events.map((e, i) => {
    const seat = seatMap.get(e.player_id);
    const seatStr = seat ? `${seat}号` : '';
    let type: LogEntry['type'] = 'system';
    let text = e.content || e.event_type;
    if (e.event_type === 'death') type = 'death';
    else if (e.event_type === 'action') { type = 'action'; text = `${seatStr} ${e.content}`; }
    else if (e.event_type === 'speech') type = 'speech';
    return { id: i, type, text, timestamp: Date.now() };
  });
}

export function useGameState(gameId: number) {
  const [status, setStatus] = useState<GameState | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [thinkingPlayers, setThinkingPlayers] = useState<Set<number>>(new Set());
  const statusRef = useRef<GameState | null>(null);
  const chatIdRef = useRef(0);
  const processedChatSet = useRef<Set<string>>(new Set());

  const fetchAndSetStatus = useCallback(async (gameId: number) => {
    const res = await api.getGameStatus(gameId);
    if (!res) return;
    const data = mapGameStatus(res);
    statusRef.current = data;
    setStatus(data);
    const newLogs = buildLogs(data.events || [], data.players || []);
    setLogs(newLogs);
  }, []);

  const addSystemChat = useCallback((text: string) => {
    chatIdRef.current++;
    const item: ChatItem = { id: `sys-${chatIdRef.current}`, text, speaker: '', type: 'system', typing: false };
    setChatItems(prev => [...prev, item]);
  }, []);

  const addSpeechChat = useCallback((playerName: string, text: string) => {
    const speechKey = `${playerName}_${text}`;
    if (processedChatSet.current.has(speechKey)) return;
    processedChatSet.current.add(speechKey);
    chatIdRef.current++;
    const chatId = `speech-${chatIdRef.current}`;
    const item: ChatItem = { id: chatId, text, speaker: playerName, type: 'speech', typing: true };
    setChatItems(prev => [...prev, item]);
    const typingDuration = Math.min(text.length * 60, 4000);
    setTimeout(() => {
      setChatItems(prev => prev.map(c => c.id === chatId ? { ...c, typing: false } : c));
    }, typingDuration);
  }, []);

  const addThoughtChat = useCallback((playerName: string, thought: string, key: string) => {
    if (processedChatSet.current.has(key)) return;
    processedChatSet.current.add(key);
    chatIdRef.current++;
    const item: ChatItem = { id: `thought-${chatIdRef.current}`, text: thought, speaker: playerName, type: 'thought', typing: false };
    setChatItems(prev => [...prev, item]);
  }, []);

  const setThinking = useCallback((pid: number) => {
    setThinkingPlayers(prev => new Set(prev).add(pid));
  }, []);

  const clearThinking = useCallback((pid: number) => {
    setThinkingPlayers(prev => {
      const next = new Set(prev);
      next.delete(pid);
      return next;
    });
  }, []);

  const clearAllThinking = useCallback(() => {
    setThinkingPlayers(new Set());
  }, []);

  return {
    status, setStatus, logs, setLogs, chatItems, setChatItems,
    thinkingPlayers, setThinkingPlayers, statusRef, chatIdRef, processedChatSet,
    fetchAndSetStatus, addSystemChat, addSpeechChat, addThoughtChat,
    setThinking, clearThinking, clearAllThinking,
  };
}

export { mapGameStatus, buildLogs };
export type { GameState, LogEntry, ChatItem };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GamePage/
git commit -m "refactor: extract game state management hook from GamePage"
```

### Task 3.3: 拆分GamePage — WebSocket事件处理

**Files:**
- Modify: `frontend/src/pages/GamePage/useWSEventHandler.ts`

内容：从GamePage中提取 `handleWSEvent` 函数体为独立hook。依赖 `useGameState` 返回值。

(代码约200行，完整搬运逻辑)

- [ ] **Commit**

### Task 3.4: 拆分GamePage — 阶段切换hook

**Files:**
- Create: `frontend/src/pages/GamePage/usePhaseTransition.ts`

```typescript
// frontend/src/pages/GamePage/usePhaseTransition.ts
import { useRef, useEffect } from 'react';
import { playNightSound, playDawnSound, playVoteTicking, playVictorySound, playDefeatSound } from '../../utils/sound';

export function usePhaseTransition(
  phase: string | undefined,
  winner: string | null | undefined,
  onPhaseChange?: (prevPhase: string, newPhase: string) => void,
) {
  const prevPhaseRef = useRef<string>('');
  const isFirstRef = useRef(true);

  useEffect(() => {
    if (!phase) return;
    if (isFirstRef.current) {
      isFirstRef.current = false;
      prevPhaseRef.current = phase;
      return;
    }
    const prev = prevPhaseRef.current;
    if (phase === prev) return;

    // 音效触发
    const oldWasNight = prev?.startsWith('night');
    const newIsDay = phase?.startsWith('day');
    if (oldWasNight && newIsDay) playDawnSound();
    const newIsNight = phase?.startsWith('night');
    if (newIsNight && !prev?.startsWith('night')) playNightSound();
    if (phase === 'day_vote') playVoteTicking();

    const isNowFinished = phase === 'finished' || phase === 'game_over' || !!winner;
    if (isNowFinished) {
      const isWolfWin = winner === 'werewolves';
      if (isWolfWin) playVictorySound();
      else playDefeatSound();
    }

    onPhaseChange?.(prev, phase);
    prevPhaseRef.current = phase;
  }, [phase, winner, onPhaseChange]);

  return { prevPhase: prevPhaseRef.current };
}
```

- [ ] **Commit**

### Task 3.5: 拆分GamePage — 纯布局组件

**Files:**
- Create: `frontend/src/pages/GamePage/GameLayout.tsx`
- Create: `frontend/src/pages/GamePage/GameLayout.module.css`

将 GamePage 中的 JSX 迁移到 `GameLayout.tsx`，通过 props 接收所有状态。`GamePage.tsx` 变成纯粹的状态编排器（~100行）。

- [ ] **Commit**

### Task 3.6: 重构GamePage主文件

**Files:**
- Modify: `frontend/src/pages/GamePage.tsx`

精简为：

```typescript
// frontend/src/pages/GamePage.tsx (~100行)
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGameState } from './GamePage/useGameState';
import { useWSEventHandler } from './GamePage/useWSEventHandler';
import { usePhaseTransition } from './GamePage/usePhaseTransition';
import { GameLayout } from './GamePage/GameLayout';
import { useWebSocket } from '../hooks/useWebSocket';
import { initAudio } from '../utils/sound';

export default function GamePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const gid = Number(gameId);
  const state = useGameState(gid);
  const handleWSEvent = useWSEventHandler(gid, state);
  usePhaseTransition(state.status?.phase, state.status?.winner);

  const { connected } = useWebSocket(gid, 'god', handleWSEvent);

  useEffect(() => { initAudio(); }, []);
  useEffect(() => { state.fetchAndSetStatus(gid); }, [gid]);

  // 轮询fallback
  useEffect(() => {
    const poll = setInterval(() => state.fetchAndSetStatus(gid), 3000);
    return () => clearInterval(poll);
  }, [gid]);

  return <GameLayout state={state} connected={connected} />;
}
```

- [ ] **Commit**

```bash
git add frontend/src/pages/
git commit -m "refactor: complete GamePage modularization"
```

---

## Phase 4: UI重设计 — 暗黑剧场风

### Task 4.1: 重写大厅页

**Files:**
- Modify: `frontend/src/pages/LobbyPage.tsx`
- Create: `frontend/src/pages/LobbyPage.module.css`

设计要点：
- 居中大标题 "🐺 AI 狼人杀" + 金色渐变
- 副标题 "9 AI Agent 策略博弈 · 暗黑剧场"
- 规则卡片（半透明磨砂玻璃）：展示9人身份配置
- 角色展示区（CSS 3D翻转卡牌，hover时翻转显示角色介绍）
- 大"开始游戏"按钮（金色渐变，hover发光）
- 底部小字显示技术栈

- [ ] **Step 1: 实现**

```typescript
// LobbyPage.tsx 核心结构
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../services/api';
import styles from './LobbyPage.module.css';

const ROLES = [
  { name: '狼人', icon: '🐺', count: 3, desc: '夜晚刀人，白天伪装' },
  { name: '预言家', icon: '🔮', count: 1, desc: '每晚查验一人身份' },
  { name: '女巫', icon: '🧪', count: 1, desc: '解药救人，毒药杀人' },
  { name: '猎人', icon: '🏹', count: 1, desc: '出局时开枪带走一人' },
  { name: '村民', icon: '👤', count: 3, desc: '靠发言和投票找出狼人' },
];

export default function LobbyPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [flippedCard, setFlippedCard] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await api.startGame();
      navigate(`/game/${res.game_id}`);
    } catch (e: any) {
      alert(e.message || '启动失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.particles} /> {/* 保留BackgroundParticles */}
      <motion.div className={styles.content} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
        <h1 className={styles.title}>🐺 AI 狼人杀</h1>
        <p className={styles.subtitle}>9 AI Agent 策略博弈 · 暗黑剧场</p>

        <div className={styles.roleGrid}>
          {ROLES.map(role => (
            <motion.div
              key={role.name}
              className={`${styles.roleCard} ${flippedCard === role.name ? styles.flipped : ''}`}
              onClick={() => setFlippedCard(flippedCard === role.name ? null : role.name)}
              whileHover={{ y: -4 }}
            >
              <div className={styles.roleCardInner}>
                <div className={styles.roleCardFront}>
                  <span className={styles.roleIcon}>{role.icon}</span>
                  <span className={styles.roleCount}>×{role.count}</span>
                  <span className={styles.roleName}>{role.name}</span>
                </div>
                <div className={styles.roleCardBack}>
                  <p>{role.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.button
          className={styles.startBtn}
          onClick={handleStart}
          disabled={loading}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          {loading ? '🎭 正在组建剧场...' : '🎭 开始游戏'}
        </motion.button>

        <p className={styles.footer}>
          FastAPI · React 18 · TypeScript · Framer Motion · 多Agent协作
        </p>
      </motion.div>
    </div>
  );
}
```

CSS Module 样式（磨砂玻璃卡片、金色渐变、3D翻转动画）。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/LobbyPage.tsx frontend/src/pages/LobbyPage.module.css
git commit -m "feat: redesign lobby with dark theater style"
```

### Task 4.2: 重写圆桌组件（塔罗牌风）

**Files:**
- Modify: `frontend/src/components/RoundTable.tsx`
- Modify: `frontend/src/components/Seat.tsx`
- Create: `frontend/src/components/RoundTable.module.css`
- Create: `frontend/src/components/SeatSlot.tsx`

设计要点：
- 圆形桌面改为带3D倾斜透视（`perspective: 800px` + `rotateX(15deg)`）
- 玩家卡片化：编号、光晕、角色颜色边框
- 存活：金色边框+呼吸光晕；死亡：灰度+翻面+✕
- 投票时出现票数角标
- 发言时卡片放大+白光边框

- [ ] **Step 1: 重构Seat.tsx**

将样式迁移到 `Seat.module.css`（后续创建），Seat组件改为纯展示：接收 `{ angle, radius, player, isSpeaking, isThinking, voteCount, winnerClass }` 等props。

- [ ] **Step 2: 创建SeatSlot.tsx**（纯展示，从RoundTable拆出）
- [ ] **Step 3: 更新RoundTable.tsx**

- [ ] **Commit**

```bash
git add frontend/src/components/
git commit -m "feat: redesign round table with tarot-card style"
```

### Task 4.3: 重写聊天面板（磨砂玻璃）

**Files:**
- Modify: `frontend/src/components/ChatBubble.tsx`
- Create: `frontend/src/components/ChatBubble.module.css`

设计要点：
- 半透明磨砂玻璃背景（`backdrop-filter: blur(12px)`）
- 发言气泡：半透明深色
- AI内心OS气泡：虚线边框+斜体+灰色（仅God View可见）
- 打字机效果：逐字显示（Framer Motion `animate`）

- [ ] **Commit**

### Task 4.4: 添加PhaseOverlay全屏动画

**Files:**
- Create: `frontend/src/components/PhaseOverlay.tsx`（动画增强版）
- Modify: `frontend/src/pages/GamePage/GameLayout.tsx`

设计要点：
- "🌙 天黑请闭眼" → 大字金色淡入，1.5s后淡出
- "☀️ 天亮了" → 白色淡入
- "🗳 请投票" → 蓝色脉冲
- 所有覆盖层使用 `AnimatePresence` + `motion.div`

- [ ] **Commit**

### Task 4.5: 统一CSS变量 + 清理inline style

**Files:**
- Modify: `frontend/src/index.css`

将现有 CSS 变量保留（已是暗色系），新增：

```css
:root {
  --glass-bg: rgba(26, 31, 46, 0.7);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: blur(12px);
  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-sm: 6px;
  --transition-fast: 0.15s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.6s ease;
}
```

清理所有 inline style（`style={{...}}`）迁移到 CSS Module。

- [ ] **Commit**

---

## Phase 5: 集成验证

### Task 5.1: 确保后端可正常启动

```bash
cd "C:\Users\22075\Desktop\AI-wolf-game-main\backend"
pip install loguru json-repair
python -c "from main import app; print('FastAPI app OK')"
python -c "from core.engine import GameEngine; print('Engine import OK')"
python -c "from core.night_phase import NightPhase; print('NightPhase import OK')"
python -c "from core.day_phase import DayPhase; print('DayPhase import OK')"
python -c "from repositories.game_repo import GameRepo; print('Repository import OK')"
```

- [ ] **Commit** (any fixes from verification)

### Task 5.2: 确保前端可正常构建

```bash
cd "C:\Users\22075\Desktop\AI-wolf-game-main\frontend"
npm run build
```

修复所有 TypeScript 编译错误。

- [ ] **Commit** (any fixes from verification)

### Task 5.3: 端到端测试

启动后端 + 前端，创建一局游戏，确认：
- UI 渲染正常（大厅 → 游戏 → 结束全流程）
- 圆桌玩家卡片正确显示
- 聊天面板正常推送
- Phase Overlay 动画播放
- God View 切换正常
- 无 console 错误

- [ ] **Commit** (any fixes)

---

## 实现顺序

```
Phase 1 (基础设施) → Phase 2 (后端重构) → Phase 3 (前端重构) → Phase 4 (UI重设计) → Phase 5 (验证)
```

每个 Phase 内任务按顺序执行，Phase 间可并联（1→2和3可并行，但4依赖3完成后）。
