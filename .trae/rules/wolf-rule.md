## 全局宪法规则（本次任务全程遵守，不可违反）

### 1. 设计审美规则
- 视觉风格必须是：**深色魔幻悬疑风**，背景深蓝黑（#0a0a12），主色调暗金（#c9a96e）和暗红（#8b0000）。
- 禁止使用高饱和度荧光色（如亮绿、亮粉、纯白背景）。
- 所有动效必须使用 **framer-motion**，禁止用纯 CSS transition 实现复杂动画。
- 动画时长统一为 0.5～1.5 秒，缓动函数使用 `easeInOut`，禁止出现线性匀速动画。
- 所有文字使用系统无衬线字体（如 Inter, PingFang SC），禁止使用衬线字体或花体字。

### 2. 代码结构规则
- 所有新组件必须放在 `frontend/src/components/` 下，一个文件一个组件，组件名用 PascalCase。
- 组件内部结构严格按以下顺序：① React hooks → ② 衍生状态（useMemo/useCallback）→ ③ 事件处理函数 → ④ JSX return。
- 禁止在 JSX 中写复杂逻辑，复杂逻辑必须提取为函数或自定义 hook。
- 所有动画相关逻辑封装在独立的 `use[Feature]Animation` 自定义 hook 中，不散落在组件主体里。

### 3. CSS 规则
- 所有样式使用 CSS Module 或 Tailwind CSS，禁止使用内联 style（特殊情况需注释说明）。
- 主题色必须引用在 `index.css` 中定义好的 CSS 变量（如 `var(--accent-gold)`），禁止硬编码颜色值。
- 动画相关的 CSS 属性（opacity, transform）必须加 `will-change` 提示浏览器 GPU 加速。

### 4. 游戏状态与事件规则
- 所有前端状态变更只能来自 WebSocket 推送的 `game_events`，禁止前端自行模拟或猜测游戏状态。
- `phase` 字段的合法值必须与后端约定好的集合一致：`night_werewolf, night_seer, night_witch, day_announce, day_speech, day_vote, elimination, game_over`。
- 任何事件处理前，必须检查 `event_type` 的合法性，未知类型直接忽略并 console.warn，不能报错中断游戏。

### 5. AI 思考状态规则
- 当玩家处于“等待 LLM 响应”状态时，对应的 `Seat` 组件必须显示“思考中...”动画。
- 思考状态由后端通过 WebSocket 推送 `event_type: "agent_thinking"` 事件来触发，前端收到后设置对应玩家的 `is_thinking` 为 true；收到该玩家的任何其他事件时，重置为 false。

### 6. 交付规则
- 每次只修改与本次任务相关的文件，禁止改动未提及的文件。
- 如果某个改动需要修改多个文件，必须按依赖顺序逐个输出，每个文件标明完整路径。
- 代码注释使用中文，解释“为什么这么做”，而不是“做了什么”。