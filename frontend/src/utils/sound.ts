let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
  return audioCtx;
}

function playTone(
  freq: number,
  duration: number,
  type: OscillatorType = 'sine',
  volume = 0.15,
  rampDown = true,
) {
  try {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, ctx.currentTime);
    if (rampDown) {
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    }
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + duration);
  } catch {
    // 音频上下文未初始化则忽略
  }
}

function playChord(
  freqs: number[],
  duration: number,
  type: OscillatorType = 'sine',
  volume = 0.1,
) {
  freqs.forEach(f => playTone(f, duration, type, volume));
}

export function playNightSound() {
  // 低沉悬疑氛围：低音长音
  playTone(110, 1.5, 'sawtooth', 0.06);
  setTimeout(() => playTone(130, 1.2, 'triangle', 0.05), 400);
  setTimeout(() => playTone(98, 1.8, 'sawtooth', 0.04), 800);
}

export function playDawnSound() {
  // 天亮：上行音符 + 弦乐感
  playTone(440, 0.3, 'sine', 0.12, false);
  setTimeout(() => playTone(554, 0.3, 'sine', 0.12, false), 150);
  setTimeout(() => playTone(659, 0.5, 'sine', 0.12, false), 300);
  setTimeout(() => playChord([440, 554, 659, 880], 1.5, 'triangle', 0.08), 500);
}

export function playVoteTicking() {
  // 投票倒计时：急促嘀嗒
  let count = 0;
  const max = 6;
  const iv = setInterval(() => {
    playTone(800, 0.08, 'square', 0.06);
    count++;
    if (count >= max) clearInterval(iv);
  }, 400);
}

export function playVictorySound() {
  // 胜利号角：大三和弦上行
  playTone(523, 0.3, 'triangle', 0.12, false);
  setTimeout(() => playTone(659, 0.3, 'triangle', 0.12, false), 200);
  setTimeout(() => playTone(784, 0.4, 'triangle', 0.12, false), 400);
  setTimeout(() => playChord([523, 659, 784, 1047], 2, 'triangle', 0.1), 700);
}

export function playDefeatSound() {
  // 失败惨淡：下行小调
  playTone(440, 0.3, 'sawtooth', 0.08, false);
  setTimeout(() => playTone(415, 0.3, 'sawtooth', 0.08, false), 250);
  setTimeout(() => playTone(370, 0.5, 'sawtooth', 0.08, false), 500);
  setTimeout(() => playTone(330, 1.5, 'sawtooth', 0.06), 800);
}

export function playVoteResultSound() {
  // 投票结果揭示
  playTone(350, 0.15, 'square', 0.08, false);
  setTimeout(() => playTone(300, 0.6, 'sawtooth', 0.07), 200);
}

export function playKnifeSound() {
  // 刀出鞘
  const ctx = getCtx();
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sawtooth';
  osc.frequency.setValueAtTime(1200, now);
  osc.frequency.exponentialRampToValueAtTime(200, now + 0.3);
  gain.gain.setValueAtTime(0.08, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.35);
}

export function initAudio() {
  if (!audioCtx) {
    audioCtx = new AudioContext();
  }
}
