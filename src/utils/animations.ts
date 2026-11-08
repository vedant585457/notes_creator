import {Easing, interpolate} from 'remotion';

/** Frame-driven helpers. Every value is a pure function of `frame`, so renders are deterministic. */

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

/** 0→1 over `dur` frames starting at `start` frame, eased. Clamped. */
export const ramp = (frame: number, start: number, dur: number, ease = EASE_OUT): number =>
  interpolate(frame, [start, start + dur], [0, 1], {
    easing: ease,
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

/** Fade in at `start`, fade out so it ends at `end` (both in local frames). */
export const fadeWindow = (frame: number, start: number, end: number, inDur = 10, outDur = 10): number =>
  interpolate(frame, [start, start + inDur, end - outDur, end], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

/** Mask-reveal percentage for a line of text (0 → 100). */
export const reveal = (frame: number, start: number, dur = 16): number => ramp(frame, start, dur, EASE_OUT) * 100;

/** Deterministic pseudo-random in [0,1) from an integer seed. */
export const hash = (n: number): number => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
