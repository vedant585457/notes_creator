import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR, FONT, SPACE, TYPE} from '../styles/theme';
import {ramp, fadeWindow} from '../utils/animations';
import {sec} from '../utils/timing';

/** Editorial lower third: mono label over a display value, amber hairline. */
export const LowerThird: React.FC<{label: string; value: string; dur: number}> = ({label, value, dur}) => {
  const frame = useCurrentFrame();
  const end = sec(dur);
  const op = fadeWindow(frame, 0, end, 12, 10);
  const slide = (1 - ramp(frame, 0, 14)) * 24;
  const rule = ramp(frame, 6, 16);
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: SPACE.marginX, bottom: SPACE.marginY + 60, transform: `translateY(${slide}px)`}}>
        <div style={{fontFamily: FONT.mono, fontSize: TYPE.label, letterSpacing: '0.2em', color: COLOR.cyan}}>{label}</div>
        <div style={{fontFamily: FONT.display, fontWeight: 700, fontSize: TYPE.lowerValue, color: COLOR.paper, marginTop: 6}}>
          {value}
        </div>
        <div style={{height: 2, width: 560 * rule, background: COLOR.amber, marginTop: 12}} />
      </div>
    </AbsoluteFill>
  );
};
