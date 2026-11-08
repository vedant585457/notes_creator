import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, interpolate, useCurrentFrame, useVideoConfig, staticFile} from 'remotion';
import {SHOTS, Shot, sec} from '../utils/timing';
import {ramp} from '../utils/animations';

/** Original screencast, graded lightly. The file is never modified: it is read as-is. */
const GRADE = 'contrast(1.06) saturate(1.04) brightness(1.01)';

const ShotClip: React.FC<{shot: Shot}> = ({shot}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const dur = sec(shot.end - shot.start);
  // Slow 3 % push-in across each shot (scale only, never a crop jitter).
  const push = interpolate(frame, [0, durationInFrames], [1.0, 1.03], {extrapolateRight: 'clamp'});
  // Only the cold open fades up from black; every other shot is a hard cut (no black gap).
  const enter = shot.start === 0 ? ramp(frame, 0, 12) : 1;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <AbsoluteFill style={{transform: `scale(${push})`, opacity: enter, filter: GRADE}}>
        <OffthreadVideo
          src={staticFile('footage.mp4')}
          startFrom={sec(shot.src)}
          endAt={sec(shot.src) + dur}
          muted
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      </AbsoluteFill>
      {shot.dim ? <AbsoluteFill style={{background: `rgba(7,8,11,${1 - shot.dim})`}} /> : null}
    </AbsoluteFill>
  );
};

/** Places every shot on the timeline from the SHOTS table. */
export const Footage: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    {SHOTS.map((s) => (
      <Sequence key={s.id} from={sec(s.start)} durationInFrames={sec(s.end - s.start)} name={s.id}>
        <ShotClip shot={s} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
