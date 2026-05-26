import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function RoomPage() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [roomId, setRoomId] = useState<number | null>(null)

  useEffect(() => {
    if (!roomCode) return
    let cancelled = false

    const lookup = async () => {
      try {
        const info = await fetch(`/api/rooms/lookup/${roomCode}`).then(r => r.json())
        if (!cancelled && info.id) {
          setRoomId(info.id)
        }
      } catch {}
    }

    lookup()
    return () => { cancelled = true }
  }, [roomCode])

  const handleStartGame = async () => {
    if (!roomId) {
      setError('找不到该房间，请先创建房间')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.startGame(roomId)
      navigate(`/game/${res.game_id}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lobby-container">
      <div className="lobby-card" style={{ width: 400, maxWidth: '90vw', textAlign: 'center' }}>
        <h1 className="lobby-title" style={{ fontSize: 24, marginBottom: 8 }}>🏠 房间等待</h1>
        <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>
          房间号：<strong style={{ color: '#9b59b6', fontSize: 24, letterSpacing: 6 }}>{roomCode}</strong>
        </p>

        <div style={{ marginBottom: 20, padding: 16, background: 'rgba(255,255,255,0.05)', borderRadius: 12 }}>
          <p style={{ fontSize: 13, color: '#aaa' }}>身份配置</p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
            <span style={{ padding: '4px 12px', borderRadius: 20, background: 'rgba(231,76,60,0.2)', color: '#e74c3c', fontSize: 12 }}>🐺 狼人×3</span>
            <span style={{ padding: '4px 12px', borderRadius: 20, background: 'rgba(243,156,18,0.2)', color: '#f39c12', fontSize: 12 }}>🔮 预言家×1</span>
            <span style={{ padding: '4px 12px', borderRadius: 20, background: 'rgba(155,89,182,0.2)', color: '#9b59b6', fontSize: 12 }}>🧪 女巫×1</span>
            <span style={{ padding: '4px 12px', borderRadius: 20, background: 'rgba(241,196,15,0.2)', color: '#f1c40f', fontSize: 12 }}>🏹 猎人×1</span>
            <span style={{ padding: '4px 12px', borderRadius: 20, background: 'rgba(52,152,219,0.2)', color: '#3498db', fontSize: 12 }}>👤 村民×3</span>
          </div>
        </div>

        <p style={{ color: '#aaa', fontSize: 13, marginBottom: 24, lineHeight: 1.6 }}>
          点击"开始观战"后，9 个 AI Agent 将自动进行完整对局，你将以观众身份实时观看。<br />
          <span style={{ color: '#9b59b6' }}>提示：可在对局页面切换上帝视角查看 AI 内心独白。</span>
        </p>

        <button
          onClick={handleStartGame}
          disabled={loading || !roomId}
          style={{
            width: '100%', padding: '14px 0', fontSize: 16,
            background: 'linear-gradient(135deg, #e74c3c, #e67e22)',
            color: '#fff',
          }}
        >
          {loading ? '正在启动...' : '🚀 开始 AI 自动对局'}
        </button>

        {error && (
          <p style={{ color: '#e74c3c', fontSize: 13, marginTop: 16 }}>
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
