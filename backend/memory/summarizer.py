"""记忆摘要模块：滑动窗口 + 定期摘要

设计：
- 滑动窗口：保留最近 10 条对话，超过的进行摘要压缩
- 定期摘要：每 3 轮创建一个摘要块
- 上下文长度管理：单段摘要不超过 500 字符
"""

from typing import Optional


class ConversationSummarizer:
    def __init__(self, window_size: int = 10, summary_interval: int = 3):
        self.window_size = window_size
        self.summary_interval = summary_interval
        self.full_history: list[dict] = []
        self.summaries: list[str] = []
        self.last_summary_round: int = 0

    def add(self, entry: dict):
        self.full_history.append(entry)

    def get_context(self, current_round: int, max_chars: int = 3000) -> str:
        # 检查是否需要生成新摘要
        if current_round - self.last_summary_round >= self.summary_interval:
            self._generate_summary(current_round)

        # 滑动窗口内的最近对话保持完整
        recent = self.full_history[-self.window_size:]
        recent_str = self._format_conversations(recent)

        # 拼接历史摘要 + 最近对话
        parts = []
        if self.summaries:
            parts.append("【历史摘要】")
            for s in self.summaries[-3:]:
                parts.append(f"· {s}")

        if recent_str:
            parts.append("\n【最近对话】")
            parts.append(recent_str)

        full = "\n".join(parts)
        if len(full) > max_chars:
            full = full[:max_chars] + "...(已截断)"
        return full

    def _generate_summary(self, current_round: int):
        round_start = max(0, len(self.full_history) - self.window_size * 2)
        round_events = self.full_history[round_start:]

        deaths = []
        eliminations = []
        vote_summary = []
        key_speeches = []

        for e in round_events:
            phase = e.get("phase", "")
            etype = e.get("type", "")
            content = e.get("content", "")
            speaker = e.get("speaker", "")

            if etype == "death":
                deaths.append(content)
            elif etype == "elimination":
                eliminations.append(content)
            elif etype == "vote":
                vote_summary.append(f"{speaker}{content}")
            elif etype == "discussion":
                if len(content) > 50:
                    key_speeches.append(f"{speaker}: {content[:60]}...")

        parts = []
        if deaths:
            parts.append(f"死亡: {'; '.join(deaths[-3:])}")
        if eliminations:
            parts.append(f"放逐: {'; '.join(eliminations[-3:])}")
        if vote_summary:
            parts.append(f"投票: {'; '.join(vote_summary[-5:])}")
        if key_speeches:
            parts.append(f"发言摘要: {'; '.join(key_speeches[-3:])}")

        summary = f"第{self.last_summary_round + 1}-{current_round}轮: " + " | ".join(parts) if parts else f"第{current_round}轮无关键事件"
        self.summaries.append(summary[:500])
        self.last_summary_round = current_round

    def _format_conversations(self, conversations: list[dict]) -> str:
        if not conversations:
            return "暂无历史记录"

        lines = []
        current_round = None
        for conv in conversations:
            r = conv.get("round", 0)
            if current_round != r:
                current_round = r
                lines.append(f"\n=== 第{r}回合 ===")
            t = conv.get("type", "")
            if t == "death":
                lines.append(f"💀 {conv.get('content', '')}")
            elif t == "vote":
                lines.append(f"🗳 {conv.get('speaker', '')}{conv.get('content', '')}")
            elif t == "elimination":
                lines.append(f"⚖️ {conv.get('content', '')}")
            elif t == "hunter_shoot":
                lines.append(f"🔫 {conv.get('content', '')}")
            else:
                speaker = conv.get("speaker", "")
                content = conv.get("content", "")
                lines.append(f"{speaker}说：{content}")
        return "\n".join(lines)

    def clear(self):
        self.full_history = []
        self.summaries = []
        self.last_summary_round = 0
