import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import BackgroundParticles from '../components/BackgroundParticles';
import RoundTable from '../components/RoundTable';
import BattleLog from '../components/BattleLog';
import PhaseOverlay, { DawnBanner, DawnInfo, NightToast } from '../components/PhaseOverlay';
import ChatBubble from '../components/ChatBubble';
import MVPDialog from '../components/MVPDialog';
import { useWebSocket } from '../hooks/useWebSocket';
import type { WSEvent, Player as ApiPlayer, GameStatus } from '../types';
import { api } from '../services/api';
import {
  playNightSound,
  playDawnSound,
  playVoteTicking,
  playVictorySound,
  playDefeatSound,
  playVoteResultSound,
  playKnifeSound,
  initAudio,
} from '../utils/sound';

interface Player {
  id: number;
  player_name: string;
  seat_number: number;
  role: string;
  personality: string;
  is_alive: boolean;
}

interface GameEvent {
  event_type: string;
  player_id: number;
  role: string;
  content: string;
  phase: string;
  round_number: number;
}

function mapGameStatus(raw: GameStatus): GameState {
  const players: Player[] = (raw.alive_players || []).map(p => ({
    id: p.id,
    player_name: p.name || '',
    seat_number: p.seat_number,
    role: p.role || '',
    personality: (p as any).personality || '',
    is_alive: p.is_alive,
  }));

  const events: GameEvent[] = (raw.events || []).map(e => ({
    event_type: e.event_type,
    player_id: e.player_id ?? 0,
    role: (e as any).role || '',
    content: e.public_content || '',
    phase: e.phase,
    round_number: e.round_number,
  }));

  return {
    game_id: raw.game_id,
    phase: raw.phase,
    round_number: raw.round_number,
    winner: raw.winner,
    players,
    events,
    current_speaker_id: (raw as any).current_speaker_id ?? null,
  };
}

interface GameState {
  game_id: number;
  phase: string;
  round_number: number;
  winner: string | null;
  players: Player[];
  events: GameEvent[];
  current_speaker_id: number | null;
}

interface LogEntry {
  id: number;
  type: 'system' | 'death' | 'action' | 'speech' | 'narrator';
  text: string;
  timestamp: number;
}

interface ChatItem {
  id: string;
  text: string;
  speaker: string;
  type: 'speech' | 'thought' | 'system';
  typing: boolean;
  systemType?: 'phase' | 'vote';
}

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

function buildLogs(events: GameEvent[], players: Player[]): LogEntry[] {
  const seatMap = new Map<number, number>();
  players.forEach(p => seatMap.set(p.id, p.seat_number));

  return events.map((e, i) => {
    const seat = seatMap.get(e.player_id);
    const seatStr = seat ? `${seat}号` : '';
    let type: LogEntry['type'] = 'system';
    let text = '';

    if (e.event_type === 'system') {
      type = 'system';
      text = e.content;
    } else if (e.event_type === 'death') {
      type = 'death';
      text = e.content;
    } else if (e.event_type === 'action') {
      type = 'action';
      text = `${seatStr} ${e.content}`;
    } else if (e.event_type === 'speech') {
      type = 'speech';
      text = `${seatStr}: "${e.content}"`;
    } else {
      type = 'system';
      text = e.content || e.event_type;
    }

    return { id: i, type, text, timestamp: Date.now() };
  });
}

function buildDawnInfo(events: GameEvent[], players: Player[]): DawnInfo | null {
  const nightDeaths = events.filter(e => e.event_type === 'death' && e.phase?.startsWith('night'));
  if (nightDeaths.length === 0) return { type: 'safe', text: '平安夜' };
  const deadSeats = nightDeaths.map(e => {
    const match = e.content?.match(/(\d+)号/);
    return match ? parseInt(match[1], 10) : null;
  }).filter(Boolean) as number[];
  if (deadSeats.length === 0) return { type: 'safe', text: '平安夜' };
  return { type: 'death', text: `#${deadSeats.join('号、')}号玩家 倒牌` };
}

function buildPhaseSystemMsg(phase: string): string {
  switch (phase) {
    case 'night_werewolf': return '⏳ 狼人正在行动...';
    case 'night_seer': return '⏳ 预言家正在查验...';
    case 'night_witch': return '⏳ 女巫正在使用药水...';
    case 'day_announce': return '📢 天亮了，请睁眼';
    case 'day_speech': return '📢 发言阶段开始';
    case 'day_vote': return '📢 投票阶段开始';
    default: return '';
  }
}

export default function GamePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const [isGodView, setIsGodView] = useState(false);
  const [status, setStatus] = useState<GameState | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [dawnInfo, setDawnInfo] = useState<DawnInfo | null>(null);
  const [nightToast, setNightToast] = useState<NightToast | null>(null);
  const [mvpVisible, setMvpVisible] = useState(false);
  const [gameFinished, setGameFinished] = useState(false);
  const [thinkingPlayers, setThinkingPlayers] = useState<Set<number>>(new Set());
  const statusRef = useRef<GameState | null>(null);
  const logsRef = useRef<LogEntry[]>([]);
  const chatIdRef = useRef(0);
  const prevPhaseRef = useRef<string>('');
  const processedChatSet = useRef<Set<string>>(new Set());
  const isFirstPhaseRef = useRef(true);
  const nightToastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const NIGHT_SUB_TOASTS: Record<string, NightToast> = {
    night_werewolf: { icon: '🐺', text: '狼人行动' },
    night_seer: { icon: '🔮', text: '预言家查验' },
    night_witch: { icon: '🧪', text: '女巫行动' },
    hunter_shoot: { icon: '🏹', text: '猎人开枪' },
  };

  function showNightToast(phase: string) {
    if (nightToastTimerRef.current) clearTimeout(nightToastTimerRef.current);
    const toast = NIGHT_SUB_TOASTS[phase];
    if (toast) {
      setNightToast(toast);
      nightToastTimerRef.current = setTimeout(() => setNightToast(null), 2500);
    }
  }

  const addSystemChat = useCallback((text: string, systemType?: 'phase' | 'vote') => {
    chatIdRef.current++;
    const cid = `sys-${chatIdRef.current}`;
    const item: ChatItem = { id: cid, text, speaker: '', type: 'system', typing: false, systemType };
    setChatItems(prev => [...prev, item]);
  }, []);

  const handleWSEvent = useCallback((event: WSEvent) => {
    const currentStatus = statusRef.current;
    if (!currentStatus) return;

    if (event.event_type === 'agent_thinking') {
      const pid = event.player_id;
      if (pid) {
        setThinkingPlayers(prev => new Set(prev).add(pid));
      }
      return;
    }

    if (event.event_type === 'phase_change') {
      const prevPhase = currentStatus.phase;
      api.getGameStatus(Number(gameId)).then((res) => {
        if (res) {
          const data = mapGameStatus(res);
          statusRef.current = data;
          setStatus(data);
          prevPhaseRef.current = prevPhase;
          const newLogs = buildLogs(data.events || [], data.players || []);
          logsRef.current = newLogs;
          setLogs(newLogs);

          const oldWasNight = prevPhase?.startsWith('night');
          const newIsDay = data.phase?.startsWith('day');
          if (oldWasNight && newIsDay) {
            const dawn = buildDawnInfo(data.events || [], data.players || []);
            setDawnInfo(dawn);
            setTimeout(() => setDawnInfo(null), 4000);
            playDawnSound();
          }

          const newIsNight = data.phase?.startsWith('night');
          if (newIsNight && !prevPhase?.startsWith('night')) {
            playNightSound();
          }

          if (data.phase === 'day_vote') {
            playVoteTicking();
          }

          const isNowFinished = data.phase === 'finished' || data.phase === 'game_over' || !!data.winner;
          if (isNowFinished && !gameFinished) {
            setGameFinished(true);
            const isWolfWin = data.winner === 'werewolves';
            if (isWolfWin) {
              playVictorySound();
            } else {
              playDefeatSound();
            }
            setTimeout(() => setMvpVisible(true), 2000);
          }

          setThinkingPlayers(new Set());
        }
      }).catch(() => {});
      return;
    }

    const pid = event.player_id;
    if (pid) {
      setThinkingPlayers(prev => {
        const next = new Set(prev);
        next.delete(pid);
        return next;
      });
    }

    if (event.event_type === 'speech') {
      const speechKey = `${event.player_id}_${event.round_number}_${event.data?.public_content || ''}`;
      if (processedChatSet.current.has(speechKey)) return;
      processedChatSet.current.add(speechKey);
      const playerName = event.data?.player_name || `${event.player_id}号`;
      const text = event.data?.public_content || '';
      chatIdRef.current++;
      const chatId = `speech-${chatIdRef.current}`;
      const newItem: ChatItem = { id: chatId, text, speaker: playerName, type: 'speech', typing: true };
      setChatItems(prev => [...prev, newItem]);
      const typingDuration = Math.min(text.length * 60, 4000);
      setTimeout(() => {
        setChatItems(prev => prev.map(c => c.id === chatId ? { ...c, typing: false } : c));
      }, typingDuration);
    }

    if (event.event_type === 'speech' && isGodView) {
      const thought = event.data?.internal_thought || event.data?.reasoning_content;
      if (thought) {
        const thoughtKey = `thought_${event.player_id}_${event.round_number}`;
        if (processedChatSet.current.has(thoughtKey)) return;
        processedChatSet.current.add(thoughtKey);
        chatIdRef.current++;
        const tId = `thought-${chatIdRef.current}`;
        const thoughtItem: ChatItem = { id: tId, text: thought, speaker: event.data?.player_name || `${event.player_id}号`, type: 'thought', typing: false };
        setChatItems(prev => [...prev, thoughtItem]);
      }
    }

    if (event.event_type === 'action' && event.phase === 'night_werewolf') {
      playKnifeSound();
    }

    if (event.event_type === 'death' && event.phase === 'day_announce') {
      const content = event.data?.public_content || '';
      const match = content.match(/(\d+)号/);
      if (match) {
        addSystemChat(`✅ 投票结果：#${match[1]}号被放逐`, 'vote');
      }
      playVoteResultSound();
    }

    const newEvent: GameEvent = {
      event_type: event.event_type,
      player_id: event.player_id ?? 0,
      role: '',
      content: event.data?.public_content || event.data?.private_content || '',
      phase: event.phase || currentStatus.phase,
      round_number: event.round_number || currentStatus.round_number,
    };

    const updatedEvents = [...currentStatus.events, newEvent];
    const updatedStatus = { ...currentStatus, events: updatedEvents, phase: event.phase || currentStatus.phase };
    statusRef.current = updatedStatus;
    setStatus(updatedStatus);

    const newLogs = buildLogs(updatedEvents, currentStatus.players);
    logsRef.current = newLogs;
    setLogs(newLogs);
  }, [gameId, gameFinished, isGodView, addSystemChat]);

  const { connected } = useWebSocket(
    Number(gameId),
    'god',
    handleWSEvent
  );

  useEffect(() => {
    initAudio();
  }, []);

  useEffect(() => {
    if (!status) return;
    const phase = status.phase;
    const prev = prevPhaseRef.current;
    if (isFirstPhaseRef.current) {
      isFirstPhaseRef.current = false;
      prevPhaseRef.current = phase;
      showNightToast(phase);
      return;
    }
    if (phase !== prev && prev !== '') {
      const sysMsg = buildPhaseSystemMsg(phase);
      if (sysMsg) addSystemChat(sysMsg, 'phase');
      showNightToast(phase);
    }
    prevPhaseRef.current = phase;
  }, [status?.phase, addSystemChat]);

  useEffect(() => {
    api.getGameStatus(Number(gameId)).then((res) => {
      if (res) {
        const data = mapGameStatus(res);
        statusRef.current = data;
        setStatus(data);
        const newLogs = buildLogs(data.events || [], data.players || []);
        logsRef.current = newLogs;
        setLogs(newLogs);
        prevPhaseRef.current = data.phase || '';
      }
    });

    const poll = setInterval(() => {
      api.getGameStatus(Number(gameId)).then((res) => {
        if (res) {
          const data = mapGameStatus(res);
          const newPhase = data.phase;
          const oldPhase = statusRef.current?.phase;
          if (newPhase !== oldPhase) {
            const prevPhase = oldPhase;
            statusRef.current = data;
            setStatus(data);
            const newLogs = buildLogs(data.events || [], data.players || []);
            logsRef.current = newLogs;
            setLogs(newLogs);

            const oldWasNight = prevPhase?.startsWith('night');
            const newIsDay = newPhase?.startsWith('day');
            if (oldWasNight && newIsDay) {
              const dawn = buildDawnInfo(data.events || [], data.players || []);
              setDawnInfo(dawn);
              setTimeout(() => setDawnInfo(null), 4000);
              playDawnSound();
            }

            const newIsNight = newPhase?.startsWith('night');
            if (newIsNight && !prevPhase?.startsWith('night')) {
              playNightSound();
            }

            if (newPhase === 'day_vote') {
              playVoteTicking();
            }

            const isNowFinished = newPhase === 'finished' || newPhase === 'game_over' || !!data.winner;
            if (isNowFinished && !gameFinished) {
              setGameFinished(true);
              const isWolfWin = data.winner === 'werewolves';
              if (isWolfWin) {
                playVictorySound();
              } else {
                playDefeatSound();
              }
              setTimeout(() => setMvpVisible(true), 2000);
            }

            setThinkingPlayers(new Set());
          }
        }
      }).catch(() => {});
    }, 2000);

    return () => clearInterval(poll);
  }, [gameId]);

  if (!status) {
    return (
      <div className="lobby-container">
        <BackgroundParticles />
        <h1 className="lobby-title">Loading...</h1>
      </div>
    );
  }

  const winner = status.winner;
  const isFinished = status.phase === 'finished' || !!winner;
  const isNight = status.phase.startsWith('night');
  const showDawnOverlay = !!dawnInfo;

  return (
    <>
      <BackgroundParticles />
      <PhaseOverlay visible={isNight || showDawnOverlay} dawnInfo={showDawnOverlay ? dawnInfo : null} nightToast={nightToast} />

      <AnimatePresence>
        {dawnInfo && (
          <DawnBanner
            info={dawnInfo}
            onDone={() => {}}
          />
        )}
      </AnimatePresence>

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
                  onClick={() => navigate('/')}
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
            gameId={Number(gameId)}
            visible={mvpVisible}
            players={status.players.map(p => ({ id: p.id, name: p.player_name, role: p.role, seat_number: p.seat_number, is_alive: p.is_alive })) as ApiPlayer[]}
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
                return (
                  <div
                    key={item.id}
                    className={`chat-system-msg ${item.systemType === 'phase' ? 'phase-notice' : item.systemType === 'vote' ? 'vote-result' : ''}`}
                  >
                    {item.text}
                  </div>
                );
              }
              return (
                <ChatBubble
                  key={item.id}
                  text={item.text}
                  speaker={item.speaker}
                  type={item.type}
                  typing={item.typing}
                />
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
