import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR} from '../styles/theme';
import {EASE_IN_OUT, ramp} from '../utils/animations';

/**
 * Mask wipe used at chapter boundaries. `at` is local frame where the wipe begins; it sweeps a
 * solid ink bar across and away. Only used at a few boundaries (plan §3.7: restraint).
 */
export const MaskWipe: React.FC<{at: number; dur: number; from?: 'left' | 'right'}> = ({at, dur, from = 'left'}) => {
  const frame = useCurrentFrame();
  const p = ramp(frame, at, dur, EASE_IN_OUT);
  const x = from === 'left' ? -100 + p * 200 : 100 - p * 200;
  const visible = frame >= at && frame <= at + dur;
  if (!visible) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(90deg, transparent 0%, ${COLOR.ink} 45%, ${COLOR.ink} 55%, transparent 100%)`,
          transform: `translateX(${x}%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          width: 3,
          background: COLOR.amber,
          left: `${50 + x / 2}%`,
        }}
      />
    </AbsoluteFill>
  );
};

/** Black fade in from the first frame of the film. */
export const FadeFromBlack: React.FC<{frames: number}> = ({frames}) => {
  const frame = useCurrentFrame();
  const o = 1 - ramp(frame, 0, frames);
  return <AbsoluteFill style={{background: COLOR.ink, opacity: o, pointerEvents: 'none'}} />;
};
