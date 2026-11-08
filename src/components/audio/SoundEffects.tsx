import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';
import {SFX, sec} from '../../utils/timing';

/** Sound-effect cue sheet, rendered from utils/timing.ts (SFX array). */
export const SoundEffects: React.FC = () => (
  <>
    {SFX.map(([t, file, gain], i) => (
      <Sequence key={`${file}-${i}`} from={sec(t)} name={`sfx ${file}`}>
        <Audio src={staticFile(`assets/sfx/${file}.wav`)} volume={gain} />
      </Sequence>
    ))}
  </>
);
