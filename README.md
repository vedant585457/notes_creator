# notes_creator — *Flag Hunters* film

A narrated, motion-graphics edit of the repository's screen recording
(`Screencast From 2026-11-08 12-56-12.webm`), built with **Remotion 4 + React**.
It follows a reverse-engineering session from the challenge brief to "Correct flag!".

- **Deliverable:** `final-video.mp4` — 1920×1080, 30 fps, 2:40, H.264 High + AAC 320 kb/s stereo, −16 LUFS, −1.5 dBFS peak.
- **Plan:** `plan.md` (creative and technical plan, plus the *Production revision* section describing what was built).
- **Assets and licences:** `assets/ASSET_MANIFEST.md`.

## Repository layout

```
Screencast From 2026-11-08 12-56-12.webm   original footage (unmodified)
final-video.mp4                            rendered deliverable
plan.md                                    production plan
assets/
  video/source_1080p_h264.mp4              H.264 intermediate of the original (git-ignored, regenerate below)
  audio/voiceover/voiceover_01..10.wav     generated narration
  music/bed_a_minor.m4a                    original music bed
  sfx/*.wav                                original sound effects
  ASSET_MANIFEST.md
src/
  index.ts  Root.tsx                       entry points, composition registration
  compositions/MainVideo.tsx               master timeline (maps timing config to components)
  components/                              Footage, ColdOpen, ActCard, LowerThird, KeywordSting,
                                           CommandCard, Schematic, FlagCallout, EndCard, ChapterRail,
                                           Transition, Finish (grid/vignette/grain)
  components/audio/                        Voiceover, BackgroundMusic (ducked), SoundEffects
  utils/timing.ts                          ALL timing: shots, narration cues, acts, SFX cue sheet, transitions
  utils/duck.ts                            precomputed music-ducking envelope
  utils/animations.ts                      frame-driven easing helpers (no CSS keyframes)
  styles/theme.ts, fonts.css               palette, type scale, self-hosted fonts
scripts/
  synthesize_audio.py                      deterministic SFX + music generator (seeded)
  render_final.sh                          render + loudness normalise + encode
remotion.config.ts                         Remotion settings (optional Chromium override)
```

Design rule: timing lives in `src/utils/timing.ts`. Components never hard-code seconds, and every animation is a pure function of `useCurrentFrame()`.

## Setup

Requires Node 18+ and Python 3 (for the audio generator only).

```bash
npm install
```

Regenerate the audio assets (optional, deterministic):

```bash
python3 -m pip install numpy            # once
npm run audio:synth                     # writes assets/sfx and assets/music (the music is then encoded to m4a)
```

Regenerate the H.264 intermediate of the source (required before rendering):

```bash
mkdir -p assets/video public
ffmpeg -i "Screencast From 2026-11-08 12-56-12.webm" -c:v libx264 -preset medium -crf 16 \
  -pix_fmt yuv420p -g 30 -keyint_min 30 -sc_threshold 0 -an -movflags +faststart \
  assets/video/source_1080p_h264.mp4
```

Remotion reads its static files from `public/`. Mirror the assets there (hard links, so nothing is duplicated):

```bash
cp -al assets public/assets
ln assets/video/source_1080p_h264.mp4 public/footage.mp4
```

## Preview

```bash
npm start            # Remotion Studio, composition "FlagHunters"
npm run typecheck    # TypeScript check
```

## Render

```bash
npm run render       # Remotion master only (writes final-video.mp4 with no loudness normalisation)
# or the full pipeline used for the delivered file (master → two-pass loudness → final-video.mp4):
bash scripts/render_final.sh
```

The delivered encode uses `-crf 19 -preset slow`, limited-range BT.709, `+faststart`. A CRF 16 master
is ~110 MB, which is larger than the repository artifact budget, so the final encode is slightly lower
in bitrate. Source footage is screen content, so this is visually transparent. Re-render the master with
`--crf=16` and skip the final encode if you need the largest file.

### Rendering in restricted sandboxes

Remotion downloads Chrome for Testing from a CDN by default. If that is blocked, use a Chromium
binary and point Remotion at it through `REMOTION_BROWSER_EXECUTABLE`. The one used here came from the
npm package `@sparticuz/chromium` (`npm i --no-save @sparticuz/chromium@153`):

```bash
node -e "require('@sparticuz/chromium').executablePath().then(p=>console.log(p))"   # extracts /tmp/chromium
# its shared libraries ship as brotli archives in node_modules/@sparticuz/chromium/bin/*.tar.br
# extract al2023.tar.br (libnss3 etc.) to /tmp/chromium-libs and set:
export LD_LIBRARY_PATH=/tmp/chromium-libs/lib:/tmp/chromium-libs
export REMOTION_BROWSER_EXECUTABLE=/tmp/chromium
```

The machine used for the render had 2 cores (`Config.setConcurrency(2)` in `remotion.config.ts`).
A full render took about 25 minutes.

## Voiceover

The narration was generated with a text-to-speech voice (voice-00). The text is the script in `plan.md §5`,
split into the 10 segments listed in `src/utils/timing.ts` (`VO`). If you regenerate the narration, update
`VO[].dur` to the measured length of each new WAV. Each clip is placed at its `at` time.

## Known limitations

- The footage is silent. All sound (narration, music, effects) is added in post.
- Source-to-narration mapping was verified against frame samples, not frame-by-frame. Sub-beat alignment is within about ±5 s.
- Music ducking is a frame-based gain envelope keyed to the narration windows. It is not a sidechain compressor.
