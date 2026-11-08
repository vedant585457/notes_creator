import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {ACTS, sec} from '../utils/timing';
import {COLOR, FONT} from '../styles/theme';
import {ramp} from '../utils/animations';

/** Thin chapter spine on the left edge: current act is lit, past acts muted, future acts hairline. */
export const ChapterRail: React.FC<{active: number}> = ({active}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 32, top: 360, display: 'flex', flexDirection: 'column', gap: 14}}>
        {ACTS.map((a, i) => {
          const on = i === active;
          return (
            <div key={a.n} style={{display: 'flex', alignItems: 'center', gap: 10, opacity: on ? 1 : 0.35}}>
              <div style={{width: on ? 22 : 10, height: 2, background: on ? COLOR.amber : COLOR.hairline}} />
              <span style={{fontFamily: FONT.mono, fontSize: 11, letterSpacing: '0.14em', color: on ? COLOR.paper : COLOR.muted, opacity: on ? ramp(frame, 0, 10) : 1}}>
                {on ? a.n : ''}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const activeActAt = (seconds: number): number => {
  let idx = -1;
  ACTS.forEach((a, i) => {
    if (seconds >= a.at) idx = i;
  });
  return idx;
};
export const _unused = sec;
