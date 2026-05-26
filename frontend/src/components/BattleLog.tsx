import { useEffect, useRef } from 'react';

interface LogEntry {
  id: number;
  type: 'system' | 'death' | 'action' | 'speech' | 'narrator';
  text: string;
  timestamp: number;
}

interface BattleLogProps {
  events: LogEntry[];
}

function getLogEmoji(type: string, text: string): string {
  if (type === 'death') return '💀 ';
  if (type === 'action') {
    if (text.includes('查验') || text.includes('预言')) return '🔮 ';
    if (text.includes('救') || text.includes('毒') || text.includes('药')) return '🧪 ';
    if (text.includes('刀') || text.includes('袭击')) return '🗡️ ';
    return '⚡ ';
  }
  if (type === 'speech') return '💬 ';
  if (type === 'narrator') {
    if (text.includes('投票结果') || text.includes('放逐')) return '✅ ';
    if (text.includes('查验')) return '⏳ ';
    if (text.includes('阶段')) return '📢 ';
    if (text.includes('胜利') || text.includes('获胜')) return '🏆 ';
    return '📍 ';
  }
  if (text.includes('阶段') || text.includes('开始')) return '📢 ';
  if (text.includes('胜利') || text.includes('获胜')) return '🏆 ';
  if (text.includes('淘汰') || text.includes('放逐')) return '⚖️ ';
  return '🔹 ';
}

export default function BattleLog({ events }: BattleLogProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div className="battle-log-panel">
      <div className="battle-log-header">-- Battle Log --</div>
      <div className="battle-log-list" ref={listRef}>
        {events.map((e) => (
          <div key={e.id} className={`battle-log-item ${e.type}`}>
            {getLogEmoji(e.type, e.text)}{e.text}
          </div>
        ))}
      </div>
    </div>
  );
}
