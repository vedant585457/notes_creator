import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, SPACE, TYPE} from '../styles/theme';
import {fadeWindow} from '../utils/animations';
import {sec} from '../utils/timing';

/** Command card: a dark mono panel that types the command at a fixed characters-per-second rate. */
export const CommandCard: React.FC<{text: string; cps: number; dur: number}> = ({text, cps, dur}) => {
  const frame = useCurrentFrame();
  const end = sec(dur);
  const op = fadeWindow(frame, 0, end, 8, 10);
  const shown = Math.min(text.length, Math.floor((frame / 30) * cps));
  const cursorOn = Math.floor(frame / 15) % 2 === 0;
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none', justifyContent: 'flex-end', alignItems: 'flex-start'}}>
      <div
        style={{
          margin: `0 ${SPACE.marginX}px ${SPACE.marginY}px`,
          background: 'rgba(16,19,25,0.94)',
          border: `1px solid ${COLOR.hairline}`,
          borderLeft: `3px solid ${COLOR.cyan}`,
          padding: '22px 30px',
          fontFamily: FONT.mono,
          fontSize: TYPE.code,
          color: COLOR.paper,
          whiteSpace: 'pre',
          maxWidth: 1500,
        }}
      >
        <span style={{color: COLOR.cyan}}>$ </span>
        {text.slice(0, shown)}
        <span style={{opacity: cursorOn ? 1 : 0, color: COLOR.amber}}>▌</span>
      </div>
    </AbsoluteFill>
  );
};
