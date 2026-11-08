import {DUCK, FPS, TOTAL_FRAMES, VO, MUSIC, sec} from './timing';

/**
 * Precomputed per-frame music gain. Narration windows (padded) drop the bed to `speechGain`;
 * otherwise it sits at `openGain`. A one-pole smoother gives the envelope its attack/release.
 * Pure data, computed once at module load, so the render is deterministic.
 */
const build = (): Float32Array => {
  const target = new Float32Array(TOTAL_FRAMES);
  for (let f = 0; f < TOTAL_FRAMES; f++) {
    const t = f / FPS;
    const inSpeech = VO.some(
      (v) => t >= v.at - DUCK.padBefore && t <= v.at + v.dur + DUCK.padAfter,
    );
    target[f] = inSpeech ? DUCK.speechGain : DUCK.openGain;
  }
  const out = new Float32Array(TOTAL_FRAMES);
  const k = 1 - Math.exp(-1 / (DUCK.smoothSec * FPS));
  let acc = DUCK.openGain;
  for (let f = 0; f < TOTAL_FRAMES; f++) {
    acc += k * (target[f] - acc);
    const t = f / FPS;
    let fade = 1;
    if (t >= MUSIC.fadeOutStart) {
      fade = Math.max(0, 1 - (t - MUSIC.fadeOutStart) / (MUSIC.fadeOutEnd - MUSIC.fadeOutStart));
    }
    out[f] = acc * fade;
  }
  return out;
};

export const DUCK_ENVELOPE = build();
export const duckAt = (frame: number): number =>
  DUCK_ENVELOPE[Math.min(TOTAL_FRAMES - 1, Math.max(0, Math.round(frame)))];
export const frameOf = sec;
