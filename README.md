# AI 狼人杀 — 9 人局 LLM 对战平台

> **AI Werewolf Game** — 每名玩家由不同的大语言模型驱动，拥有独立人格、专属记忆和推理能力。9 人标准局，全程实时推演，支持上帝视角复盘。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?logo=typescript)](https://www.typescriptlang.org)

---

## 功能特性

| 特性 | 说明 |
|------|------|
| 🎭 **多模型混战** | 每位玩家可配置不同 LLM（OpenAI / DeepSeek / 智谱 GLM / Anthropic 等），一个对局最多 9 个模型同台竞技 |
| 🧠 **ReAct 推理循环** | Thought → Action → Observation 三步决策，每步输出内心独白（internal_thought），可复盘 AI 的真实想法 |
| 🛡️ **防语义漂移** | 三层防护：QueryValidator（调用前） → EvidenceJudge（响应后） → DriftGuard（连续漂移自动回滚） |
| 💬 **人格系统** | 6 种人格 x 5 种角色，狼人分煽动型/深水倒钩型/冷静分析型，女巫高冷掌控型，猎人为暴民领袖型 |
| 🔄 **三级容错** | LLM API 失败时自动降级到人格化备用发言（fallback），每条备用发言都按角色+人格+阶段定制 |
| ⚡ **并发控制** | Semaphore(3) 限流 + 指数退避重试 + Circuit Breaker 熔断器，防止 API 过载 |
| 📝 **滑动窗口记忆** | 最近 10 轮完整对话 + 每 3 轮自动摘要压缩，上下文不超限 |
| 🎬 **WebSocket 实时推送** | 上帝视角（看全部私密信息+内心独白）vs 普通视角（只看公开内容），支持游戏回放 |
| 🏆 **MVP/SVP 统计** | 投票正确率、技能使用次数、存活轮数，赛后自动评选 |

---

## 游戏规则

9 人标准局：**3 狼人 + 1 预言家 + 1 女巫 + 1 猎人 + 3 村民**

```
夜晚：狼人刀人 → 预言家查验 → 女巫用药
白天：轮流发言 → 投票放逐
胜负：狼人全灭 → 好人胜；神职全灭或村民全灭 → 狼人胜
```

---

## 架构设计

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (React 18)                │
│          Vite + TypeScript + Framer Motion           │
│              WebSocket / REST API                     │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────────┐
│                   Backend (FastAPI)                    │
│                                                       │
│  ┌─────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  API    │  │  WebSocket   │  │   Middleware     │  │
│  │ /games  │  │  /ws/game/   │  │ (CORS/Error/    │  │
│  │ /stats  │  │  {id}        │  │  Logger)        │  │
│  └────┬────┘  └──────┬───────┘  └─────────────────┘  │
│       │              │                                │
│  ┌────┴──────────────┴────────────────────────────┐   │
│  │              GameEngine                         │   │
│  │  night_phase → day_phase → check_winner        │   │
│  │  God View 实时日志 + 事件推送                   │   │
│  └────┬───────────────────────────────────────────┘   │
│       │                                               │
│  ┌────┴───────────────────────────────────────────┐   │
│  │            AgentManager                         │   │
│  │  ┌──────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │   │
│  │  │ Werewolf │ │  Seer  │ │ Witch │ │ Hunter │ │   │
│  │  │  Agent   │ │ Agent  │ │ Agent │ │ Agent  │ │   │
│  │  └────┬─────┘ └───┬────┘ └──┬────┘ └───┬────┘ │   │
│  │       │            │         │          │       │   │
│  │  ┌────┴────────────┴─────────┴──────────┴────┐ │   │
│  │  │          ReAct Loop (max 3 steps)          │ │   │
│  │  │  Thought → Action → Observation → repeat   │ │   │
│  │  └────────────────────┬───────────────────────┘ │   │
│  └───────────────────────┼─────────────────────────┘   │
│                          │                             │
│  ┌───────────────────────┼─────────────────────────┐   │
│  │            LLMClient  │                          │   │
│  │  ┌────────────────────┴──────────────────────┐  │   │
│  │  │  OpenAI-compatible API (multi-provider)   │  │   │
│  │  │  json_repair → 正则提取 → fallback        │  │   │
│  │  └───────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │
│  │  Memory  │  │  Drift   │  │  Concurrency       │   │
│  │  Manager │  │  Guard   │  │  (Semaphore + CB)  │   │
│  └──────────┘  └──────────┘  └───────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │         SQLite (async, aiosqlite)                 │ │
│  │  games / game_players / game_events / rooms       │ │
│  └──────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────┘
```

### 核心设计

#### ReAct 推理循环

每名 AI 玩家做决策时经历：

```
Thought（思考） → Action（行动） → Observation（观察结果）
     ↑                                        |
     └────────── 修正思路，继续思考 ←──────────┘
```

- 最多 3 步循环
- 连续 2 次相同目标 → 自动终止（防止死循环）
- LLM 主动声明 `final_answer` → 提前结束

#### 防语义漂移 (DriftGuard)

| 阶段 | 组件 | 职责 |
|------|------|------|
| 调用前 | QueryValidator | 检查 prompt 是否偏离原始任务、有无身份暴露/Prompt注入风险 |
| 响应后 | EvidenceJudge | 验证 target_id 合法性、药水可用性、发言长度 |
| 累计控制 | DriftGuard | 连续 3 次漂移触发回滚，重置为 baseline prompt |

#### 记忆管理

```
滑动窗口 (最近 10 条)        定期摘要 (每 3 轮)
┌──────────────────┐      ┌──────────────────┐
│ 完整对话 (NEW)    │      │ 第1-3轮: 死亡/放逐/ │
│ 完整对话 (NEW)    │      │ 投票/发言摘要       │
│ ...              │      ├──────────────────┤
│ 完整对话 (OLD) → 压缩  │ 第4-6轮: ...       │
└──────────────────┘      └──────────────────┘
```

---

## 快速开始

### 1. 环境准备

```bash
git clone <repo-url>
cd AI-wolf-game-main

# 后端
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 2. 配置 LLM API

```bash
# 复制配置模板
cp backend/config.example.py backend/config.py

# 设置环境变量（.env 或直接 export）
export LLM_API_KEY=your-api-key
export LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
export LLM_MODEL=GLM-4-Flash

# 高级：每位玩家可用不同模型
export P1_MODEL=gpt-4o-mini
export P1_BASE_URL=https://api.openai.com/v1
export P1_API_KEY=sk-xxx
export P3_MODEL=deepseek-chat
export P3_BASE_URL=https://api.deepseek.com/v1
export P3_API_KEY=sk-xxx
```

### 3. 启动

```bash
# 终端1：后端
cd backend
uvicorn main:app --reload --port 8000

# 终端2：前端
cd frontend
npm run dev
```

访问 `http://localhost:5173` 进入游戏界面。

### 4. 一键开始游戏

```bash
curl -X POST http://localhost:8000/api/games/start
# 返回 {"game_id": 1}
```

或访问 `http://localhost:8000/docs` 使用 Swagger 交互文档。

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/games/start` | 一键创建房间+分配角色+启动游戏 |
| POST | `/api/games/{id}/force-start` | 手动触发游戏（备用） |
| GET | `/api/games/{id}/status` | 获取游戏状态（存活玩家、事件） |
| GET | `/api/games/{id}/debug` | 调试端点：引擎状态+日志+统计 |
| GET | `/api/games/{id}/replay` | 完整回放（含私密信息） |
| GET | `/api/games/{id}/stats` | MVP/SVP、投票记录、技能使用 |
| WS | `/ws/game/{id}?viewer=god` | WebSocket 实时推送（上帝视角） |
| WS | `/ws/game/{id}?viewer=normal` | WebSocket 实时推送（普通视角） |

---

## 人格系统

| 角色 | 可选人格 | 特点 |
|------|---------|------|
| 狼人 | 煽动型 | 主动带节奏，混淆视听 |
| 狼人 | 深水倒钩型 | 伪装好人，潜伏深处 |
| 狼人 | 冷静分析型 | 理性发言，不露破绽 |
| 预言家 | 耿直技术流 | 报查验结果，逻辑硬刚 |
| 女巫 | 高冷掌控型 | 沉默寡言，关键时出手 |
| 猎人 | 暴民领袖型 | 强势带队，死前开枪 |
| 村民 | 萌新表水型 | 表水自证，跟票分析 |
| 村民 | 冷静分析型 | 逻辑推理，排除法 |
| 村民 | 暴民领袖型 | 主动归票，carry 全场 |

---

## 容错机制

```
LLM API 调用
  ├── ✅ 成功 → json_repair 鲁棒解析 → EvidenceJudge 验证 → 返回结果
  └── ❌ 失败 → 指数退避重试 (1s→2s→4s)
       ├── ✅ 重试成功 → 继续
       └── ❌ 3次全败 → Circuit Breaker 熔断 → fallback 决策
            └── 按 角色+人格+阶段 匹配备用发言/行动
```

---

## 项目结构

```
AI-wolf-game-main/
├── backend/
│   ├── main.py                    # FastAPI 入口，CORS，启动时 LLM 连通性测试
│   ├── config.py                  # 多模型配置（支持每人不同 LLM）+ 游戏参数
│   ├── requirements.txt
│   ├── agents/
│   │   ├── base_agent.py          # BaseAgent：ReAct 循环 + 漂移检测
│   │   ├── werewolf_agent.py      # 狼人：夜晚刀人 + 白天伪装发言
│   │   ├── seer_agent.py          # 预言家：查验身份 + 报查验结果
│   │   ├── witch_agent.py         # 女巫：解药/毒药决策
│   │   ├── hunter_agent.py        # 猎人：死亡时开枪
│   │   └── villager_agent.py      # 村民：分析发言 + 投票
│   ├── core/
│   │   ├── engine.py              # GameEngine：夜晚/白天阶段编排，胜负判定
│   │   ├── agent_manager.py       # 并发调度所有 Agent 的 LLM 调用
│   │   ├── react_loop.py          # ReAct 循环：Thought→Action→Observation
│   │   ├── drift_guard.py         # 防漂移：QueryValidator + EvidenceJudge
│   │   ├── concurrency.py         # Semaphore(3) + Circuit Breaker + 指数退避
│   │   └── stats_tracker.py       # MVP/SVP 统计，投票正确率
│   ├── llm/
│   │   └── llm_client.py          # OpenAI SDK 封装，json_repair 解析，fallback
│   ├── memory/
│   │   ├── memory_manager.py      # 上下文构建器（不同角色看到不同信息）
│   │   └── summarizer.py          # 滑动窗口 + 定期摘要压缩
│   ├── prompts/
│   │   ├── system_prompts.py      # 角色人格 System Prompt 模板
│   │   └── templates.py           # User Message 模板（发言/投票/夜晚行动）
│   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── game.py, room.py, game_player.py, game_event.py
│   ├── schemas/
│   │   └── game_schemas.py        # Pydantic 请求/响应 + AgentContext/Decision
│   ├── repositories/              # 数据访问层
│   ├── services/
│   │   └── game_service.py        # 游戏服务：创建对局、分配角色、启动引擎
│   ├── api/
│   │   ├── game.py                # REST API：start/status/debug/replay/stats
│   │   └── ws.py                  # WebSocket：实时推送 + 历史重放
│   ├── middleware/
│   │   ├── error_handler.py       # 全局异常处理
│   │   └── logger.py              # loguru 日志配置
│   └── db/
│       └── database.py            # SQLite async 引擎 + 表创建
├── frontend/
│   ├── src/                       # React 18 + TypeScript
│   ├── package.json               # Vite + React Router + Framer Motion
│   └── vite.config.ts
├── docs/
│   └── superpowers/               # 设计文档 + 优化计划
└── 启动.bat / 安装依赖.bat         # Windows 一键脚本
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI |
| **数据库** | SQLite + SQLAlchemy (async) |
| **LLM SDK** | OpenAI Python SDK (兼容多提供商) |
| **实时通信** | WebSocket |
| **JSON 解析** | json-repair（容错解析 LLM 输出） |
| **日志** | loguru |
| **前端** | React 18 + TypeScript + Vite |
| **动画** | Framer Motion |
| **路由** | React Router v6 |

### 支持的 LLM 提供商

| 提供商 | Base URL |
|--------|----------|
| OpenAI | `https://api.openai.com/v1` |
| 智谱 AI (GLM) | `https://open.bigmodel.cn/api/paas/v4/` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Anthropic | `https://api.anthropic.com/v1` |
| 任意 OpenAI-compatible | 自定义 |

---

## 环境变量

```bash
# 全局默认（所有玩家共用）
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
LLM_MODEL=GLM-4-Flash

# 单人覆盖（P1~P9，N 为座位号）
P1_API_KEY=sk-xxx
P1_BASE_URL=https://api.openai.com/v1
P1_MODEL=gpt-4o-mini

# 游戏参数
GAME_SPEED=1.0      # 速度倍率：1.0 正常，5.0 极速
FAST_DEBUG=true     # 调试模式：跳过等待
LLM_TIMEOUT=60      # LLM 调用超时（秒）
LLM_MAX_RETRIES=2   # LLM 调用最大重试次数
```
