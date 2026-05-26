import { motion, AnimatePresence } from 'framer-motion';
import type { IdentityReveal } from './RoundTable';

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
  identityReveal?: IdentityReveal | null;
  voteLabel?: string | null;
  shaking?: boolean;
  eliminated?: boolean;
  winnerClass?: string;
  showRole?: boolean;
  targetGlow?: string | null;
  onClick?: () => void;
}

const ROLE_LABELS_ZH: Record<string, string> = {
  werewolf: '狼人',
  seer: '预言家',
  witch: '女巫',
  hunter: '猎人',
  villager: '村民',
};

const ROLE_COLORS: Record<string, string> = {
  werewolf: '#ef4444',
  seer: '#f59e0b',
  witch: '#8b5cf6',
  hunter: '#f1c40f',
  villager: '#3b82f6',
};

const AVATAR_COLORS = [
  '#f59e0b', '#3b82f6', '#ef4444', '#22c55e', '#8b5cf6', '#06b6d4',
];

function getGlowClass(phase: string | undefined, role: string | undefined): string {
  if (!phase || !role) return '';
  if (phase === 'night_werewolf' && role === 'werewolf') return 'glow-wolf';
  if (phase === 'night_seer' && role === 'seer') return 'glow-seer';
  if (phase === 'night_witch' && role === 'witch') return 'glow-witch';
  return '';
}

export default function Seat({
  seatNumber,
  playerName,
  isAlive,
  isCurrentSpeaker,
  angle,
  radius,
  role,
  phase,
  isThinking,
  isSpeaker,
  identityReveal,
  voteLabel,
  shaking,
  eliminated,
  winnerClass,
  showRole,
  targetGlow,
  onClick,
}: SeatProps) {
  const TABLE_CX = 250;
  const TABLE_CY = 250;
  const TABLE_RADIUS = 180;
  const rad = (angle * Math.PI) / 180;

  let x: number;
  let y: number;

  if (isSpeaker) {
    x = TABLE_CX - 36;
    y = TABLE_CY - TABLE_RADIUS - 10;
  } else {
    x = TABLE_CX + radius * Math.cos(rad) - 36;
    y = TABLE_CY + radius * Math.sin(rad) - 36;
  }

  const color = AVATAR_COLORS[(seatNumber - 1) % AVATAR_COLORS.length];
  const glowClass = getGlowClass(phase, role);
  const roleLabel = showRole && role ? ROLE_LABELS_ZH[role] || role : null;
  const roleColor = role ? ROLE_COLORS[role] || '#666' : '#666';

  return (
    <motion.div
      className={`seat ${!isAlive && !eliminated ? 'dead' : ''} ${isCurrentSpeaker ? 'current' : ''} ${glowClass} ${isThinking ? 'thinking' : ''} ${isSpeaker ? 'speaker-focus' : ''} ${shaking ? 'shaking' : ''} ${winnerClass || ''}`}
      style={{ left: x, top: y }}
      animate={isSpeaker ? { scale: 1.2, left: x, top: y } : { scale: 1, left: x, top: y }}
      transition={{ duration: 0.5, ease: 'easeInOut' }}
      onClick={onClick}
    >
      <AnimatePresence>
        {voteLabel && (
          <motion.div
            className={`vote-box ${voteLabel !== '投票' ? 'voted' : ''}`}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            {voteLabel}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {identityReveal && (
          <motion.div
            className={`identity-badge ${identityReveal.type}`}
            initial={{ scale: 0, opacity: 0, y: 5 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0, opacity: 0, y: -5 }}
            transition={{ duration: 0.4, ease: 'easeInOut' }}
          >
            {identityReveal.label}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {roleLabel && (
          <motion.div
            className="god-role-badge"
            style={{ borderColor: roleColor, color: roleColor, background: `${roleColor}22` }}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: 'easeInOut' }}
          >
            {roleLabel}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {targetGlow && (
          <motion.div
            className={`target-glow-ring ${targetGlow}`}
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.5, ease: 'easeInOut' }}
          />
        )}
      </AnimatePresence>

      <div
        className={`seat-avatar ${isAlive && !eliminated ? 'alive' : 'dead-avatar'} ${eliminated ? 'eliminated' : ''}`}
        style={{ background: isAlive && !eliminated ? color : '#374151' }}
      >
        {seatNumber}
      </div>

      <AnimatePresence>
        {isThinking && (
          <motion.div
            className="thinking-indicator"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <span className="thinking-gear">⚙️</span>
            <span className="thinking-text">思考中...</span>
          </motion.div>
        )}
      </AnimatePresence>

      {!isThinking && (
        <>
          <div className="seat-name">{playerName}</div>
          <span className={`seat-status ${isAlive && !eliminated ? 'alive' : 'dead'}`}>
            {eliminated ? '淘汰' : (isAlive ? '存活' : '死亡')}
          </span>
        </>
      )}
    </motion.div>
  );
}
