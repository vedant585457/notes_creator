import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, TYPE} from '../styles/theme';
import {reveal, fadeWindow} from '../utils/animations';
import {sec} from '../utils/timing';

/** Kinetic sting: a short phrase mask-revealed in the centre, then held and cleared. Used sparingly. */
export const KeywordSting: React.FC<{text: string; color: 'amber' | 'red'; dur?: number}> = ({text, color, dur = 2.2}) => {
  const frame = useCurrentFrame();
  const end = sec(dur);
  const op = fadeWindow(frame, 0, end, 4, 12);
  const mask = reveal(frame, 0, 14);
  const hue = color === 'red' ? COLOR.red : COLOR.amber;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: op, pointerEvents: 'none'}}>
      <div
        style={{
          fontFamily: FONT.display,
          fontWeight: 700,
          fontSize: TYPE.sting,
          letterSpacing: '-0.01em',
          color: hue,
          textShadow: `0 0 40px ${hue}55`,
          clipPath: `inset(0 ${100 - mask}% 0 0)`,
          whiteSpace: 'nowrap',
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
