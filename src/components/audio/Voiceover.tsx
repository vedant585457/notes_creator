import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';
import {VO, sec} from '../../utils/timing';

/** Narration clips placed at their cue times. Each clip is the generated WAV, unmodified. */
export const Voiceover: React.FC = () => (
  <>
    {VO.map((v) => (
      <Sequence key={v.n} from={sec(v.at)} durationInFrames={sec(v.dur) + 2} name={`VO ${v.n}`}>
        <Audio src={staticFile(`assets/audio/voiceover/voiceover_${v.n}.wav`)} volume={1} />
      </Sequence>
    ))}
  </>
);
