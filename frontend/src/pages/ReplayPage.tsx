import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { ReplayData, ReplayPlayer } from '../types';
import RoundTable from '../components/RoundTable';
import BattleLog from '../components/BattleLog';
import ReplayControls from '../components/ReplayControls';

interface ReplayEventItem {
  round_number: number;
  phase: string;
  player_id: number | null;
  player_name: string | null;
  event_type: string;
  public_content: string | null;
  private_content: string | null;
  internal_thought: string | null;
  reasoning_content: string | null;
}

interface LogEntry {
  id: number;
  type: 'system' | 'death' | 'action' | 'speech';
  text: string;
  timestamp: number;
}

interface ChatEntry {
  id: number;
  speaker: string;
  text: string;
  type: 'speech' | 'thought';
}

function buildLogs(events: ReplayEventItem[], seatMap: Map<number, number>): LogEntry[] {
  return events.map((e, i) => {
    const seat = e.player_id ? seatMap.get(e.player_id) : undefined;
    const seatStr = seat ? `${seat}号` : e.player_name || '';
    let type: LogEntry['type'] = 'system';
    let text = '';

    if (e.event_type === 'death') {
      type = 'death';
      text = e.public_content || '';
    } else if (e.event_type === 'action') {
      type = 'action';
      text = seatStr ? `${seatStr} ${e.public_content || ''}` : (e.public_content || '');
    } else if (e.event_type === 'speech') {
      type = 'speech';
      text = seatStr ? `${seatStr}: "${e.public_content || ''}"` : `"${e.public_content || ''}"`;
    } else {
      type = 'system';
      text = e.public_content || e.event_type;
    }

    return { id: i, type, text, timestamp: Date.now() };
  });
}

function derivePlayers(players: ReplayPlayer[], events: ReplayEventItem[], step: number): ReplayPlayer[] {
  return players.map(p => {
    let alive = p.is_alive;
    for (let i = 0; i <= step; i++) {
      const e = events[i];
      const content = e.public_content || '';
      if ((e.event_type === 'death' || e.event_type === 'elimination') && content.includes(`${p.seat_number}号`)) {
        alive = false;
      }
      if (e.event_type === 'game_over' && e.player_id === p.id) {
        alive = false;
      }
    }
    return { ...p, is_alive: alive };
  });
}

export default function ReplayPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const numGameId = gameId ? parseInt(gameId) : null;

  const [data, setData] = useState<ReplayData | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [viewer, setViewer] = useState<'normal' | 'god'>('god');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!numGameId) return;
    api.getReplay(numGameId).then(setData).catch(() => {});
  }, [numGameId]);

  useEffect(() => {
    if (!playing || !data || currentStep >= data.events.length - 1) {
      setPlaying(false);
      return;
    }
    const delay = 2000 / speed;
    timerRef.current = setTimeout(() => {
      setCurrentStep(s => Math.min(s + 1, data.events.length - 1));
    }, delay);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [playing, currentStep, data, speed]);

  if (!data) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 18 }}>加载回放数据...</p>
      </div>
    );
  }

  const events = data.events as ReplayEventItem[];
  const totalSteps = events.length;
  const isLast = totalSteps > 0 && currentStep >= totalSteps - 1;

  const visibleEvents = useMemo(() => events.slice(0, currentStep + 1), [events, currentStep]);

  const playersWithStatus = useMemo(
    () => derivePlayers(data.players, events, currentStep),
    [data.players, events, currentStep]
  );

  const seatMap = useMemo(() => {
    const m = new Map<number, number>();
    data.players.forEach(p => m.set(p.id, p.seat_number));
    return m;
  }, [data.players]);

  const logs = useMemo(() => buildLogs(visibleEvents, seatMap), [visibleEvents, seatMap]);

  const lastEvent = visibleEvents[visibleEvents.length - 1];
  const currentPhase = lastEvent?.phase || '';
  const currentRound = lastEvent?.round_number || 0;
  const roundLabel = `第${currentRound}轮 · ${currentPhase}`;

  const winner = useMemo(() => {
    for (const e of visibleEvents) {
      if (e.event_type === 'game_over' && e.public_content?.includes('狼人')) return 'werewolf';
      if (e.event_type === 'game_over' && (e.public_content?.includes('好人') || e.public_content?.includes('村民'))) return 'villager';
    }
    if (playersWithStatus.every(p => !p.is_alive)) return 'villager';
    return playersWithStatus.find(p => p.role === 'werewolf' && p.is_alive) ? 'werewolf' : null;
  }, [visibleEvents, playersWithStatus]);

  const chatMessages = useMemo(() => {
    const msgs: ChatEntry[] = [];
    visibleEvents.forEach((e, i) => {
      if (e.event_type === 'speech' && e.public_content) {
        const seat = e.player_id ? seatMap.get(e.player_id) : undefined;
        const speaker = seat ? `${seat}号 ${e.player_name || ''}` : (e.player_name || '');
        msgs.push({ id: i, speaker, text: e.public_content, type: 'speech' });
      }
      if (viewer === 'god' && e.internal_thought) {
        const seat = e.player_id ? seatMap.get(e.player_id) : undefined;
        const speaker = seat ? `${seat}号 ${e.player_name || ''}` : (e.player_name || '');
        msgs.push({ id: i + 10000, speaker, text: e.internal_thought, type: 'thought' });
      }
    });
    return msgs;
  }, [visibleEvents, seatMap, viewer]);

  const handlePlayPause = () => {
    if (isLast) {
      setCurrentStep(0);
      setPlaying(true);
    } else {
      setPlaying(!playing);
    }
  };

  const handleSeek = (step: number) => {
    setCurrentStep(step);
    setPlaying(false);
  };

  return (
    <div className="game-layout" style={{ minHeight: '100vh' }}>
      <header className="replay-header">
        <div className="replay-header-left">
          <h1 className="replay-header-title">🐺 复盘回放</h1>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {roundLabel}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={() => setViewer(v => v === 'god' ? 'normal' : 'god')}
            style={{
              padding: '6px 14px', fontSize: 12,
              background: viewer === 'god' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255,255,255,0.08)',
              color: viewer === 'god' ? 'var(--accent-purple)' : 'var(--text-muted)',
              border: `1px solid ${viewer === 'god' ? 'var(--accent-purple)' : 'var(--border)'}`,
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {viewer === 'god' ? '👁 上帝视角' : '普通视角'}
          </button>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '6px 14px', fontSize: 12, fontWeight: 600,
              background: 'rgba(255,255,255,0.08)', color: 'var(--text-muted)',
              border: '1px solid var(--border)', borderRadius: 8, cursor: 'pointer',
            }}
          >
            返回
          </button>
        </div>
      </header>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <div style={{ width: '18%', minWidth: 200, borderRight: '1px solid var(--border)', overflow: 'auto' }}>
            <BattleLog events={logs} />
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
              <div style={{ maxWidth: 500, width: '100%' }}>
                <RoundTable
                  players={playersWithStatus.map(p => ({
                    id: p.id,
                    player_name: p.name,
                    seat_number: p.seat_number,
                    role: p.role,
                    is_alive: p.is_alive,
                  }))}
                  currentSpeakerId={null}
                  isGodView={viewer === 'god'}
                  phase={currentPhase}
                  winner={winner}
                />
              </div>
            </div>
          </div>

          <div style={{ width: '25%', minWidth: 220, borderLeft: '1px solid var(--border)', overflow: 'auto' }}>
            <div className="chat-header">
              <span>-- CHAT --</span>
            </div>
            <div className="chat-messages">
              {chatMessages.map(msg => (
                <div key={msg.id} className="chat-bubble">
                  <div className="chat-bubble-header">
                    <span className="chat-bubble-speaker">{msg.speaker}</span>
                    {msg.type === 'thought' && (
                      <span style={{ fontSize: 10, color: 'var(--text-muted)', opacity: 0.6 }}>(内心独白)</span>
                    )}
                  </div>
                  <div className={`chat-bubble-body ${msg.type}`}>
                    {msg.type === 'thought' ? <span className="chat-bubble-thought-prefix">💭内心OS: </span> : null}
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <ReplayControls
          currentStep={currentStep}
          totalSteps={totalSteps}
          playing={playing}
          speed={speed}
          roundLabel={roundLabel}
          onPlayPause={handlePlayPause}
          onPrev={() => setCurrentStep(s => Math.max(0, s - 1))}
          onNext={() => setCurrentStep(s => Math.min(totalSteps - 1, s + 1))}
          onFirst={() => setCurrentStep(0)}
          onLast={() => setCurrentStep(totalSteps - 1)}
          onSpeedChange={setSpeed}
          onSeek={handleSeek}
        />
      </main>
    </div>
  );
}
