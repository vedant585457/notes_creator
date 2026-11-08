import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, TYPE} from '../styles/theme';
import {ramp, fadeWindow} from '../utils/animations';
import {FLAG_CALLOUT, sec} from '../utils/timing';

/** Bracket corners snap around the flag line in the footage, plus a mono label. */
export const FlagCallout: React.FC = () => {
  const frame = useCurrentFrame();
  const end = sec(FLAG_CALLOUT.end - FLAG_CALLOUT.start);
  const op = fadeWindow(frame, 0, end, 8, 12);
  const s = ramp(frame, 4, 14);
  const {x, y, w, h} = FLAG_CALLOUT.box;
  const k = 40 + (1 - s) * 30;
  const corner = (cx: number, cy: number, dx: number, dy: number) => (
    <path d={`M ${cx} ${cy + dy * k} L ${cx} ${cy} L ${cx + dx * k} ${cy}`} stroke={COLOR.amber} strokeWidth={3} fill="none" />
  );
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none'}}>
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        {corner(x, y, 1, 1)}
        {corner(x + w, y, -1, 1)}
        {corner(x, y + h, 1, -1)}
        {corner(x + w, y + h, -1, -1)}
      </svg>
      <div
        style={{
          position: 'absolute',
          left: x + w + 24,
          top: y + h / 2 - 18,
          fontFamily: FONT.mono,
          fontSize: TYPE.label + 2,
          letterSpacing: '0.18em',
          color: COLOR.amber,
          opacity: ramp(frame, 10, 12),
          whiteSpace: 'nowrap',
        }}
      >
        FLAG IN THE LYRICS
      </div>
    </AbsoluteFill>
  );
};
