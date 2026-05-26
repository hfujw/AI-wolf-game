import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

export default function LobbyPage() {
  const navigate = useNavigate()
  const [playerName, setPlayerName] = useState('')
  const [roomCode, setRoomCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'create' | 'join'>('create')

  const handleCreate = async () => {
    setLoading(true)
    setError('')
    try {
      const room = await api.createRoom()
      navigate(`/room/${room.room_code}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleJoin = async () => {
    if (!roomCode.trim()) {
      setError('请输入房间号')
      return
    }
    setLoading(true)
    setError('')
    try {
      navigate(`/room/${roomCode.trim().toUpperCase()}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lobby-container">
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <h1 className="lobby-title" style={{ fontSize: 48 }}>🐺 AI 狼人杀</h1>
        <p className="lobby-subtitle" style={{ fontSize: 16, marginTop: 8 }}>
          多 AI Agent 策略博弈 · 9 人标准局</p>
      </div>

      <div className="lobby-card" style={{ width: 400, maxWidth: '90vw' }}>
        <div style={{ display: 'flex', marginBottom: 24, borderRadius: 8, overflow: 'hidden', border: '1px solid #333' }}>
          <button
            onClick={() => { setMode('create'); setError('') }}
            style={{
              flex: 1, borderRadius: 0, padding: '12px 0',
              background: mode === 'create' ? '#9b59b6' : 'transparent',
              color: mode === 'create' ? '#fff' : '#888',
            }}
          >
            创建房间
          </button>
          <button
            onClick={() => { setMode('join'); setError('') }}
            style={{
              flex: 1, borderRadius: 0, padding: '12px 0',
              background: mode === 'join' ? '#9b59b6' : 'transparent',
              color: mode === 'join' ? '#fff' : '#888',
            }}
          >
            加入房间
          </button>
        </div>

        {mode === 'create' ? (
          <div>
            <p style={{ color: '#aaa', fontSize: 13, marginBottom: 16, lineHeight: 1.6 }}>
              创建房间后，系统将自动分配 9 个 AI Agent（3狼人·1预言家·1女巫·1猎人·3村民）进行对局。
            </p>
            <button
              onClick={handleCreate}
              disabled={loading}
              style={{
                width: '100%', padding: '14px 0', fontSize: 16,
                background: 'linear-gradient(135deg, #9b59b6, #3498db)',
                color: '#fff',
              }}
            >
              {loading ? '创建中...' : '创建房间并开始观战'}
            </button>
          </div>
        ) : (
          <div>
            <input
              type="text"
              placeholder="输入4位房间号，如 ABCD"
              value={roomCode}
              onChange={(e) => { setRoomCode(e.target.value.toUpperCase()); setError('') }}
              maxLength={4}
              style={{ width: '100%', marginBottom: 16, textAlign: 'center', letterSpacing: 4, fontSize: 18 }}
            />
            <button
              onClick={handleJoin}
              disabled={loading}
              style={{
                width: '100%', padding: '14px 0', fontSize: 16,
                background: 'linear-gradient(135deg, #9b59b6, #3498db)',
                color: '#fff',
              }}
            >
              {loading ? '加入中...' : '加入房间'}
            </button>
          </div>
        )}

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
