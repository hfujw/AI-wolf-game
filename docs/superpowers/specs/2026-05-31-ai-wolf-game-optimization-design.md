# AI狼人杀项目全面优化 — 设计文档

> 日期：2026-05-31
> 状态：已确认

---

## 一、目标与范围

对AI狼人杀项目进行**中度重构**（拆大文件、消除重复、引入三层架构、添加日志/异常处理中间件），同时**重新设计前端UI**为暗黑剧场风格，最终提炼简历技术亮点。

### 不做的事
- 不引入新的重型框架（如Redux、Django）
- 不改变AI Agent核心逻辑
- 不添加Docker/CI配置（后续可加）

---

## 二、后端重构

### 2.1 拆分 engine.py（837行 → 4文件）

| 新文件 | 内容 | 预估 |
|--------|------|------|
| `backend/core/engine.py` | 游戏主循环 run/night_phase/day_phase/_check_winner/_apply_deaths | ~250行 |
| `backend/core/night_phase.py` | `_wolf_action` / `_seer_action` / `_witch_action` / `_resolve_night_deaths` / `_trigger_hunter_shoot`(night) | ~200行 |
| `backend/core/day_phase.py` | `_day_speech_phase` / `_day_vote_phase` / `_elimination` / `_trigger_hunter_shoot`(vote) | ~180行 |
| `backend/core/stats_tracker.py` | `StatsTracker` 类（从engine.py内嵌类独立） | ~100行 |

### 2.2 引入三层架构

```
api/game.py              # 路由层（参数校验 + 调用service）
services/game_service.py  # 业务层（增强现有）
repositories/            # 🆕 数据访问层
├── game_repo.py         # Game CRUD
├── player_repo.py       # GamePlayer CRUD
└── event_repo.py        # GameEvent CRUD
```

### 2.3 消除 API 重复

`api/game.py` 中 `/replay`、`/events`、`/debug` 共享的查询逻辑抽出公共函数 `_get_game_with_players_and_events()`。

### 2.4 安全 + 基础设施

- **移除硬编码API Key**：`config.py` 的默认值只从 `.env` 读取，不设fallback明文
- **全局异常处理**：`middleware/error_handler.py` — FastAPI exception handler，统一返回 `{"detail": "...", "error_code": "..."}`
- **结构化日志**：引入 `loguru`，所有 `print()` 替换为 `logger.info()`
- **JSON解析增强**：LLM响应解析用 `json_repair` 替代手写正则

### 2.5 新增文件清单

| 文件 | 说明 |
|------|------|
| `backend/core/night_phase.py` | 夜晚阶段逻辑 |
| `backend/core/day_phase.py` | 白天阶段逻辑 |
| `backend/core/stats_tracker.py` | MVP/SVP统计 |
| `backend/repositories/__init__.py` | |
| `backend/repositories/game_repo.py` | Game数据访问 |
| `backend/repositories/player_repo.py` | Player数据访问 |
| `backend/repositories/event_repo.py` | Event数据访问 |
| `backend/middleware/__init__.py` | |
| `backend/middleware/error_handler.py` | 全局异常处理 |
| `backend/middleware/logger.py` | Loguru配置 |

---

## 三、前端重构

### 3.1 拆分 GamePage.tsx（520行 → 模块化）

| 新文件 | 内容 |
|--------|------|
| `pages/GamePage/GamePage.tsx` | 主页面，~200行，只做状态编排+布局 |
| `pages/GamePage/useGameState.ts` | 核心状态管理hook（status/logs/chat/thinking） |
| `pages/GamePage/useWSEventHandler.ts` | WebSocket事件处理 |
| `pages/GamePage/usePhaseTransition.ts` | 阶段切换检测+音效触发 |
| `pages/GamePage/GameLayout.tsx` | 纯UI布局组件 |

### 3.2 消除重复

- `handleWSEvent` 和 polling `useEffect` 中重复的phase切换/音效/finished检测 → 抽入 `usePhaseTransition`
- 3次重复的 `mapGameStatus` + `buildLogs` 调用模式 → 抽入 `useGameState`

### 3.3 组件优化

- `RoundTable.tsx` → 拆出 `SeatSlot.tsx` 纯展示
- `ChatBubble.tsx` 打字机效果 → Framer Motion 逐字动画
- `BackgroundParticles.tsx` → `React.memo` + `useMemo`
- 全局 inline style → **CSS Module**（`*.module.css`）

---

## 四、UI 重新设计：暗黑剧场风

### 4.1 整体风格
- 暗黑底色 + 琥珀金点缀 + 血红警告
- 磨砂玻璃面板（`backdrop-filter: blur()`）
- 统一动效系统：fadeInUp / pulse / shake / flip

### 4.2 各模块改动

| 模块 | 改动 |
|------|------|
| **大厅** | 加规则卡片、角色展示（CSS 3D卡牌翻转）、一键开始按钮 |
| **圆桌** | 3D倾斜桌面视角、玩家卡片化（编号+光晕+状态标识）、死亡翻面 |
| **阶段覆盖层** | 全屏半透明大字动画（"🌙 天黑请闭眼" → 1.5s淡出） |
| **聊天面板** | 半透明磨砂玻璃、God View显示AI内心OS、打字机逐字动画 |
| **战斗日志** | 底部横条、彩色事件标签（💀红/🗳蓝/🔮金） |

### 4.3 技术方案
- 继续 Framer Motion（`AnimatePresence`、`motion.div`）
- CSS Module 替代 inline style
- 音效保留，可选加氛围 BGM 开关

---

## 五、简历技术亮点

### 必被问（⭐⭐⭐⭐⭐）
1. **AsyncIO并发控制** — Semaphore(3) + 指数退避 + 熔断器
2. **多Agent协作** — 9个AI独立上下文，狼人隐式协作
3. **ReAct循环** — Thought→Action→Observation + 重复检测
4. **Prompt Engineering** — 5角色×多种人格 = 完整策略体系
5. **WebSocket实时推送** — 指数退避重连 + 上帝视角权限分离

### 大概率被问（⭐⭐⭐⭐）
6. FastAPI async全链路 + SQLAlchemy Async
7. Pydantic ↔ TypeScript 类型体系
8. 滑动窗口记忆 + 定期摘要压缩
9. Framer Motion 动画体系
10. 防语义漂移（QueryValidator + EvidenceJudge）

### 可能被问（⭐⭐⭐）
11. 策略模式（BaseAgent继承体系）
12. 事件驱动（engine事件 → WS broadcast）
13. 指数退避重试（双层：LLM层 + 并发层）
14. React Router + Vite HMR
15. 泛型API封装（`request<T>`）

---

## 六、验收标准

- [ ] engine.py 拆分为4个文件，每文件<300行
- [ ] API层重复代码消除
- [ ] 硬编码API Key移除
- [ ] 全局异常处理 + loguru日志
- [ ] GamePage.tsx 拆分为模块化结构
- [ ] CSS Module 替代 inline style
- [ ] 暗黑剧场风UI完整可用
- [ ] `npm run build` 通过
- [ ] `python backend/main.py` 正常启动
- [ ] 一次完整9人对局可运行
