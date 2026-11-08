import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLOR} from '../styles/theme';

/** Film finish: fine grid, vignette and seeded grain. Grain seed = frame, so it is deterministic. */
export const Finish: React.FC<{grain?: number}> = ({grain = 0.035}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${COLOR.hairline}55 1px, transparent 1px), linear-gradient(90deg, ${COLOR.hairline}55 1px, transparent 1px)`,
          backgroundSize: '96px 96px',
          opacity: 0.09,
        }}
      />
      <AbsoluteFill
        style={{background: 'radial-gradient(ellipse at center, transparent 58%, rgba(0,0,0,0.55) 100%)'}}
      />
      <AbsoluteFill style={{opacity: grain, mixBlendMode: 'overlay'}}>
        <svg width="100%" height="100%">
          <filter id="g">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={frame} stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#g)" />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
