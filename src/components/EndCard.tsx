import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, TYPE} from '../styles/theme';
import {ramp, fadeWindow} from '../utils/animations';
import {sec} from '../utils/timing';

const CHIPS = ['1  SOURCE', '2  CROWD INPUT', '3  RETURN 0', '4  LINE 0'];

/** End card: recap chips appear in sequence, lockup, credit line. Fades the footage out, not the audio. */
export const EndCard: React.FC<{dur: number}> = ({dur}) => {
  const frame = useCurrentFrame();
  const op = fadeWindow(frame, 0, sec(dur), 10, 4);
  const lock = ramp(frame, 4, 22);
  return (
    <AbsoluteFill style={{background: 'rgba(7,8,11,0.82)', alignItems: 'center', justifyContent: 'center', opacity: op, pointerEvents: 'none'}}>
      <div style={{fontFamily: FONT.mono, letterSpacing: '0.24em', fontSize: TYPE.label + 2, color: COLOR.amber, opacity: lock}}>
        CASE 001 · SOLVED
      </div>
      <div
        style={{
          fontFamily: FONT.display,
          fontWeight: 700,
          fontSize: 132,
          letterSpacing: '-0.03em',
          color: COLOR.paper,
          marginTop: 14,
          clipPath: `inset(0 ${100 - lock * 100}% 0 0)`,
        }}
      >
        FLAG HUNTERS
      </div>
      <div style={{display: 'flex', gap: 18, marginTop: 34}}>
        {CHIPS.map((c, i) => (
          <div
            key={c}
            style={{
              fontFamily: FONT.mono,
              fontSize: 18,
              letterSpacing: '0.12em',
              color: COLOR.paper,
              border: `1px solid ${COLOR.hairline}`,
              padding: '10px 18px',
              opacity: ramp(frame, 26 + i * 6, 12),
            }}
          >
            {c}
          </div>
        ))}
      </div>
      <div style={{fontFamily: FONT.body, fontSize: 20, color: COLOR.muted, marginTop: 44, opacity: ramp(frame, 60, 16)}}>
        Footage: live session recording · Narration: synthetic voice · Music and effects: original
      </div>
    </AbsoluteFill>
  );
};
