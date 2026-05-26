interface ReplayControlsProps {
  currentStep: number;
  totalSteps: number;
  playing: boolean;
  speed: number;
  roundLabel: string;
  onPlayPause: () => void;
  onPrev: () => void;
  onNext: () => void;
  onFirst: () => void;
  onLast: () => void;
  onSpeedChange: (speed: number) => void;
  onSeek: (step: number) => void;
}

const SPEEDS = [1, 2, 4, 8];

export default function ReplayControls({
  currentStep,
  totalSteps,
  playing,
  speed,
  roundLabel,
  onPlayPause,
  onPrev,
  onNext,
  onFirst,
  onLast,
  onSpeedChange,
  onSeek,
}: ReplayControlsProps) {
  const isFirst = currentStep <= 0;
  const isLast = totalSteps > 0 && currentStep >= totalSteps - 1;

  return (
    <div className="replay-controls">
      <button className="replay-btn" onClick={onFirst} disabled={isFirst}>
        ⏮
      </button>
      <button className="replay-btn" onClick={onPrev} disabled={isFirst}>
        ◀
      </button>

      <button
        className="replay-btn play"
        onClick={onPlayPause}
      >
        {playing ? '⏸ 暂停' : isLast ? '🔄 重播' : '▶ 播放'}
      </button>

      <button className="replay-btn" onClick={onNext} disabled={isLast}>
        ▶
      </button>
      <button className="replay-btn" onClick={onLast} disabled={isLast}>
        ⏭
      </button>

      <div className="replay-progress-wrap">
        <span className="replay-progress-label">{roundLabel}</span>
        <input
          type="range"
          className="replay-progress"
          min={0}
          max={Math.max(0, totalSteps - 1)}
          value={currentStep}
          onChange={e => onSeek(parseInt(e.target.value, 10))}
        />
        <span className="replay-progress-label">{currentStep + 1}/{totalSteps}</span>
      </div>

      <div className="replay-speed-group">
        {SPEEDS.map(s => (
          <button
            key={s}
            className={`replay-speed-btn ${s === speed ? 'active' : ''}`}
            onClick={() => onSpeedChange(s)}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
}
