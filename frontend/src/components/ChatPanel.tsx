import { useEffect, useRef, useMemo, useState } from 'react'
import { GameEvent, ROLE_LABELS, ROLE_COLORS } from '../types'

interface PlayerInfo {
  id: number
  name: string
  role: string
  seat_number: number
  is_alive: boolean
}

interface Props {
  events: GameEvent[]
  players: PlayerInfo[]
  viewer: 'normal' | 'god'
}

function getPlayerName(players: PlayerInfo[], playerId: number | null): string {
  if (!playerId) return '系统'
  const p = players.find(pl => pl.id === playerId)
  if (p) return `${p.seat_number}号 ${p.name.replace('AI_', '').replace(`_${p.seat_number}号`, '')}`
  return `玩家${playerId}`
}

function getPlayerRole(players: PlayerInfo[], playerId: number | null): string {
  if (!playerId) return ''
  const p = players.find(pl => pl.id === playerId)
  return p ? p.role : ''
}

const SPEAKER_COLORS = ['#3498db', '#e67e22', '#2ecc71', '#e74c3c', '#9b59b6', '#1abc9c']

function getSpeakerColor(playerId: number | null): string {
  if (!playerId) return '#888'
  return SPEAKER_COLORS[(playerId - 1) % SPEAKER_COLORS.length]
}

function parseActionParts(text: string): { action: string | null; speech: string } {
  const match = text.match(/^【(.+?)】\s*(.*)/s)
  if (match) {
    return { action: match[1], speech: match[2] || text }
  }
  return { action: null, speech: text }
}

export default function ChatPanel({ events, players, viewer }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [expandedThoughts, setExpandedThoughts] = useState<Set<string>>(new Set())

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  const deduped = useMemo(() => {
    const seen = new Set<string>()
    return events.filter(e => {
      const key = `${e.event_type}|${e.player_id}|${e.round_number}|${e.public_content?.slice(0, 50)}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [events])

  const displayEvents = deduped.slice(-80)

  const toggleThought = (key: string) => {
    setExpandedThoughts(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div style={{
      flex: 1, overflow: 'auto', padding: '16px 8px',
      maxHeight: '50vh', minHeight: 150,
      scrollBehavior: 'smooth',
    }}>
      {displayEvents.length === 0 && (
        <div style={{ textAlign: 'center', color: '#555', padding: 20, fontSize: 14 }}>
          ⏳ 等待游戏事件...
        </div>
      )}

      {displayEvents.map((event, idx) => {
        const playerName = getPlayerName(players, event.player_id)
        const playerRole = getPlayerRole(players, event.player_id)
        const isNightEvent = event.event_type === 'seer_check' || event.event_type === 'witch_action' || event.event_type === 'witch_use_antidote' || event.event_type === 'witch_use_poison' || event.event_type === 'werewolf_kill'
        const isSystemEvent = event.event_type === 'death' || event.event_type === 'phase_change' || event.event_type === 'elimination' || event.event_type === 'game_over' || isNightEvent

        if (isSystemEvent) {
          const isNight = event.phase?.startsWith('night')
          const bgColor = event.event_type === 'death' ? 'rgba(231,76,60,0.12)' :
                         event.event_type === 'game_over' ? 'rgba(46,204,113,0.15)' :
                         event.event_type === 'elimination' ? 'rgba(230,126,34,0.12)' :
                         isNightEvent ? 'rgba(52,73,94,0.25)' :
                         'rgba(155,89,182,0.08)'
          const borderColor = event.event_type === 'death' ? '#e74c3c' :
                             event.event_type === 'game_over' ? '#2ecc71' :
                             event.event_type === 'elimination' ? '#e67e22' :
                             isNightEvent ? '#607d8b' :
                             '#9b59b6'
          const emoji = event.event_type === 'phase_change' ? '📢 ' :
                       event.event_type === 'death' ? '💀 ' :
                       event.event_type === 'elimination' ? '⚖️ ' :
                       event.event_type === 'game_over' ? '🏆 ' :
                       event.event_type === 'seer_check' ? '🔮 ' :
                       event.event_type === 'werewolf_kill' ? '🗡️ ' :
                       event.event_type?.startsWith('witch') ? '🧪 ' : ''

          return (
            <div key={idx} style={{
              textAlign: 'center',
              padding: '10px 18px',
              marginBottom: 8,
              background: bgColor,
              borderRadius: 10,
              borderLeft: `3px solid ${borderColor}`,
            }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: event.event_type === 'death' ? '#e74c3c' : event.event_type === 'game_over' ? '#2ecc71' : '#ccc' }}>
                {emoji}{event.public_content}
                {viewer === 'god' && event.private_content && !isNightEvent && (
                  <span style={{ color: '#888', fontSize: 12 }}> ({event.private_content})</span>
                )}
              </span>
              {viewer === 'god' && isNightEvent && event.private_content && (
                <div style={{
                  marginTop: 4, padding: '4px 10px',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: 6, fontSize: 12, color: '#9eafb8',
                }}>
                  {event.private_content}
                </div>
              )}
            </div>
          )
        }

        if (event.event_type === 'speech') {
          const speakerColor = getSpeakerColor(event.player_id)
          const speechText = event.public_content?.replace(/^\d+号\s+\S+\s*[:：]\s*/, '') || ''
          const { action, speech } = parseActionParts(speechText)
          const thoughtKey = `speech-${event.id}`

          return (
            <div key={idx} style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 10,
              borderLeft: `4px solid ${speakerColor}`,
              padding: '12px 16px',
              marginBottom: 10,
              transition: 'all 0.2s',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: speakerColor }}>
                  💬 {playerName}
                </span>
                {viewer === 'god' && (
                  <span style={{
                    fontSize: 10, color: ROLE_COLORS[playerRole] || '#888',
                    background: (ROLE_COLORS[playerRole] || '#555') + '22',
                    padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                  }}>
                    {ROLE_LABELS[playerRole] || ''}
                  </span>
                )}
              </div>

              {action && (
                <div style={{
                  fontSize: 12, color: '#f0a050', fontStyle: 'italic',
                  background: 'rgba(240,160,80,0.06)',
                  padding: '4px 10px', borderRadius: 6, marginBottom: 8,
                  borderLeft: '2px solid #f0a050',
                }}>
                  🎭 {action}
                </div>
              )}

              <div style={{ fontSize: 14, color: '#ddd', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
                {speech}
              </div>

              {viewer === 'god' && event.reasoning_content && (
                <div style={{ marginTop: 8 }}>
                  <div
                    onClick={() => toggleThought(thoughtKey)}
                    style={{
                      fontSize: 11, color: '#607d8b', cursor: 'pointer',
                      padding: '4px 8px', borderRadius: 4,
                      background: 'rgba(96,125,139,0.08)',
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                    }}
                  >
                    💭 AI推理过程 {expandedThoughts.has(thoughtKey) ? '▲' : '▼'}
                  </div>
                  {expandedThoughts.has(thoughtKey) && (
                    <div style={{
                      marginTop: 4, padding: '8px 12px',
                      background: 'rgba(96,125,139,0.06)',
                      borderRadius: 8,
                      borderLeft: '2px solid #607d8b',
                      fontSize: 12, color: '#9eafb8', lineHeight: 1.6,
                      whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto',
                    }}>
                      {event.reasoning_content}
                    </div>
                  )}
                </div>
              )}

              {viewer === 'god' && event.internal_thought && (
                <div style={{
                  marginTop: 8, padding: '6px 10px',
                  background: 'rgba(155,89,182,0.06)',
                  borderRadius: 6,
                  borderLeft: '2px solid #9b59b6',
                }}>
                  <span style={{ fontSize: 10, color: '#9b59b6', fontWeight: 600 }}>OS：</span>
                  <span style={{ fontSize: 12, color: '#bba', fontStyle: 'italic' }}>
                    {event.internal_thought}
                  </span>
                </div>
              )}
            </div>
          )
        }

        if (event.event_type === 'vote') {
          const speakerColor = getSpeakerColor(event.player_id)
          const thoughtKey = `vote-${event.id}`

          return (
            <div key={idx} style={{
              padding: '4px 16px', marginBottom: 1, fontSize: 13,
              color: '#999',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ color: speakerColor, fontWeight: 600, fontSize: 11 }}>🗳</span>
                <span>{event.public_content}</span>
                {viewer === 'god' && event.internal_thought && (
                  <span style={{ color: '#9b59b6', fontStyle: 'italic', fontSize: 11 }}>
                    ({event.internal_thought})
                  </span>
                )}
              </div>
              {viewer === 'god' && event.reasoning_content && (
                <div style={{ marginTop: 2 }}>
                  <div
                    onClick={() => toggleThought(thoughtKey)}
                    style={{
                      fontSize: 10, color: '#607d8b', cursor: 'pointer',
                      padding: '2px 6px', borderRadius: 3,
                      display: 'inline-flex', alignItems: 'center', gap: 3,
                    }}
                  >
                    💭 {expandedThoughts.has(thoughtKey) ? '▲' : '▼'}
                  </div>
                  {expandedThoughts.has(thoughtKey) && (
                    <div style={{
                      marginTop: 2, padding: '6px 10px',
                      background: 'rgba(96,125,139,0.05)',
                      borderRadius: 6,
                      borderLeft: '2px solid #607d8b',
                      fontSize: 11, color: '#9eafb8', lineHeight: 1.5,
                      whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto',
                    }}>
                      {event.reasoning_content}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        }

        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
