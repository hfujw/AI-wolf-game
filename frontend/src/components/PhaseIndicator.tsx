const PHASE_LABELS: Record<string, string> = {
  night_werewolf: '🌙 狼人行动中',
  night_seer: '🌙 预言家查验中',
  night_witch: '🌙 女巫用药中',
  day_announce: '☀️ 天亮公告',
  day_speech: '☀️ 发言环节',
  day_vote: '☀️ 投票环节',
  elimination: '⚖️ 放逐结算',
  game_over: '🏆 游戏结束',
  waiting: '⏳ 等待开始',
}

export default function PhaseIndicator({ phase, round }: { phase: string; round: number }) {
  const label = PHASE_LABELS[phase] || phase
  const isNight = phase.startsWith('night')

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 16px', borderRadius: 20,
      background: isNight ? 'rgba(52,73,94,0.3)' : 'rgba(241,196,15,0.1)',
      border: `1px solid ${isNight ? '#34495e' : '#f1c40f'}`,
    }}>
      <span style={{ fontSize: 14 }}>{label}</span>
      {round > 0 && (
        <span style={{ fontSize: 12, color: '#888', marginLeft: 4 }}>
          第 {round} 轮
        </span>
      )}
    </div>
  )
}
