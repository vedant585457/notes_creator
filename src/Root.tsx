import React from 'react';
import {Composition} from 'remotion';
import {MainVideo} from './compositions/MainVideo';
import {FPS, HEIGHT, TOTAL_FRAMES, WIDTH} from './utils/timing';
import './styles/fonts.css';

export const Root: React.FC = () => (
  <Composition id="FlagHunters" component={MainVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
);
