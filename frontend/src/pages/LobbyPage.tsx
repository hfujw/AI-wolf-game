import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import BackgroundParticles from '../components/BackgroundParticles';
import { api } from '../services/api';
import styles from './LobbyPage.module.css';

const ROLES = [
  { name: '狼人', icon: '🐺', count: 3, desc: '夜晚刀人，白天伪装成好人。狼队友互知身份，通过隐晦配合引导投票。' },
  { name: '预言家', icon: '🔮', count: 1, desc: '每晚查验一人身份（好人/狼人）。白天报查验结果，带队归票。' },
  { name: '女巫', icon: '🧪', count: 1, desc: '拥有一瓶解药（救人）和一瓶毒药（杀人），各只能用一次。' },
  { name: '猎人', icon: '🏹', count: 1, desc: '被刀或被票出局时可以开枪带走一人（被毒则不可）。' },
  { name: '村民', icon: '👤', count: 3, desc: '无特殊技能。靠听发言、分析逻辑、投票放逐来找出狼人。' },
];

export default function LobbyPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [flippedCard, setFlippedCard] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await api.startGame();
      navigate(`/game/${res.game_id}`);
    } catch (e: any) {
      alert(e.message || '启动失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <BackgroundParticles />

      <motion.div
        className={styles.content}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      >
        <h1 className={styles.title}>🐺 AI 狼人杀</h1>
        <p className={styles.subtitle}>9 AI Agent 策略博弈 · 暗黑剧场</p>

        <div className={styles.ruleCard}>
          <p>
            3🐺狼人 · 1🔮预言家 · 1🧪女巫 · 1🏹猎人 · 3👤村民 | 屠边规则
          </p>
        </div>

        <div className={styles.roleGrid}>
          {ROLES.map((role) => (
            <motion.div
              key={role.name}
              className={`${styles.roleCard} ${flippedCard === role.name ? styles.flipped : ''}`}
              onClick={() => setFlippedCard(flippedCard === role.name ? null : role.name)}
              whileHover={{ y: -6 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <div className={styles.roleCardInner}>
                <div className={styles.roleCardFront}>
                  <span className={styles.roleIcon}>{role.icon}</span>
                  <span className={styles.roleCount}>×{role.count}</span>
                  <span className={styles.roleName}>{role.name}</span>
                </div>
                <div className={styles.roleCardBack}>
                  <p>{role.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.button
          className={styles.startBtn}
          onClick={handleStart}
          disabled={loading}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
        >
          {loading ? '🎭 正在组建剧场...' : '🎭 开始游戏'}
        </motion.button>

        <p className={styles.footer}>
          FastAPI · React 18 · TypeScript · Framer Motion · 多 Agent 协作
        </p>
      </motion.div>
    </div>
  );
}
