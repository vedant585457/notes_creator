import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, TYPE} from '../styles/theme';
import {ramp, reveal, fadeWindow} from '../utils/animations';
import {sec} from '../utils/timing';

/** Opening title over the first footage shot. Question first, identity second. */
export const ColdOpen: React.FC<{dur: number}> = ({dur}) => {
  const frame = useCurrentFrame();
  const op = fadeWindow(frame, 0, sec(dur), 10, 14);
  const kicker = ramp(frame, 8, 14);
  const title = reveal(frame, 18, 20);
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(7,8,11,0.25), rgba(7,8,11,0.82))', opacity: op, pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 96, bottom: 150}}>
        <div style={{fontFamily: FONT.mono, fontSize: TYPE.label + 2, letterSpacing: '0.24em', color: COLOR.amber, opacity: kicker}}>
          CASE 001 · REVERSE ENGINEERING
        </div>
        <div
          style={{
            fontFamily: FONT.display,
            fontWeight: 700,
            fontSize: 176,
            lineHeight: 0.95,
            letterSpacing: '-0.035em',
            color: COLOR.paper,
            marginTop: 14,
            clipPath: `inset(0 ${100 - title}% 0 0)`,
          }}
        >
          FLAG HUNTERS
        </div>
      </div>
    </AbsoluteFill>
  );
};
