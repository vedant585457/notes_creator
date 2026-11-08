import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLOR, FONT, SPACE, TYPE} from '../styles/theme';
import {ramp, reveal, fadeWindow} from '../utils/animations';
import {ACT_CARD_SECONDS, sec} from '../utils/timing';

/** Act card: kicker, title (mask-revealed), and a 1px amber rule that draws left to right. */
export const ActCard: React.FC<{n: string; title: string}> = ({n, title}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const total = sec(ACT_CARD_SECONDS);
  const op = fadeWindow(frame, 0, total, 8, 12);
  const rule = ramp(frame, 8, 16);
  const titleMask = reveal(frame, 4, 16);
  const kickerOp = ramp(frame, 0, 8);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: op}}>
      <div style={{position: 'absolute', left: SPACE.marginX, top: SPACE.marginY + 40, width: 900}}>
        <div style={{fontFamily: FONT.mono, fontSize: TYPE.label + 1, letterSpacing: '0.22em', color: COLOR.amber, opacity: kickerOp}}>
          ACT {n}
        </div>
        <div
          style={{
            fontFamily: FONT.display,
            fontWeight: 700,
            fontSize: TYPE.actTitle,
            lineHeight: 1.05,
            letterSpacing: '-0.02em',
            color: COLOR.paper,
            clipPath: `inset(0 ${100 - titleMask}% 0 0)`,
            marginTop: 8,
          }}
        >
          {title}
        </div>
        <div style={{height: 2, width: 420 * rule, background: COLOR.amber, marginTop: 18}} />
      </div>
      {durationInFrames ? null : null}
    </AbsoluteFill>
  );
};
