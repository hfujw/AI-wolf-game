import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function LobbyPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleStart = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.startGame()
      navigate(`/game/${res.game_id}`)
    } catch (e: any) {
      setError(e.message || '启动失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lobby-container">
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <h1 className="lobby-title" style={{ fontSize: 48 }}>🐺 AI 狼人杀</h1>
        <p className="lobby-subtitle" style={{ fontSize: 16, marginTop: 8 }}>
          多 AI Agent 策略博弈 · 9 人标准局
        </p>
      </div>

      <div className="lobby-card" style={{ width: 400, maxWidth: '90vw' }}>
        <p style={{ color: '#aaa', fontSize: 13, marginBottom: 16, lineHeight: 1.6 }}>
          系统将自动分配 9 个 AI Agent（3狼人 · 1预言家 · 1女巫 · 1猎人 · 3村民）进行对局。
        </p>
        <button
          onClick={handleStart}
          disabled={loading}
          style={{
            width: '100%', padding: '14px 0', fontSize: 16,
            background: 'linear-gradient(135deg, #9b59b6, #3498db)',
            color: '#fff',
          }}
        >
          {loading ? '启动中...' : '开始游戏'}
        </button>
        {error && (
          <p style={{ color: '#e74c3c', fontSize: 13, marginTop: 16, textAlign: 'center' }}>
            {error}
          </p>
        )}
      </div>

      <div style={{ marginTop: 40, textAlign: 'center' }}>
        <p style={{ color: '#555', fontSize: 12 }}>
          身份配置：狼人×3 · 预言家×1 · 女巫×1 · 猎人×1 · 村民×3 | 屠边规则
        </p>
      </div>
    </div>
  )
}
