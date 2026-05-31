import { AnimatePresence, motion } from 'framer-motion';
import BackgroundParticles from '../../components/BackgroundParticles';
import RoundTable from '../../components/RoundTable';
import BattleLog from '../../components/BattleLog';
import ChatBubble from '../../components/ChatBubble';
import MVPDialog from '../../components/MVPDialog';
import type { GameState, LogEntry, ChatItem, GamePlayer } from './useGameState';

const PHASE_LABELS: Record<string, string> = {
  waiting: 'WAITING',
  night_werewolf: 'NIGHT - Wolf Action',
  night_seer: 'NIGHT - Seer Check',
  night_witch: 'NIGHT - Witch Potion',
  day_speech: 'DAY - Speech',
  day_vote: 'DAY - Vote',
  day_result: 'DAY - Result',
  finished: 'GAME OVER',
};

interface GameLayoutProps {
  status: GameState;
  logs: LogEntry[];
  chatItems: ChatItem[];
  thinkingPlayers: Set<number>;
  isGodView: boolean;
  setIsGodView: (v: boolean) => void;
  mvpVisible: boolean;
  setMvpVisible: (v: boolean) => void;
  onNavigateHome: () => void;
}

export function GameLayout({
  status, logs, chatItems, thinkingPlayers,
  isGodView, setIsGodView, mvpVisible, setMvpVisible, onNavigateHome,
}: GameLayoutProps) {
  const winner = status.winner;
  const isFinished = status.phase === 'finished' || !!winner;

  return (
    <>
      <BackgroundParticles />

      <div className="game-layout">
        <BattleLog events={logs} />

        <div className="center-stage">
          <div className="phase-indicator-wrap">
            <span className="phase-badge">
              {PHASE_LABELS[status.phase] || status.phase.toUpperCase()} | Round {status.round_number}
            </span>
          </div>

          <RoundTable
            players={status.players}
            currentSpeakerId={status.current_speaker_id}
            isGodView={isGodView}
            phase={status.phase}
            events={status.events}
            winner={winner}
            thinkingPlayerIds={thinkingPlayers}
          />

          {isFinished && (
            <AnimatePresence>
              <motion.div
                className={`victory-fullscreen ${winner === 'werewolves' ? 'werewolf' : 'villager'}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 1.5, ease: 'easeInOut' }}
              >
                <motion.div
                  className="victory-icon"
                  initial={{ scale: 0, rotate: -30 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ duration: 0.8, ease: 'easeOut', delay: 0.3 }}
                >
                  {winner === 'werewolves' ? '🐺' : '🛡️'}
                </motion.div>
                <motion.h1
                  className="victory-title"
                  style={{ color: winner === 'werewolves' ? 'var(--accent-red)' : 'var(--accent-gold)' }}
                  initial={{ y: 30, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, ease: 'easeOut', delay: 0.8 }}
                >
                  {winner === 'werewolves' ? '狼人获胜' : '好人获胜'}
                </motion.h1>
                <motion.p
                  className="victory-subtitle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 1.2 }}
                >
                  {winner === 'werewolves' ? '暗夜降临，狼群咆哮' : '正义之光，驱散黑暗'}
                </motion.p>
                <motion.button
                  className="victory-back-btn"
                  onClick={onNavigateHome}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6, delay: 1.6 }}
                  whileHover={{ scale: 1.05 }}
                >
                  返回首页
                </motion.button>
              </motion.div>
            </AnimatePresence>
          )}

          <MVPDialog
            gameId={status.game_id}
            visible={mvpVisible}
            players={status.players.map(p => ({
              id: p.id, name: p.player_name, role: p.role || '',
              seat_number: p.seat_number, is_alive: p.is_alive,
            }))}
            onClose={() => setMvpVisible(false)}
          />
        </div>

        <div className="chat-panel">
          <div className="chat-header">
            <span>-- CHAT --</span>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={isGodView}
                onChange={(e) => setIsGodView(e.target.checked)}
                style={{ marginRight: 4 }}
              />
              God View
            </label>
          </div>
          <div className="chat-messages">
            {chatItems.map((item) => {
              if (item.type === 'system') {
                return <div key={item.id} className="chat-system-msg">{item.text}</div>;
              }
              return (
                <ChatBubble
                  key={item.id}
                  text={item.text}
                  speaker={item.speaker}
                  type={item.type}
                  typing={item.typing || false}
                />
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
