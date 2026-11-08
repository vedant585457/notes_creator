import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {Footage} from '../components/Footage';
import {ActCard} from '../components/ActCard';
import {LowerThird} from '../components/LowerThird';
import {KeywordSting} from '../components/KeywordSting';
import {CommandCard} from '../components/CommandCard';
import {Schematic} from '../components/Schematic';
import {FlagCallout} from '../components/FlagCallout';
import {EndCard} from '../components/EndCard';
import {ColdOpen} from '../components/ColdOpen';
import {Finish} from '../components/Graticule';
import {ChapterRail, activeActAt} from '../components/ChapterRail';
import {MaskWipe, FadeFromBlack} from '../components/Transition';
import {Voiceover} from '../components/audio/Voiceover';
import {BackgroundMusic} from '../components/audio/BackgroundMusic';
import {SoundEffects} from '../components/audio/SoundEffects';
import {
  ACTS, ACT_CARD_SECONDS, COMMANDS, FLAG_CALLOUT, FPS, LOWER_THIRDS, SCHEMATIC, STINGS, TRANSITIONS, sec,
} from '../utils/timing';

/**
 * Master timeline. Every block is placed by a timing constant; nothing here carries its own seconds.
 */
export const MainVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const active = activeActAt(frame / FPS);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Footage />

      <Sequence from={0} durationInFrames={sec(6)} name="cold open">
        <ColdOpen dur={6} />
      </Sequence>

      {ACTS.map((a) => (
        <Sequence key={a.n} from={sec(a.at)} durationInFrames={sec(ACT_CARD_SECONDS)} name={`act ${a.n}`}>
          <ActCard n={a.n} title={a.title} />
        </Sequence>
      ))}

      {LOWER_THIRDS.map((l) => (
        <Sequence key={l.label} from={sec(l.at)} durationInFrames={sec(l.dur)} name={`lt ${l.label}`}>
          <LowerThird label={l.label} value={l.value} dur={l.dur} />
        </Sequence>
      ))}

      {STINGS.map((s) => (
        <Sequence key={s.text} from={sec(s.at)} durationInFrames={sec(2.2)} name={`sting ${s.text}`}>
          <KeywordSting text={s.text} color={s.color} />
        </Sequence>
      ))}

      {COMMANDS.map((c) => (
        <Sequence key={c.text} from={sec(c.at)} durationInFrames={sec(c.end - c.at)} name="command">
          <CommandCard text={c.text} cps={c.cps} dur={c.end - c.at} />
        </Sequence>
      ))}

      <Sequence from={sec(SCHEMATIC.start)} durationInFrames={sec(SCHEMATIC.end - SCHEMATIC.start)} name="schematic">
        <Schematic />
      </Sequence>

      <Sequence from={sec(FLAG_CALLOUT.start)} durationInFrames={sec(FLAG_CALLOUT.end - FLAG_CALLOUT.start)} name="flag callout">
        <FlagCallout />
      </Sequence>

      <Sequence from={sec(105)} durationInFrames={TRANSITIONS.wipeFrames} name="wipe 105">
        <MaskWipe at={0} dur={TRANSITIONS.wipeFrames} />
      </Sequence>
      <Sequence from={sec(137)} durationInFrames={TRANSITIONS.wipeFrames} name="wipe 137">
        <MaskWipe at={0} dur={TRANSITIONS.wipeFrames} from="right" />
      </Sequence>

      <Sequence from={sec(148)} durationInFrames={sec(12)} name="end card">
        <EndCard dur={12} />
      </Sequence>

      <ChapterRail active={active} />
      <Finish />
      <FadeFromBlack frames={TRANSITIONS.fadeFromBlackFrames} />

      <Voiceover />
      <BackgroundMusic />
      <SoundEffects />
      {frame < 0 ? null : null}
    </AbsoluteFill>
  );
};
