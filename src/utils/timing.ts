/**
 * Single source of truth for every time-based decision in the film.
 * Components read from here; they never hard-code seconds or frames.
 * Seconds are authored (easier to reason about against the narration);
 * `sec()` converts them to integer frames at the composition frame rate.
 */
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const TOTAL_SECONDS = 160;

export const sec = (s: number): number => Math.round(s * FPS);
export const TOTAL_FRAMES = sec(TOTAL_SECONDS);

/** Footage shots: timeline window (seconds) and the source in-point (seconds into the screencast). */
export type Shot = {id: string; start: number; end: number; src: number; dim?: number};
export const SHOTS: Shot[] = [
  {id: 'cold-open', start: 0, end: 6, src: 0},
  {id: 'brief', start: 6, end: 26, src: 6},
  {id: 'copilot', start: 26, end: 45, src: 20},
  {id: 'recon', start: 45, end: 64, src: 40},
  {id: 'obstacle', start: 64, end: 75, src: 180},
  {id: 'instance', start: 75, end: 86, src: 255},
  {id: 'insight', start: 86, end: 105, src: 190, dim: 0.18},
  {id: 'payload', start: 105, end: 122, src: 300},
  {id: 'flag', start: 122, end: 137, src: 315},
  {id: 'result', start: 137, end: 148, src: 326},
  {id: 'end-card', start: 148, end: 160, src: 325, dim: 0.12},
];

/** Narration clips. `at` = start on timeline (s); `dur` = measured length of the WAV (s). */
export const VO = [
  {n: '01', at: 1.0, dur: 4.09},
  {n: '02', at: 6.0, dur: 19.78},
  {n: '03', at: 28.0, dur: 16.51},
  {n: '04', at: 46.0, dur: 16.21},
  {n: '05', at: 64.5, dur: 7.8},
  {n: '06', at: 74.5, dur: 10.4},
  {n: '07', at: 87.0, dur: 17.01},
  {n: '08', at: 106.0, dur: 15.06},
  {n: '09', at: 123.0, dur: 12.84},
  {n: '10', at: 137.0, dur: 10.88},
] as const;

/** Chapter / act cards. Each one is a timing point; the card's own duration lives in ACT_CARD_SECONDS. */
export const ACT_CARD_SECONDS = 2.6;
export const ACTS = [
  {n: '01', title: 'THE BRIEF', at: 6.0},
  {n: '02', title: 'THE COPILOT', at: 26.0},
  {n: '03', title: 'RECON', at: 45.0},
  {n: '04', title: 'THE OBSTACLE', at: 64.0},
  {n: '05', title: 'THE INSTANCE', at: 75.0},
  {n: '06', title: 'THE INSIGHT', at: 86.0},
  {n: '07', title: 'THE PAYLOAD', at: 105.0},
  {n: '08', title: 'THE RESULT', at: 137.0},
] as const;

/** Lower thirds. */
export const LOWER_THIRDS = [
  {at: 8.5, label: 'PLATFORM', value: 'cyLab Academy', dur: 5.0},
  {at: 13.5, label: 'CHALLENGE', value: 'Flag Hunters · Reverse Engineering · Easy', dur: 6.0},
] as const;

/** Kinetic type stings (short, sparing). */
export const STINGS = [
  {at: 16.0, text: 'HIDDEN REFRAIN', color: 'amber'},
  {at: 66.5, text: 'flag.txt NOT FOUND', color: 'red'},
  {at: 109.0, text: "RETURN 0", color: 'amber'},
  {at: 126.0, text: 'FLAG IN THE LYRICS', color: 'amber'},
] as const;

/** Schematic (line-index diagram) window. */
export const SCHEMATIC = {start: 86.0, end: 105.0};

/** Command cards typed on screen. `at` = start, `chars`= characters per second typing speed. */
export const COMMANDS = [
  {at: 109.0, end: 121.0, text: "(echo ' x;RETURN 0'; sleep 60) | nc xebec.cylabacademy.net 20544", cps: 26},
] as const;

/** Callout (flag) window and bracket region in source-frame pixels (1920x1080). */
export const FLAG_CALLOUT = {start: 129.5, end: 134.0, box: {x: 200, y: 975, w: 330, h: 60}};

/** Sound effects cue sheet: [seconds, file, gain]. */
export const SFX: ReadonlyArray<readonly [number, string, number]> = [
  [0.4, 'impact', 0.7],
  [5.6, 'whoosh', 0.35],
  [6.0, 'tick', 0.5],
  [25.6, 'whoosh', 0.35],
  [44.6, 'whoosh', 0.35],
  [63.6, 'whoosh', 0.35],
  [66.5, 'thud', 0.6],
  [74.6, 'whoosh', 0.35],
  [85.8, 'whoosh', 0.35],
  [102.0, 'riser', 0.5],
  [105.0, 'impact', 0.6],
  [108.5, 'key', 0.35],
  [109.4, 'key', 0.35],
  [110.4, 'key', 0.35],
  [112.0, 'key', 0.35],
  [126.0, 'blip', 0.4],
  [128.0, 'impact', 0.6],
  [136.6, 'whoosh', 0.35],
  [141.0, 'chime', 0.45],
  [147.6, 'whoosh', 0.35],
] as const;

/** Music bed: start, and the fade-out window that closes the film. */
export const MUSIC = {start: 0.0, fadeOutStart: 150.0, fadeOutEnd: 160.0, gain: 0.55};

/** Ducking: music gain when narration is present vs. when it is absent, with smoothing. */
export const DUCK = {speechGain: 0.22, openGain: 0.55, padBefore: 0.2, padAfter: 0.35, smoothSec: 0.18};

/** Transition timing (mask wipes, cross-fades). */
export const TRANSITIONS = {wipeFrames: 12, fadeFromBlackFrames: 15};
