import React from 'react';
import {Audio, staticFile} from 'remotion';
import {MUSIC} from '../../utils/timing';
import {duckAt} from '../../utils/duck';

/** Original music bed with a frame-accurate ducking envelope under narration (see utils/duck.ts). */
export const BackgroundMusic: React.FC = () => (
  <Audio
    src={staticFile('assets/music/bed_a_minor.m4a')}
    volume={(f: number) => duckAt(f) * MUSIC.gain}
  />
);
