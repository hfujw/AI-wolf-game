import { useEffect, useState, useCallback, useRef } from 'react';
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

function parseVoteEvent(e: GameEvent): { voterId: number; targetSeat: number } | null {
  if (e.event_type !== 'vote' || e.phase !== 'day_vote') return null;
  const match = e.content.match(/(\d+)号/);
  if (!match) return null;
  const targetSeat = parseInt(match[1], 10);
  return { voterId: e.player_id, targetSeat };
}

export default function RoundTable({
  players, currentSpeakerId, isGodView, phase, events, winner, thinkingPlayerIds, onPlayerClick,
}: RoundTableProps) {
  const sorted = [...players].sort((a, b) => a.seat_number - b.seat_number);
  const [voteCounts, setVoteCounts] = useState<Record<number, number>>({});

  const pendingVoteQueueRef = useRef<VoteItem[]>([]);
  const voteSortedRef = useRef<VoteItem[]>([]);
  const voteProcessingIdx = useRef(0);
  const voteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const votePhaseRoundRef = useRef<string>('');
  const processedEventIds = useRef<Set<number>>(new Set());
  const eventIdxRef = useRef(0);

  const processEvents = useCallback(() => {
    if (!events || events.length === 0) return;
    const newEventIdx = eventIdxRef.current;
    let hasNewVote = false;

    for (let i = newEventIdx; i < events.length; i++) {
      const e = events[i];
      if (processedEventIds.current.has(i)) continue;
      processedEventIds.current.add(i);

      const vote = parseVoteEvent(e);
      if (vote) {
        const voter = players.find(p => p.id === vote.voterId);
        if (voter) {
          pendingVoteQueueRef.current.push({ voterSeat: voter.seat_number, targetSeat: vote.targetSeat });
          hasNewVote = true;
        }
      }
    }
    eventIdxRef.current = events.length;

    if (hasNewVote && phase === 'day_vote') startVoteSequence();
  }, [events, players, phase]);

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
    voteProcessingIdx.current++;
    voteTimerRef.current = setTimeout(processNextVote, 1000);
  }

  useEffect(() => { processEvents(); }, [processEvents]);

  useEffect(() => () => {
    if (voteTimerRef.current) clearTimeout(voteTimerRef.current);
  }, []);

  useEffect(() => {
    if (phase !== 'day_vote') {
      setVoteCounts({});
      voteSortedRef.current = [];
      voteProcessingIdx.current = 0;
      pendingVoteQueueRef.current = [];
      votePhaseRoundRef.current = '';
      if (voteTimerRef.current) { clearTimeout(voteTimerRef.current); voteTimerRef.current = null; }
    }
  }, [phase]);

  const isSpeechPhase = phase === 'day_speech';
  const isVotePhase = phase === 'day_vote';
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

      {sorted.map((p, i) => {
        const angle = 270 - (i * 360) / sorted.length;
        const isSpeaker = isSpeechPhase && currentSpeakerId === p.id;

        let voteLabel: string | null = null;
        if (isVotePhase && p.is_alive) {
          const count = voteCounts[p.seat_number] || 0;
          voteLabel = count > 0 ? `${count}票` : '投票';
        }

        return (
          <Seat
            key={p.id}
            seatNumber={p.seat_number}
            playerName={p.player_name}
            isAlive={p.is_alive}
            isCurrentSpeaker={currentSpeakerId === p.id}
            angle={angle}
            radius={TABLE_RADIUS}
            role={p.role}
            phase={phase}
            isSpeaker={isSpeaker}
            isThinking={thinkingPlayerIds?.has(p.id)}
            voteLabel={voteLabel}
            winnerClass={getWinnerClass(p)}
            showRole={isGodView}
            onClick={() => onPlayerClick?.(p.id)}
          />
        );
      })}
    </div>
  );
}
