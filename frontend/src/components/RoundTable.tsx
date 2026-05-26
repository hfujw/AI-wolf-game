import { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Seat from './Seat';

interface Player {
  id: number;
  player_name: string;
  seat_number: number;
  role?: string;
  personality?: string;
  is_alive: boolean;
}

interface GameEvent {
  event_type: string;
  player_id: number;
  role?: string;
  content: string;
  phase: string;
  round_number: number;
}

export interface IdentityReveal {
  type: 'good' | 'wolf' | 'save' | 'poison';
  label: string;
}

interface KnifeAnim {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  key: number;
  color: string;
}

interface HunterGlow {
  playerId: number;
  timestamp: number;
}

export interface EliminatingPlayer {
  playerId: number;
  seatNumber: number;
  timestamp: number;
}

interface VoteItem {
  voterSeat: number;
  targetSeat: number;
}

interface RoundTableProps {
  players: Player[];
  currentSpeakerId: number | null;
  isGodView: boolean;
  phase?: string;
  events?: GameEvent[];
  winner?: string | null;
  thinkingPlayerIds?: Set<number>;
  onPlayerClick?: (playerId: number) => void;
}

const TABLE_CX = 250;
const TABLE_CY = 250;
const TABLE_RADIUS = 180;

function getSeatCoords(seatNumber: number, totalSeats: number) {
  const sortedSeats = Array.from({ length: totalSeats }, (_, i) => i + 1);
  const index = sortedSeats.indexOf(seatNumber);
  if (index < 0) return { x: TABLE_CX, y: TABLE_CY };
  const angle = 270 - (index * 360) / totalSeats;
  const rad = (angle * Math.PI) / 180;
  return {
    x: TABLE_CX + TABLE_RADIUS * Math.cos(rad),
    y: TABLE_CY + TABLE_RADIUS * Math.sin(rad),
  };
}

function parseWolfAction(event: GameEvent, players: Player[]): { fromId: number; toSeat: number } | null {
  if (event.event_type !== 'action' || event.phase !== 'night_werewolf') return null;
  const player = players.find(p => p.id === event.player_id);
  if (!player) return null;
  const match = event.content.match(/(\d+)号/);
  if (!match) return null;
  const toSeat = parseInt(match[1], 10);
  return { fromId: event.player_id, toSeat };
}

function parseSeerReveal(event: GameEvent): IdentityReveal | null {
  if (event.event_type !== 'action' || event.phase !== 'night_seer') return null;
  if (event.content.includes('狼人') || event.content.includes('werewolf')) {
    return { type: 'wolf', label: '狼人' };
  }
  if (event.content.includes('好人') || event.content.includes('good')) {
    return { type: 'good', label: '好人' };
  }
  return null;
}

function parseWitchAction(event: GameEvent): { toSeat: number; reveal: IdentityReveal } | null {
  if (event.event_type !== 'action' || event.phase !== 'night_witch') return null;
  if (event.content.includes('救') || event.content.includes('save') || event.content.includes('解药')) {
    const match = event.content.match(/(\d+)号/);
    return match ? { toSeat: parseInt(match[1], 10), reveal: { type: 'save', label: '解药' } } : null;
  }
  if (event.content.includes('毒') || event.content.includes('poison') || event.content.includes('毒药')) {
    const match = event.content.match(/(\d+)号/);
    return match ? { toSeat: parseInt(match[1], 10), reveal: { type: 'poison', label: '毒药' } } : null;
  }
  return null;
}

function isDeathEvent(e: GameEvent): boolean {
  return e.event_type === 'death' && e.phase === 'day_announce';
}

function parseVoteEvent(e: GameEvent): { voterId: number; targetSeat: number } | null {
  if (e.event_type !== 'vote' || e.phase !== 'day_vote') return null;
  const match = e.content.match(/(\d+)号/);
  if (!match) return null;
  const targetSeat = parseInt(match[1], 10);
  return { voterId: e.player_id, targetSeat };
}

function parseHunterShoot(e: GameEvent): { fromSeat: number; toSeat: number } | null {
  if (e.event_type !== 'hunter_shoot') return null;
  if (!e.content) return null;
  const matches = e.content.match(/(\d+)号/g);
  if (!matches || matches.length < 2) return null;
  const fromSeat = parseInt(matches[0], 10);
  const toSeat = parseInt(matches[1], 10);
  return { fromSeat, toSeat };
}

export default function RoundTable({
  players,
  currentSpeakerId,
  isGodView,
  phase,
  events,
  winner,
  thinkingPlayerIds,
  onPlayerClick,
}: RoundTableProps) {
  const sorted = [...players].sort((a, b) => a.seat_number - b.seat_number);
  const [knifeAnims, setKnifeAnims] = useState<KnifeAnim[]>([]);
  const [identityMap, setIdentityMap] = useState<Record<number, IdentityReveal>>({});
  const [targetGlowMap, setTargetGlowMap] = useState<Record<number, string>>({});
  const [voteCounts, setVoteCounts] = useState<Record<number, number>>({});
  const [shakingPlayerId, setShakingPlayerId] = useState<number | null>(null);
  const [eliminatingPlayers, setEliminatingPlayers] = useState<EliminatingPlayer[]>([]);
  const knifeKeyRef = useRef(0);
  const processedEventIds = useRef<Set<number>>(new Set());
  const eventIdxRef = useRef(0);
  const elimTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pendingVoteQueueRef = useRef<VoteItem[]>([]);
  const voteSortedRef = useRef<VoteItem[]>([]);
  const voteProcessingIdx = useRef(0);
  const voteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const votePhaseRoundRef = useRef<string>('');

  const processEvents = useCallback(() => {
    if (!events || events.length === 0) return;

    const newEventIdx = eventIdxRef.current;
    let hasNewVote = false;
    for (let i = newEventIdx; i < events.length; i++) {
      const e = events[i];
      if (processedEventIds.current.has(i)) continue;
      processedEventIds.current.add(i);

      const wolfAction = parseWolfAction(e, players);
      if (wolfAction) {
        const wolf = players.find(p => p.id === wolfAction.fromId);
        const target = players.find(p => p.seat_number === wolfAction.toSeat);
        if (wolf && target) {
          const from = getSeatCoords(wolf.seat_number, sorted.length);
          const to = getSeatCoords(target.seat_number, sorted.length);
          knifeKeyRef.current++;
          setKnifeAnims(prev => [...prev, {
            fromX: from.x, fromY: from.y, toX: to.x, toY: to.y,
            key: knifeKeyRef.current, color: 'var(--accent-red)',
          }]);
        }
      }

      const hunterShoot = parseHunterShoot(e);
      if (hunterShoot) {
        const hunter = players.find(p => p.seat_number === hunterShoot.fromSeat);
        const target = players.find(p => p.seat_number === hunterShoot.toSeat);
        if (hunter && target) {
          const from = getSeatCoords(hunter.seat_number, sorted.length);
          const to = getSeatCoords(target.seat_number, sorted.length);
          knifeKeyRef.current++;
          setKnifeAnims(prev => [...prev, {
            fromX: from.x, fromY: from.y, toX: to.x, toY: to.y,
            key: knifeKeyRef.current, color: '#f59e0b',
          }]);
        }
      }

      const seerReveal = parseSeerReveal(e);
      if (seerReveal && e.player_id) {
        const match = e.content.match(/(\d+)号/);
        if (match) {
          const targetSeat = parseInt(match[1], 10);
          const targetPlayer = players.find(p => p.seat_number === targetSeat);
          if (targetPlayer) {
            setIdentityMap(prev => ({ ...prev, [targetPlayer.id]: seerReveal }));
            setTargetGlowMap(prev => ({ ...prev, [targetPlayer.id]: 'seer-check' }));
            setTimeout(() => {
              setIdentityMap(prev => { const next = { ...prev }; delete next[targetPlayer.id]; return next; });
              setTargetGlowMap(prev => { const next = { ...prev }; delete next[targetPlayer.id]; return next; });
            }, 3000);
          }
        }
      }

      const witchAction = parseWitchAction(e);
      if (witchAction && e.player_id) {
        const target = players.find(p => p.seat_number === witchAction.toSeat);
        if (target) {
          setIdentityMap(prev => ({ ...prev, [target.id]: witchAction.reveal }));
          const glowType = witchAction.reveal.type === 'save' ? 'witch-save' : 'witch-poison';
          setTargetGlowMap(prev => ({ ...prev, [target.id]: glowType }));
          setTimeout(() => {
            setIdentityMap(prev => { const next = { ...prev }; delete next[target.id]; return next; });
            setTargetGlowMap(prev => { const next = { ...prev }; delete next[target.id]; return next; });
          }, 3000);
        }
      }

      const vote = parseVoteEvent(e);
      if (vote) {
        const voter = players.find(p => p.id === vote.voterId);
        if (voter) {
          pendingVoteQueueRef.current.push({ voterSeat: voter.seat_number, targetSeat: vote.targetSeat });
          hasNewVote = true;
        }
      }

      if (isDeathEvent(e)) {
        const match = e.content.match(/(\d+)号/);
        if (match) {
          const deadSeat = parseInt(match[1], 10);
          const deadPlayer = players.find(p => p.seat_number === deadSeat);
          if (deadPlayer) {
            setEliminatingPlayers(prev => [...prev, { playerId: deadPlayer.id, seatNumber: deadSeat, timestamp: Date.now() }]);
            if (elimTimerRef.current) clearTimeout(elimTimerRef.current);
            elimTimerRef.current = setTimeout(() => {
              setEliminatingPlayers(prev => prev.filter(ep => ep.playerId !== deadPlayer.id));
            }, 2500);
          }
        }
      }
    }
    eventIdxRef.current = events.length;

    if (hasNewVote && phase === 'day_vote') {
      startVoteSequence();
    }
  }, [events, players, sorted.length, phase]);

  function startVoteSequence() {
    if (voteTimerRef.current) return;

    const phaseRoundKey = `${phase}_${events?.length || 0}`;
    if (phaseRoundKey === votePhaseRoundRef.current) return;
    votePhaseRoundRef.current = phaseRoundKey;

    if (pendingVoteQueueRef.current.length === 0) return;

    voteSortedRef.current = [...pendingVoteQueueRef.current].sort((a, b) => a.voterSeat - b.voterSeat);
    pendingVoteQueueRef.current = [];
    voteProcessingIdx.current = 0;

    processNextVote();
  }

  function processNextVote() {
    const idx = voteProcessingIdx.current;
    if (idx >= voteSortedRef.current.length) {
      voteTimerRef.current = null;
      voteSortedRef.current = [];
      return;
    }

    const v = voteSortedRef.current[idx];
    setVoteCounts(prev => {
      const next = { ...prev };
      next[v.targetSeat] = (next[v.targetSeat] || 0) + 1;
      return next;
    });
    const targetPlayer = players.find(p => p.seat_number === v.targetSeat);
    if (targetPlayer) {
      setShakingPlayerId(targetPlayer.id);
      setTimeout(() => setShakingPlayerId(null), 600);
    }

    voteProcessingIdx.current++;
    voteTimerRef.current = setTimeout(processNextVote, 1500);
  }

  useEffect(() => { processEvents(); }, [processEvents]);

  useEffect(() => {
    if (knifeAnims.length === 0) return;
    const timer = setTimeout(() => setKnifeAnims(prev => prev.slice(1)), 1000);
    return () => clearTimeout(timer);
  }, [knifeAnims]);

  useEffect(() => () => {
    if (elimTimerRef.current) clearTimeout(elimTimerRef.current);
    if (voteTimerRef.current) clearTimeout(voteTimerRef.current);
  }, []);

  useEffect(() => {
    if (phase !== 'day_vote') {
      setVoteCounts({});
      voteSortedRef.current = [];
      voteProcessingIdx.current = 0;
      pendingVoteQueueRef.current = [];
      votePhaseRoundRef.current = '';
      if (voteTimerRef.current) {
        clearTimeout(voteTimerRef.current);
        voteTimerRef.current = null;
      }
    }
  }, [phase]);

  const isSpeechPhase = phase === 'day_speech';
  const isVotePhase = phase === 'day_vote';
  const eliminatingPlayerIds = new Set(eliminatingPlayers.map(ep => ep.playerId));
  const isFinished = phase === 'finished' || phase === 'game_over' || !!winner;

  function getWinnerClass(p: Player): string {
    if (!isFinished || !winner) return '';
    const pp = (p.role || '').toLowerCase();
    if (winner === 'werewolves') return pp === 'werewolf' ? 'winner-glow winner-wolf' : 'loser-dim';
    return pp !== 'werewolf' ? 'winner-glow winner-good' : 'loser-dim';
  }

  return (
    <div className="round-table" style={{ width: TABLE_CX * 2, height: TABLE_CY * 2 }}>
      <div className="table-bg" />

      <AnimatePresence>
        {knifeAnims.map((anim) => (
          <motion.svg
            key={anim.key}
            className="knife-svg-overlay"
            viewBox={`0 0 ${TABLE_CX * 2} ${TABLE_CY * 2}`}
          >
            <motion.line
              className="knife-glow"
              x1={anim.fromX} y1={anim.fromY}
              x2={anim.toX} y2={anim.toY}
              stroke={anim.color}
              strokeWidth={3}
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 1 }}
              animate={{ pathLength: 1, opacity: [1, 1, 0] }}
              transition={{ duration: 0.8, ease: 'easeInOut', opacity: { times: [0, 0.8, 1], duration: 0.8 } }}
            />
            <motion.circle
              cx={anim.toX} cy={anim.toY} r={0}
              fill={anim.color}
              animate={{ r: [0, 8, 0], opacity: [1, 0.8, 0] }}
              transition={{ duration: 0.6, delay: 0.7, ease: 'easeInOut' }}
            />
          </motion.svg>
        ))}
      </AnimatePresence>

      <AnimatePresence>
        {eliminatingPlayers.map((ep) => (
          <motion.div key={ep.playerId} className="elimination-particles">
            {Array.from({ length: 20 }).map((_, pi) => {
              const player = players.find(p => p.id === ep.playerId);
              const coords = player ? getSeatCoords(player.seat_number, sorted.length) : { x: TABLE_CX, y: TABLE_CY };
              const angle = (pi / 20) * 360;
              const rad2 = (angle * Math.PI) / 180;
              const dist = 30 + Math.random() * 50;
              return (
                <motion.div
                  key={pi}
                  className="elimination-particle"
                  style={{
                    left: coords.x, top: coords.y,
                    width: 4 + Math.random() * 6, height: 4 + Math.random() * 6,
                    background: pi % 2 === 0 ? 'var(--accent-red)' : 'var(--accent-gold)',
                  }}
                  initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
                  animate={{ x: Math.cos(rad2) * dist, y: Math.sin(rad2) * dist, opacity: 0, scale: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.8 + Math.random() * 0.4, ease: 'easeOut' }}
                />
              );
            })}
          </motion.div>
        ))}
      </AnimatePresence>

      {sorted.map((p, i) => {
        const angle = 270 - (i * 360) / sorted.length;
        const radius = TABLE_RADIUS;
        const isSpeaker = isSpeechPhase && currentSpeakerId === p.id;
        const isEliminating = eliminatingPlayerIds.has(p.id);

        let voteLabel: string | null = null;
        if (isVotePhase && p.is_alive) {
          const count = voteCounts[p.seat_number] || 0;
          voteLabel = count > 0 ? `${count}票` : '投票';
        }

        const isShaking = shakingPlayerId === p.id;

        return (
          <Seat
            key={p.id}
            seatNumber={p.seat_number}
            playerName={p.player_name}
            isAlive={p.is_alive && !isEliminating}
            isCurrentSpeaker={currentSpeakerId === p.id}
            angle={angle}
            radius={radius}
            role={p.role}
            phase={phase}
            isSpeaker={isSpeaker}
            isThinking={thinkingPlayerIds?.has(p.id)}
            identityReveal={identityMap[p.id] || null}
            voteLabel={voteLabel}
            shaking={isShaking}
            eliminated={isEliminating}
            winnerClass={getWinnerClass(p)}
            showRole={isGodView}
            targetGlow={targetGlowMap[p.id] || null}
            onClick={() => onPlayerClick?.(p.id)}
          />
        );
      })}
    </div>
  );
}
