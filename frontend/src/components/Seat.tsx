import { motion, AnimatePresence } from 'framer-motion';

interface SeatProps {
  seatNumber: number;
  playerName: string;
  isAlive: boolean;
  isCurrentSpeaker: boolean;
  angle: number;
  radius: number;
  role?: string;
  phase?: string;
  isThinking?: boolean;
  isSpeaker?: boolean;
  voteLabel?: string | null;
  eliminated?: boolean;
  showRole?: boolean;
  winnerClass?: string;
  onClick?: () => void;
}

const AVATAR_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#2980b9', '#c0392b'];

const ROLE_LABELS_ZH: Record<string, string> = {
  werewolf: '狼人', seer: '预言家', witch: '女巫', hunter: '猎人', villager: '村民',
};

const ROLE_COLORS: Record<string, string> = {
  werewolf: '#ef4444', seer: '#f59e0b', witch: '#8b5cf6', hunter: '#f1c40f', villager: '#3b82f6',
};

function getGlowClass(phase: string | undefined, role: string | undefined): string {
  if (!phase || !role) return '';
  if (phase === 'night_werewolf' && role === 'werewolf') return 'glow-wolf';
  if (phase === 'night_seer' && role === 'seer') return 'glow-seer';
  if (phase === 'night_witch' && role === 'witch') return 'glow-witch';
  return '';
}

const SPEAKER_TABLE_CX = 250;
const SPEAKER_TABLE_CY = 250;
const SPEAKER_TABLE_RADIUS = 180;

export default function Seat({
  seatNumber, playerName, isAlive, isCurrentSpeaker, angle, radius, role, phase,
  isThinking, isSpeaker, voteLabel, eliminated, showRole, winnerClass, onClick,
}: SeatProps) {
  const rad = (angle * Math.PI) / 180;
  const x = SPEAKER_TABLE_CX + radius * Math.cos(rad);
  const y = SPEAKER_TABLE_CY + radius * Math.sin(rad);
  const color = AVATAR_COLORS[(seatNumber - 1) % AVATAR_COLORS.length];
  const glowClass = getGlowClass(phase, role);
  const roleLabel = showRole && role ? ROLE_LABELS_ZH[role] || role : null;
  const roleColor = role ? ROLE_COLORS[role] || '#666' : '#666';

  return (
    <motion.div
      className={`seat ${!isAlive && !eliminated ? 'dead' : ''} ${isCurrentSpeaker ? 'current' : ''} ${glowClass} ${isThinking ? 'thinking' : ''} ${isSpeaker ? 'speaker-focus' : ''} ${winnerClass || ''}`}
      style={{ left: x, top: y }}
      onClick={onClick}
    >
      <AnimatePresence>
        {voteLabel && (
          <motion.div
            className={`vote-box ${voteLabel !== '投票' ? 'voted' : ''}`}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {voteLabel}
          </motion.div>
        )}
      </AnimatePresence>

      {roleLabel && (
        <div
          className="god-role-badge"
          style={{ borderColor: roleColor, color: roleColor, background: `${roleColor}22` }}
        >
          {roleLabel}
        </div>
      )}

      <div className="seat-avatar" style={{ background: isAlive ? color : '#555' }}>
        {isThinking && (
          <div className="thinking-dots">
            <span className="dot" style={{ animationDelay: '0s' }} />
            <span className="dot" style={{ animationDelay: '0.2s' }} />
            <span className="dot" style={{ animationDelay: '0.4s' }} />
          </div>
        )}
        {!isThinking && playerName[0]}
      </div>
      {isThinking && <div className="thinking-text">思考中...</div>}
      {!isThinking && (
        <div className="seat-name">
          {seatNumber}号 {playerName}
        </div>
      )}
    </motion.div>
  );
}
