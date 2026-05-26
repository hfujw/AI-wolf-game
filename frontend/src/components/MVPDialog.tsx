import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../services/api';
import type { GameStats, Player } from '../types';
import { ROLE_LABELS } from '../types';

interface MVPDialogProps {
  gameId: number;
  visible: boolean;
  players: Player[];
  onClose: () => void;
}

function calcMVP(stats: GameStats, players: Player[]): { name: string; role: string; score: number; votesCorrect: number; votesTotal: number; speeches: number; skillUses: number; survivedRounds: number } | null {
  let bestId = -1;
  let bestScore = -1;
  for (const [idStr, ps] of Object.entries(stats.player_stats)) {
    const pid = parseInt(idStr, 10);
    if (ps.score > bestScore) {
      bestScore = ps.score;
      bestId = pid;
    }
  }
  if (bestId < 0) return null;
  const player = players.find(p => p.id === bestId);
  const ps = stats.player_stats[bestId];
  return {
    name: player?.name || `${bestId}号`,
    role: ROLE_LABELS[ps.role] || ps.role,
    score: ps.score,
    votesCorrect: ps.votes_correct,
    votesTotal: ps.votes_total,
    speeches: ps.speeches,
    skillUses: ps.skill_uses,
    survivedRounds: ps.survived_rounds,
  };
}

export default function MVPDialog({ gameId, visible, players, onClose }: MVPDialogProps) {
  const [stats, setStats] = useState<GameStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    api.getGameStats(gameId).then(s => {
      setStats(s);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [gameId, visible]);

  const mvp = stats ? calcMVP(stats, players) : null;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="mvp-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5, ease: 'easeInOut' }}
          onClick={onClose}
        >
          <motion.div
            className="mvp-dialog"
            initial={{ scale: 0.8, opacity: 0, y: 40 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.8, opacity: 0, y: 40 }}
            transition={{ duration: 0.5, ease: 'easeInOut' }}
            onClick={e => e.stopPropagation()}
          >
            {loading ? (
              <div className="mvp-loading">计算中...</div>
            ) : mvp ? (
              <>
                <motion.div
                  className="mvp-crown"
                  animate={{ rotate: [0, -5, 5, -3, 0], scale: [1, 1.1, 1] }}
                  transition={{ duration: 1, ease: 'easeInOut', repeat: Infinity, repeatDelay: 2 }}
                >
                  👑
                </motion.div>
                <div className="mvp-title">MVP</div>
                <div className="mvp-player-name">{mvp.name}</div>
                <div className="mvp-player-role">{mvp.role}</div>
                <div className="mvp-stats">
                  <div className="mvp-stat-item">
                    <div className="mvp-stat-value">{mvp.score}</div>
                    <div className="mvp-stat-label">综合得分</div>
                  </div>
                  <div className="mvp-stat-item">
                    <div className="mvp-stat-value">{mvp.speeches}</div>
                    <div className="mvp-stat-label">发言次数</div>
                  </div>
                  <div className="mvp-stat-item">
                    <div className="mvp-stat-value">{mvp.votesCorrect}/{mvp.votesTotal}</div>
                    <div className="mvp-stat-label">投票正确率</div>
                  </div>
                  <div className="mvp-stat-item">
                    <div className="mvp-stat-value">{mvp.survivedRounds}</div>
                    <div className="mvp-stat-label">存活轮次</div>
                  </div>
                  {mvp.skillUses > 0 && (
                    <div className="mvp-stat-item" style={{ gridColumn: '1 / -1' }}>
                      <div className="mvp-stat-value">{mvp.skillUses}</div>
                      <div className="mvp-stat-label">技能使用次数</div>
                    </div>
                  )}
                </div>
                <button className="mvp-close-btn" onClick={onClose}>返回</button>
              </>
            ) : (
              <div className="mvp-loading">暂无统计数据</div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
