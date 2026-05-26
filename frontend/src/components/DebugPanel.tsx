import { useEffect, useState, useRef } from 'react'
import { ROLE_LABELS, ROLE_COLORS } from '../types'

interface DebugData {
  game_id: number
  started_at: string | null
  ended_at: string | null
  engine_online: boolean
  engine_phase: string
  engine_round: number
  engine_winner: string | null
  witch_antidote: boolean | null
  witch_poison: boolean | null
  players: Array<{
    id: number
    name: string
    role: string
    personality: string
    seat_number: number
    is_alive: boolean
  }>
  events_count: number
  engine_log: string[]
  latest_events: Array<{
    round: number
    phase: string
    type: string
    public: string | null
    private: string | null
    thought: string | null
  }>
}

interface Props {
  gameId: number | null
  visible: boolean
  onToggle: () => void
}

const PHASE_LABELS: Record<string, string> = {
  night_werewolf: '🌙 狼人行动',
  night_seer: '🌙 预言家查验',
  night_witch: '🌙 女巫用药',
  day_announce: '☀️ 天亮公告',
  day_speech: '☀️ 发言环节',
  day_vote: '☀️ 投票环节',
  elimination: '⚖️ 放逐结算',
  elimination_end: '⚖️ 放逐结束',
  game_over: '🏆 游戏结束',
  game_start: '🎬 游戏开始',
  waiting: '⏳ 等待',
}

export default function DebugPanel({ gameId, visible, onToggle }: Props) {
  const [data, setData] = useState<DebugData | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!gameId || !visible) return
    let cancelled = false

    const poll = async () => {
      try {
        const res = await fetch(`/api/games/${gameId}/debug`)
        const d: DebugData = await res.json()
        if (!cancelled) setData(d)
      } catch {}
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [gameId, visible])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [data?.engine_log?.length])

  if (!visible) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 999,
          padding: '8px 16px',
          fontSize: 12,
          background: 'rgba(155,89,182,0.3)',
          color: '#9b59b6',
          border: '1px solid #9b59b6',
          borderRadius: 20,
        }}
      >
        🔍 监测面板
      </button>
    )
  }

  if (!data) {
    return (
      <div style={{
        position: 'fixed',
        right: 0,
        top: 0,
        width: 360,
        height: '100vh',
        background: 'rgba(10,10,30,0.95)',
        borderLeft: '1px solid rgba(255,255,255,0.1)',
        zIndex: 998,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#888',
        fontSize: 13,
      }}>
        加载中...
      </div>
    )
  }

  const aliveCount = data.players.filter(p => p.is_alive).length
  const deadCount = data.players.length - aliveCount

  return (
    <div style={{
      position: 'fixed',
      right: 0,
      top: 0,
      width: 380,
      height: '100vh',
      background: 'rgba(10,10,30,0.97)',
      borderLeft: '1px solid rgba(255,255,255,0.1)',
      zIndex: 998,
      display: 'flex',
      flexDirection: 'column',
      fontSize: 12,
      color: '#ccc',
    }}>
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(0,0,0,0.3)',
      }}>
        <span style={{ fontWeight: 600, color: '#9b59b6' }}>🔍 实时监测</span>
        <button
          onClick={onToggle}
          style={{
            padding: '2px 10px', fontSize: 11,
            background: 'rgba(255,255,255,0.08)', color: '#888',
            border: '1px solid #444', borderRadius: 4,
          }}
        >
          关闭
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '10px 14px' }}>
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          borderRadius: 8,
          padding: '10px 12px',
          marginBottom: 10,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888' }}>状态</span>
            <span style={{ color: data.engine_online ? '#2ecc71' : '#e74c3c', fontWeight: 600 }}>
              {data.engine_online ? '● 运行中' : '○ 离线'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888' }}>阶段</span>
            <span style={{ fontWeight: 600 }}>
              {PHASE_LABELS[data.engine_phase] || data.engine_phase}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888' }}>轮次</span>
            <span style={{ fontWeight: 600 }}>第 {data.engine_round} 轮</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888' }}>存活/死亡</span>
            <span>
              <span style={{ color: '#2ecc71' }}>{aliveCount}</span>
              <span style={{ color: '#666' }}> / </span>
              <span style={{ color: '#e74c3c' }}>{deadCount}</span>
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: '#888' }}>女巫状态</span>
            <span style={{ fontSize: 11 }}>
              🧪解药:{data.witch_antidote ? '✅' : '❌'} ☠毒药:{data.witch_poison ? '✅' : '❌'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#888' }}>事件数</span>
            <span>{data.events_count}</span>
          </div>
          {data.engine_winner && (
            <div style={{
              marginTop: 8, padding: '6px 10px',
              background: data.engine_winner === 'villagers' ? 'rgba(46,204,113,0.15)' : 'rgba(231,76,60,0.15)',
              borderRadius: 6,
              textAlign: 'center',
              color: data.engine_winner === 'villagers' ? '#2ecc71' : '#e74c3c',
              fontWeight: 600,
            }}>
              {data.engine_winner === 'villagers' ? '🎉 好人阵营获胜' : '🐺 狼人阵营获胜'}
            </div>
          )}
        </div>

        <div style={{ marginBottom: 10 }}>
          <div style={{ color: '#9b59b6', fontWeight: 600, marginBottom: 6 }}>玩家状态</div>
          {data.players.map(p => (
            <div key={p.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px',
              marginBottom: 2,
              borderRadius: 4,
              background: p.is_alive ? 'rgba(46,204,113,0.05)' : 'rgba(231,76,60,0.08)',
              opacity: p.is_alive ? 1 : 0.5,
            }}>
              <span style={{ fontWeight: 600, minWidth: 28 }}>{p.seat_number}号</span>
              <span style={{
                fontSize: 10,
                padding: '1px 6px',
                borderRadius: 3,
                background: (ROLE_COLORS[p.role] || '#555') + '33',
                color: ROLE_COLORS[p.role] || '#888',
              }}>
                {ROLE_LABELS[p.role] || p.role}
              </span>
              <span style={{ flex: 1, fontSize: 11 }}>{p.name.replace('AI_', '')}</span>
              {!p.is_alive && <span>💀</span>}
            </div>
          ))}
        </div>

        <div style={{ marginBottom: 10 }}>
          <div style={{ color: '#9b59b6', fontWeight: 600, marginBottom: 6 }}>最新事件 ({data.latest_events.length})</div>
          {data.latest_events.slice(0, 15).map((e, i) => (
            <div key={i} style={{
              padding: '3px 8px',
              marginBottom: 1,
              fontSize: 10,
              borderRadius: 3,
              background: e.type === 'phase_change' ? 'rgba(155,89,182,0.08)' :
                          e.type === 'death' ? 'rgba(231,76,60,0.08)' :
                          e.type === 'speech' ? 'rgba(52,152,219,0.08)' :
                          'transparent',
            }}>
              <span style={{ color: '#666' }}>R{e.round}</span>
              <span style={{ color: '#888', marginLeft: 4 }}>{e.type}</span>
              <span style={{ marginLeft: 6, color: '#bbb' }}>
                {e.public || e.private || ''}
              </span>
            </div>
          ))}
        </div>

        <div>
          <div style={{ color: '#9b59b6', fontWeight: 600, marginBottom: 6 }}>引擎日志</div>
          <div style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 6,
            padding: '8px 10px',
            fontFamily: 'monospace',
            fontSize: 10,
            color: '#aaa',
            maxHeight: 250,
            overflow: 'auto',
            lineHeight: 1.6,
          }}>
            {data.engine_log.length === 0 && <span style={{ color: '#555' }}>暂无日志</span>}
            {data.engine_log.map((line, i) => (
              <div key={i} style={{
                color: line.includes('异常') ? '#e74c3c' :
                       line.includes('调用LLM') ? '#f39c12' :
                       line.includes('击杀') || line.includes('死亡') ? '#e74c3c' :
                       line.includes('开始') || line.includes('结束') ? '#9b59b6' :
                       '#aaa',
              }}>
                {line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
