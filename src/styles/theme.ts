/** Visual identity: "Terminal noir". See plan.md §3. */
export const COLOR = {
  ink: '#07080B',
  panel: '#101319',
  hairline: '#242A36',
  amber: '#FF7A2F',
  amberLight: '#FFB27A',
  cyan: '#59E3C8',
  red: '#FF4D5E',
  paper: '#F3F1EC',
  muted: '#9AA3B2',
} as const;

export const FONT = {
  display: '"Space Grotesk", "Inter", sans-serif',
  body: '"Inter", "Helvetica Neue", Arial, sans-serif',
  mono: '"JetBrains Mono", "Menlo", monospace',
} as const;

export const SPACE = {marginX: 96, marginY: 88, sideX: 72, baseline: 8} as const;

export const TYPE = {
  actTitle: 104,
  sting: 84,
  statement: 72,
  lowerValue: 34,
  label: 13,
  code: 28,
  caption: 22,
} as const;
