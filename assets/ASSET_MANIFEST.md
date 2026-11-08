# Asset Manifest — Flag Hunters

Every non-code asset used by `final-video.mp4`, with source, licence and purpose.

| # | File | Type | Purpose | Source | Licence / rights |
|---|------|------|---------|--------|------------------|
| 1 | `../Screencast From 2026-11-08 12-56-12.webm` | Video (silent, 1920×1080, 30.3 fps, 5:37) | Primary footage of the whole film | Original screen recording in this repository | Project material. Original file is **not modified**; SHA-256 `ec6a25b7b0880ccabbc51eafb4bca86b4dcfbd11d2c378746d5423edb76d7723` |
| 2 | `video/source_1080p_h264.mp4` | Video (H.264 intermediate, CRF 16, GOP 30, no audio) | Seek-accurate playback copy of #1 for Remotion | Transcoded from #1 with FFmpeg (`libx264 -crf 16 -pix_fmt yuv420p -g 30 -an`) | Derivative of #1; git-ignored (regenerate with the command in README) |
| 3 | `audio/voiceover/voiceover_01.wav` … `voiceover_10.wav` | Narration (WAV, 44.1 kHz mono, 10 segments, 131 s total) | Full voiceover | Generated with Arena.ai `generate_speech`, voice `voice-00` (masculine narration voice selected in audition) | Generated for this project from the script in `plan.md §5` |
| 4 | `music/bed_a_minor.m4a` | Music bed (AAC 224 kb/s, 165 s, A minor) | Background bed, ducked under narration | **Original.** Synthesised deterministically by `scripts/synthesize_audio.py` (sine/triangle oscillators, seeded) | Owned by the project; no third-party samples or melodies |
| 5 | `sfx/impact.wav` | SFX | Title and reveal impacts | Original, `scripts/synthesize_audio.py` (sine sweep + noise) | Owned by the project |
| 6 | `sfx/whoosh.wav` | SFX | Act transitions | Original, filtered noise sweep | Owned by the project |
| 7 | `sfx/tick.wav` | SFX | Lower-third and label entry | Original, 2.5 kHz click | Owned by the project |
| 8 | `sfx/key.wav` | SFX | Typed command clicks | Original, dry noise burst | Owned by the project |
| 9 | `sfx/blip.wav` | SFX | Terminal data marker | Original, chirp | Owned by the project |
| 10 | `sfx/thud.wav` | SFX | "flag.txt not found" beat | Original, low thud | Owned by the project |
| 11 | `sfx/riser.wav` | SFX | Build into the payload | Original, rising sine + noise | Owned by the project |
| 12 | `sfx/chime.wav` | SFX | Result beat | Original, two-note bell | Owned by the project |

## Typefaces (bundled via npm, loaded through `src/styles/fonts.css`)

| Family | Weights used | Package | Licence |
|--------|--------------|---------|---------|
| Space Grotesk | 500, 700 | `@fontsource/space-grotesk` 5.x | SIL Open Font License 1.1 |
| Inter | 400, 600 | `@fontsource/inter` 5.x | SIL Open Font License 1.1 |
| JetBrains Mono | 400, 500 | `@fontsource/jetbrains-mono` 5.x | SIL Open Font License 1.1 |

## Rendering tooling (not shipped in the film)

| Component | Source | Licence |
|-----------|--------|---------|
| Chromium headless shell | `@sparticuz/chromium` 153 (npm), used via `REMOTION_BROWSER_EXECUTABLE` | BSD-3 (Chromium) / MIT (wrapper) |
| Remotion 4.0.541 | npm | Remotion licence (free for individuals and non-profit / teams under the company threshold — check your usage) |

## Explicitly not used

- No stock footage, stock photography or commercial music.
- No watermarked or unlicensed material.
- Pexels, Pixabay, Freesound and Mixkit were not reachable from this sandbox; every sound was therefore synthesised in-house rather than sourced, which avoids any licence question.
