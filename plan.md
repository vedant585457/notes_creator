# PROFESSIONAL VIDEO PRODUCTION PLAN

**Project:** *Flag Hunters* — a reverse-engineering session, directed
**Source material:** `Screencast From 2026-11-08 12-56-12.webm` (5:37, 1920×1080, 30.3 fps, no audio)
**Deliverable:** `final-video.mp4` — 1920×1080, 30 fps, H.264 + AAC, ~3:40
**Production framework:** Remotion 4 (React) + FFmpeg, original voiceover + original audio design

---

## 1. Project Overview

### 1.1 Video concept
A near-silent, 5½-minute screen recording of a real reverse-engineering session is rebuilt as a
**short, narrated, cinematic "case file"** — the story of how one CTF challenge (*Flag Hunters*, cyLab Academy) goes from an empty answer box to **"Correct flag!"**, solved
with a language-model copilot in the loop.

The edit is a **documentary explainer**: the audience watches the actual screen, while narration
and a designed motion-graphics layer explain *what* is being looked at and *why* it matters.
Nothing is invented: every command, insight, output line and result shown in the film comes from
the source recording.

### 1.2 Main subject
The unedited work session: browser (cyLab Academy challenge page, Arena.ai chat) + Warp terminal,
recorded on macOS. The "character" is the *investigation itself* — the loop of
**hypothesis → one command → evidence → next hypothesis**.

### 1.3 Intended audience
- Developers, CS students and CTF beginners who want to see methodology, not magic.
- Security-curious viewers who have never watched a reverse-engineering session.
- No prior knowledge of the challenge is assumed; the film teaches the *shape* of the exploit.

### 1.4 Communication objective
1. Show that solving a reverse-engineering challenge is a **methodical reading exercise**, not a trick.
2. Demonstrate the **human + AI copilot loop** honestly: the model proposes one command at a time,
   the human supplies real evidence.
3. Explain the actual vulnerability in plain language: a **user-controlled lyric line is split on a
   semicolon**, producing a synthetic `RETURN 0` that redirects execution to line 0 — the secret
   intro that contains the flag.

### 1.5 Desired emotional impact
Curiosity → mild tension (the program will not print it) → the click of understanding (the diagram)
→ satisfaction (flag in the output) → closure ("Correct flag!"). The tone is *quietly confident*,
like a well-made technical documentary: no hype, no jump-cut chaos, no meme energy.

### 1.6 Overall creative direction
"**Terminal noir**": near-black canvas, warm amber accent (the color of the challenge platform),
cool cyan for machine/terminal voice, off-white typography, film grain and a soft vignette.
Footage is treated like *evidence* — framed, pushed into, labelled, never stretched or replaced.
Motion graphics behave like a documentary graphics package: chapter rail, act cards, mono-type
labels, one animated schematic, one flag callout, one end card.

---

## 2. Source Video Analysis

### 2.1 Technical facts (measured with FFprobe/FFmpeg)

| Property | Value |
|---|---|
| Source filename | `Screencast From 2026-11-08 12-56-12.webm` |
| Container / codec | Matroska / VP8, `yuv420p`, BT.709, progressive |
| Duration | 00:05:37.02 (337.02 s) |
| Resolution | 1920 × 1080 |
| Frame rate | 30.30 fps (constant ~30) |
| Aspect ratio | 16:9, DAR 1:1 |
| Bitrate | ~1.06 Mb/s |
| Audio | **None** (single video stream, no audio track) |
| Encoder | GStreamer matroskamux (GNOME screen recorder) |
| Capture content | Full macOS desktop: Chrome tabs + Warp terminal |

The original `.webm` is **preserved untouched** (`source/` stays as-is). A frame-accurate,
seek-safe H.264 intermediate is generated in `assets/video/` for Remotion playback.

### 2.2 Scene-by-scene timeline of the source (verified beats, frame inspection)

Timecodes are source time (`SRC`). Boundaries were verified with scene-change detection and
contact sheets; sub-beat positions are approximate to ±5 s.

| SRC time | What is actually on screen |
|---|---|
| 00:00–00:20 | cyLab Academy Challenge Library, "Flag Hunters" modal: *Reverse Engineering, Easy, by tnesh, 2610 pts, 68% solved*. Description about a hidden refrain the program does not print by default. FLAG field empty. |
| 00:20–00:45 | Arena.ai chat: a system-style prompt defining an interactive CTF copilot: solve one step at a time, output exactly one command, wait for output. |
| 00:45–01:15 | Warp terminal in the challenge folder: `ls -la` (spacer `lyrics.json` visible); assistant reasons about the source. |
| 01:15–02:00 | Terminal: `lyric-reader.py` source is shown in full (`reader(song, startLabel)`, `[VERSE1]` / `[REFRAN]` / `[RETURN]` markers, `CROWD` line calls `input('Crowd: ')`, `RETURN n` sets the next index, `[END]` ends the loop). |
| 02:00–03:00 | `cat flag.txt … || echo "flag.txt not found"` → **flag.txt not found**. Assistant states the `[REFRAIN]` recursion insight. |
| 03:00–04:20 | `lyrics.json` contents are visible (includes `secret_intro`, which holds the flag), and the local program run prints output. |
| 04:20–05:00 | `nc xebec.cylabacademy.net 20544` runs; the song stops at the `Crowd:` prompt. The injection `' x;RETURN 0'` is typed (with `sleep 60`). |
| 05:00–05:30 | Program output loops back to line 0; the flag appears inside the lyric output. Transcript shows the result. |
| 05:30–05:37 | Challenge Library: flag submitted, toast **"Correct flag!"**. End of source. |

### 2.3 Important visual moments (used deliberately)
1. The empty flag field (00:00) — the "before".
2. The system prompt being written (00:20) — establishes the copilot contract.
3. First `ls -la` / `cat` in the terminal (00:44–00:60) — recon begins.
4. `flag.txt not found` (00:105) — the obstacle that forces the real exploit.
5. Remote program stopping at `Crowd:` (00:172) — the injection point, in frame.
6. The `'; RETURN 0'` command line (00:246) — the turning point.
7. The flag inside a lyric line (00:279) — the payoff.
8. `FLAG_FOUND` (00:302) and **"Correct flag!"** (00:335) — resolution.

### 2.4 Sections that need enhancement / trimming
- **Trim:** empty terminal dead air (00:44–00:55), long idle "Thinking…" waits (00:40–00:46, 00:130–00:160, 00:205–00:245), the repeated refrain spam after the flag (00:280–00:300).
- **Enhance:** the challenge brief (illegible at full-frame 1080p), the assistant's key reasoning lines (tiny specks in the recording), the semicolon logic (needs a diagram), the flag line (needs a callout).
- **Pacing:** 8 acts, ~25–30 s each; cuts land on narration beats, not on the source's cursor movements.

### 2.5 Existing audio
None. All sound in the deliverable (narration, music, effects) is created in this production.

---

## 3. Creative Direction

### 3.1 Visual identity
- **Palette**
  - Ink `#07080B` (canvas), Panel `#101319`, Hairline `#242A36`
  - Amber `#FF7A2F` (primary accent — platform/lock/file), Amber light `#FFB27A`
  - Cyan `#59E3C8` (machine/terminal data), Signal Red `#FF4D5E` (only for "not found" / obstacle)
  - Paper `#F3F1EC` (type), Muted `#9AA3B2` (secondary type)
- **Texture:** fine 1-px grid at 4 % opacity, animated film grain (3 %), soft vignette, very subtle
  chromatic edge on highlights. No lens flares, no bokeh spam.
- **Grade on footage:** slight contrast lift (S-curve), shadows cooled toward cobalt, highlights left
  neutral, saturation +4 % and a touch of sharpening, so the amber UI of the platform carries the frame.
  Screen content stays legible: **no heavy LUTs, no crushed blacks over text**.

### 3.2 Editing style
- **Cut on information**, not on movement. Every shot has a job: establish, reveal, explain, resolve.
- Speeds: real-time for reading moments (so the viewer can read proof), **1.0×–1.6×** fast-forward for
  waits, never below 1× (no slow motion on UI text).
- Repeat-framing: the same challenge page is shown three times — empty → instance running → solved.
  That repetition *is* the structure.
- Average shot length target: 4.5–7 s; no shot shorter than 2 s except in the montage of recon commands.

### 3.3 Cinematic treatment
- Footage lives inside an implied "screen" with a 2–3 % push-in on every shot (Ken-Burns by scale,
  not by crop jitter) so the frame is never dead.
- Deliberate depth: background grid drifts slower than the footage; foreground type sits above with
  a slight parallax offset (±6 px).
- Rack-focus feeling achieved with masked crops: a clean rectangular "lens" region sharp, the rest
  dimmed to 18 % with a 40 px feather, used for the three most important reveals (description,
  `'; RETURN 0'`, flag line).

### 3.4 Motion graphics direction
Editorial, restrained, technical: mono uppercase labels, thin rules, numbers as indices.
Motion primitives: 8–14 frame ease-out rises, mask wipes, 1-px rule draws, tick counters.
Every graphic carries information — no decorative shapes. Nothing animates for more than 24 frames
unless it is the schematic or the flag reveal.

### 3.5 Typography direction
- **Display / titles:** Space Grotesk (tight tracking, 700) — modern, technical, not corporate.
- **Body / labels / lower thirds:** Inter (400/500/600).
- **Technical / code / timestamps:** JetBrains Mono (400/500) — used for commands, line numbers,
  chapter indices, and any literal machine text.
- Scale system (1080p): act titles 104 px, big statements 84 px, lower-third title 34 px, label 13 px
  (mono, +18 % tracking), code 26–30 px. Minimum on-screen size for factual text: 22 px.

### 3.6 Color palette usage rule
Amber = human intent (the challenge, the answer, the flag). Cyan = machine output (terminal,
assistant text). Red appears exactly twice: `flag.txt not found`, and the "locked" hint rows.

### 3.7 Transition style
Three tools only:
1. **Hard cut** (default, ~70 % of cuts).
2. **Whip-pan wipe** with 3-frame directional motion blur, used between acts (max 6 times).
3. **Amber rule / mask reveal** (a 1-px line expands to a full wipe) for chapter cards and the ending.
No cross-dissolves on text, no zoom-blur abuse, no star wipes.

### 3.8 Sound design direction
"Quiet room with a pulse": a low, slowly evolving synth bed; dry UI clicks that belong to the actions
on screen; sub-impact on chapter cards; a rising noise sweep into the injection; one clean chime on
`FLAG_FOUND`. Narration sits forward and dry (short plate reverb, -18 dB).

---

## 4. Detailed Scene-by-Scene Editing Plan

Master timeline, 30 fps, 1920×1080. Act boundaries are also the chapter-rail beats.
`SRC` = source in-point in the original recording.

| Timecode (final) | Source Footage | Editing Action | Motion Graphics | Voiceover | Sound Design |
|---|---|---|---|---|---|
| **00:00.0–00:09.0** (0–270f) | SRC 00:00–00:09 (challenge modal), desaturated + pushed 118 % to the description | Cold open: footage fades up from black at 20 %, scaled inside a bordered "evidence" plate | Mono kicker `CASE 001 / REVERSE ENGINEERING`, then title **FLAG HUNTERS** rising with a mask wipe; `CyLab Academy · Reverse Engineering` under it | "Somewhere in this challenge is a flag the program was never meant to print." | Low sub drone fades in; single sub impact on title; whoosh into Act 1 |
| **00:09–00:34** (270–1020f) | SRC 00:00–00:09 + 00:110–00:125 (modal with instance) | Hold on the modal, slow 3 % push. Lens region over the description text; FLAG field legible | Lower third `01 — THE BRIEF`; animated label set: `CATEGORY Reverse Engineering`, `DIFFICULTY Easy`, `AUTHOR tnesh`; keyword sting `HIDDEN REFRAIN` | "This is Flag Hunters — a reverse engineering challenge hosted on cyLab Academy. The brief is simple: the program prints a song, jumping from verses into a refrain the way a function call returns. There's a hidden refrain it never prints by default. Get it to print, and something is waiting inside." | Warm pad enters (music A); soft UI tick as lower third lands; quiet paper-rumble under push |
| **00:34–00:59** (1020–1770f) | SRC 00:09–00:40 (Arena chat, prompt being written) | Cut to chat; 1.4× on the typing; crop to composer + prompt header; slight vertical drift | Act card `02 — THE COPILOT`; mono quote block of the actual instruction: *"output exactly one command … wait for the user's terminal output"*; chip `HUMAN IN THE LOOP` | "So no exploit kit, no brute force. A language model is given one job: be a reverse-engineering copilot. Analyse the evidence, propose exactly one command, then wait for the output before deciding the next move." | Bed continues; typing clicks (light, sparse); soft whoosh on act card; a single low tick on "one command" |
| **00:59–01:30** (1770–2700f) | SRC 00:40–00:80 (assistant's `ls -la`, empty terminal, `cat`, code view) | Three-beat recon montage: assistant command → terminal `ls` → `cat lyric-reader.py`; footage accelerated 1.5× on wait segments; last beat locks on the code window (light theme) | `03 — RECON`; command card types `ls -la` then `cat lyric-reader.py` in mono; line-number gutter graphic `001 … 100` slides in beside the code; callout labels `REFRAIN`, `RETURN` | "First step is recon. List the directory, then read the source: a single Python file, lyric-reader.py. Inside it, every REFRAIN is a subroutine call, and every RETURN entry is where the song jumps back." | Bed thins to pulse; two dry keystroke clusters; paper-slide whoosh on each cut; cyan data blips as labels appear |
| **01:30–01:56** (2700–3480f) | SRC 00:100–00:110 (run script, `flag.txt not found`) | Real-time; crop to terminal output block. Freeze 12 frames on `flag.txt not found` | Act card `04 — THE OBSTACLE`; keyword sting in red `flag.txt NOT FOUND`; mono footnote `the file only exists on the server` | "Running it locally prints the whole song — but there is no flag file on this machine. The flag only exists on the challenge server." | Music drops to a single sub; error thud (soft, unclipped); room tone close |
| **01:56–02:22** (3480–4260f) | SRC 00:110–00:180 (launch instance, `nc …`, remote output, `Crowd:` prompt) | Cut to challenge page → Launch Instance → terminal `nc`; crop over `nc xebec.cylabacademy.net 20544`; then the remote song output with the cursor waiting | `05 — THE INSTANCE`; instance chip `RUNNING · 20544`; command card types the `nc` line; pulsing ring on the `Crowd:` prompt | "So the instance is launched, and the program is reached over the network. Same song, same listeners — and this time it stops and asks the crowd for a line." | Riser under the cut; modem-ish data blips; music pulse returns low; a dry click on `Crowd:` |
| **02:22–02:52** (4260–5160f) | SRC 00:180–00:246 (assistant's deep analysis, then command) | Pasting-output beat, then the reasoning block with three options; lens region on the "CROWD input replaces song_lines[lip]" line; 1.4× through idle thinking | `06 — THE INSIGHT`; the **animated schematic**: song line indices 0…N, marker `[VERSE1]`, `[REFRAIN]`, `RETURN`, a red "writes here" pointer on the refrain line, then a `;` splitting the line into `Crowd:` + `RETURN 0` and an arrow jumping back to line 0 (`secret_intro`) | "Back in the chat, the output is pasted in and the assistant walks the code line by line. It lays out three options: read the file, patch the program, or hijack the input. Then it stops on the one that works. Whatever the crowd types is written straight back into the song at that index — and the reader splits lines on a semicolon." | Schematic: delicate ticks as lines draw, sub pulse on each marker, one rising tone into the arrow; bed opens up |
| **02:52–03:19** (5160–5970f) | SRC 00:250–00:290 (running the exploit, flag printed) | Real-time command typing (reproduced as type, synced to the footage), then the output streams; **flag line** isolated with a lens region and a bracket callout | `07 — THE PAYLOAD`; command card: `(echo ' x;RETURN 0'; sleep 60) | nc …`; then `RETURN 0 → LINE 0` tag; flag line framed with animated brackets + mono label `FLAG IN THE LYRICS`; amber glow pulse | Typing clicks built to the rhythm; riser → **impact** on flag reveal; music hits a single warm chord; sparkle tail |
| **03:19–03:34** (5970–6420f) | SRC 00:290–00:337 (FLAG_FOUND, submit, "Correct flag!") | Cut to chat `FLAG_FOUND` → challenge page → flag typed → Submit → toast | `08 — THE RESULT`; stamp-style `FLAG FOUND` with cyan rule; then the toast `Correct flag!` circled with a thin amber ring | "The transcript goes back for verification. The line the crowd wrote was re-read as a return address, execution jumped to the intro nobody was supposed to read, and the flag printed inside the song. One field left. The flag goes in — and the challenge closes with two words." | Music resolves to a warmer chord; UI click on submit; bright chime on "Correct flag!" |
| **03:34–03:44** (6420–6720f) | Frozen last frame, dimmed to 12 % + grain | End card: full screen graphics over near-black | Recap chips `1 SOURCE → 2 CROWD INPUT → 3 RETURN 0 → 4 LINE 0`; credit line `Footage: live session · Copilot: Arena.ai · Narration: synthetic voice`; title mark `FLAG HUNTERS / SOLVED` | "No framework. Just a source file, a subroutine with a missing return address — and a copilot that knew where to look." | Final chord decay + sub tail; one soft click as the credit line lands; fade to silence |

**Total duration:** 6720 frames = **224 s = 3:44** at 30 fps.

---

## 5. Voiceover Script

Delivery: warm, low-energy documentary confidence. Measure: conversational, ~145 wpm, allowing
breaths at every `/`. Emphasis in **bold**. No up-talk, no salesmanship, no smile-voice.

| # | Timecode | Script | Delivery notes |
|---|---|---|---|
| 1 | 00:01–00:08 | "Somewhere in this challenge is a flag the program was never meant to print." | Half-volume, intimate; long pause after. Land on "never". |
| 2 | 00:10–00:32 | "This is **Flag Hunters** — a reverse engineering challenge hosted on cyLab Academy. / The brief is simple: the program prints a song, jumping from verses into a refrain — the way a function call returns. / There's a hidden refrain it never prints by default. Get it to print it, and there might be something waiting inside." | Explainer calm. Lift slightly on "Flag Hunters". Slight smile on "something waiting inside". |
| 3 | 00:35–00:57 | "So there's no exploit kit here, and no brute force. / A language model is given one job — act as a reverse engineering copilot. / Analyse the evidence, propose exactly **one** command, then wait for the terminal output before deciding the next move." | Slower on the three-part instruction; firm on "one". |
| 4 | 01:00–01:28 | "First step is recon. List the directory, then read the source — one Python file, `lyric-reader.py`. / Inside it, the song is the program. Every refrain is a subroutine call, and every **return** entry is where the song jumps back." | Precise, methodical. Tiny pause between the two sentences. |
| 5 | 01:31–01:53 | "Run it locally and the whole song prints out. / But there's no flag file on this machine — the flag only exists on the challenge server." | First sentence plain; second flatter, more serious. |
| 6 | 01:57–02:19 | "So the instance gets launched, and the program is reached over the network. / Same song, same lyrics — and this time it stops, and asks the crowd for a line." | Momentum returning; dry delivery on "asks the crowd". |
| 7 | 02:23–02:50 | "Back in the chat, the output is pasted in, and the assistant walks the code line by line. / It lays out the options: read the file, patch the program, or hijack the input. Then it stops on the one that works. / Whatever the crowd types is written straight back into the song at that index — and the reader splits lines on a semicolon." | Third sentence is the key: slow down, clear consonants on "semicolon". |
| 8 | 02:53–03:17 | "The payload is a single shell line: echo a value containing a semicolon and `RETURN 0`, hold the connection open, and pipe it into the program. / The song plays again, takes the crowd's line — and follows the new return address backwards, to the intro nobody was supposed to read." | Build tension through the command; release on "backwards". |
| 9 | 03:20–03:32 | "The flag prints in the middle of the lyrics, hidden in the program's own output. / The line the crowd wrote was re-read as a return address — execution jumped to line zero, and the flag came with it. / One field left." | Narrating the proof: even, factual, quiet satisfaction. |
| 10 | 03:33–03:43 | "The flag goes in, and the challenge closes with two words. / No framework. Just a source file, a subroutine with a missing return — and a copilot that knew where to look." | Final line slower, lower, with a small pause before "and a copilot". |
| — | On screen | **"Correct flag!"** is a *toast in the footage*, not narration — the VO says "two words" and lets the footage answer. | Intentional: the image speaks. |

Total narration ≈ 430 words ≈ 3:05 of speech, leaving room for breaths, the schematic beat and the
end card. The voiceover is mixed as the anchor; all other audio ducks under it.

---

## 6. Motion Graphics Plan

### 6.1 System
- **Chapter rail** (left edge, 32 px inset): eight 2-px ticks, index digits in JetBrains Mono 11 px;
  current act = amber + label revealed, past acts = muted, future acts = hairline only. It gives the
  film a spine and tells the viewer where they are. Fades out during the schematic and the end card.
- **Act cards**: kicker (`ACT 03`), title (`RECON`), one 1-px amber rule that draws left→right
  (14 frames), 12 px mono subtitle. Upper-left, 96 px margin. Duration 2.2 s, then it moves up 24 px
  and fades to 55 % as a persistent corner label for the act.
- **Lower thirds**: two-line editorial block — small mono label (`PLATFORM`), value (`cyLab Academy`),
  amber hairline, 420 ms in / 300 ms out, never over a face (there are none) and never over the
  narration's key word.
- **Kinetic type stings**: 1–3 words, mask-revealed per line, 60–84 px, used 5 times in the whole film
  (`HIDDEN REFRAIN`, `flag.txt NOT FOUND`, `RETURN 0`, `LINE 0`, `FLAG FOUND`). Each has an audio accent.
- **Command cards**: a dark mono panel (JetBrains Mono 27 px, cyan prompt glyph) that types a command
  character-by-character at 2 characters per frame, with a blinking block cursor and a subtle
  key-click per 3 characters. Used for `ls -lau`… (only commands actually seen in the source).
- **Schematic (Act 06, the centerpiece)**: a vertical list of lyric lines with real indices. Three
  labelled anchors (`[VERSE1]`, `[REFRAIN]`, `RETURN`), a highlight that travels line to line, then:
  the crowd input arrives → the line at index *k* is overwritten → a semicolon splits it →
  `RETURN 0` → an amber arc jumps back to index 0 (`secret_intro`) → the flag line lights up.
  Everything is drawn with SVG paths + frame-driven `strokeDashoffset`; ~5 s of build, 3 s hold.
- **Flag callout**: animated bracket corners (24 px) snap around the flag text inside the terminal
  output, plus a leader line and mono label; the flag itself gets a slow 1-px scan-line sweep.
- **Progress indicator**: a 1-px timeline hairline at the very bottom (right half only) showing elapsed
  chapters — subtle, 55 % opacity, never competing with subtitles.
- **End card**: recap chips animating in sequence, credit line, `FLAG HUNTERS / SOLVED` lockup.

### 6.2 Restraint rules
- Never more than **two** graphic elements on screen at once (rail counts as one, always).
- No graphic may cover text the narration is pointing at.
- No text animation longer than 24 frames except the schematic and the end card.
- All type snaps to an 8-px baseline grid; safe margins 96 px top/bottom, 72 px sides.

---

## 7. Sound Design Plan

### 7.1 Bed (music)
Original composition, synthesised for this production (no clearance issues):
- 3-part ambient/tech bed, key of A minor, 72 BPM pulse, sub-bass root A1, airy pad, sparse arpeggio
  during recon, single held chord at the payoff, resolution in A major-ish third on the end card.
- Structure follows the acts: drone (0–34 s) → pad enters (34 s) → pulse (59 s) → thin/pulse only
  (90 s) → drop-out on the obstacle (90–116 s) → return with pulse (116 s) → open for the schematic
  (142–172 s) → riser + impact at 172 s → warm resolve (199 s) → tail on the end card.
- Target level under narration: **-27 LUFS-S** (≈ -20 dB relative to the voice), rising to -20 LUFS-S
  in the two dialogue-free beats (schematic hold, end card).

### 7.2 Effects (all original, synthesised)
| Effect | Where | Character |
|---|---|---|
| Sub impact | Title, chapter cards, flag reveal | 45–70 Hz sine thump + short noise body, 350 ms |
| Whoosh | Whip transitions (6×) | filtered noise sweep 300–1200 Hz, 380 ms, stereo pan across |
| UI tick | Lower thirds, labels, chips | 2.5 kHz click, 18 ms, -24 dB |
| Keystroke cluster | Typed commands, prompt writing (light) | dry clicks, 6–10 per second, varied pitch |
| Data blip | Terminal output, IDs | short sine chirp 900–1400 Hz, 60 ms |
| Error thud | `flag.txt not found` | lowpassed noise + 90 Hz drop |
| Riser | Into payload / schematic arrow | noise + rising sine 6 s, ends in impact |
| Chime | `FLAG_FOUND`, `Correct flag!` | triangle bell, two notes (A5, E6) with long tail, -20 dB |

### 7.3 Mix
- Narration: 1.0 anchor, HPF 90 Hz, gentle 3:1 compression, +1 dB presence at 3 kHz, de-ess lightly,
  peak ≤ -3 dBFS, integrated **-16 LUFS** in dialogue.
- Music: -20 dB under speech with 180 ms attack / 400 ms release ducking (implemented as a
  frame-based volume envelope in Remotion, keyed to narration windows); -3 dB extra during key lines.
- SFX: -18 to -12 dB (impacts accent only, never under speech), whooshes -22 dB.
- Master: peak -1 dBTP, integrated -14 LUFS (web), true-peak limiter, no clipping, mono-safe voice.

---

## 8. External Assets Required

| Asset | Purpose | Format | Source | License | Used in |
|---|---|---|---|---|---|
| Source screencast | All footage | WebM VP8 (kept) + H.264 MP4 intermediate | Already in repo | Project material, unmodified original preserved | All acts |
| Space Grotesk (500/700) | Titles, act cards, end card | WOFF2 | `@fontsource/space-grotesk` (npm) | SIL OFL 1.1 | Titles, cards |
| Inter (400/500/600) | Body, lower thirds | WOFF2 | `@fontsource/inter` (npm) | SIL OFL 1.1 | Lower thirds, notes |
| JetBrains Mono (400/500) | Code, labels, rail, chips | WOFF2 | `@fontsource/jetbrains-mono` (npm) | SIL OFL 1.1 | Command cards, schematic |
| Narration voice | Voiceover | WAV 48 kHz | Arena `add_voice` / `generate_speech` (synthetic TTS) | Generated for this project | All acts, 10 segments |
| Music bed | Emotional bed | WAV 48 kHz | **Original**, synthesised with Python/NumPy for this project | Owned / original | All acts |
| SFX set (9) | Accents, transitions, UI | WAV 48 kHz | **Original**, synthesised for this project | Owned / original | Throughout |
| Grain / vignette / grid | Texture overlays | Procedural in Remotion | Generated in code | Original | All acts |

No third-party footage, stock clips or commercial music are used, so the original message and the
footage integrity are preserved, and there are no licensing liabilities. Every asset is logged in
`assets/ASSET_MANIFEST.md` with source, license and purpose.

**Note on network access in this environment:** external asset libraries (Pexels, Pixabay, Freesound,
Google Fonts CDN) are not reachable from the sandbox; fonts are therefore installed from the npm
registry (OFL, redistributable) and music/SFX are composed and synthesised locally, which satisfies
the licensing requirements without relying on unverifiable downloads.

---

## 9. Technical Implementation Plan

### 9.1 Composition architecture
```
src/
  Root.tsx                     # registers <Composition id="FlagHunters" 1920x1080 30fps 6720f>
  compositions/
    MainVideo.tsx              # master timeline: maps ACTS -> <Sequence> + global layers
  components/
    Footage.tsx                # OffthreadVideo + crop/zoom/grade (deterministic camera)
    OpeningSequence.tsx        # cold open + title lockup
    ActCard.tsx                # kicker/title/rule, persistent corner label
    LowerThird.tsx             # editorial label block
    KeywordSting.tsx           # kinetic type
    CommandCard.tsx            # typing command panel
    Schematic.tsx              # SVG line-index / RETURN 0 diagram
    FlagCallout.tsx            # bracket callout + label
    EndCard.tsx                # recap chips + credits
    ChapterRail.tsx            # act spine (right-side index + ticks)
    Graticule.tsx              # grid, grain, vignette, scanline (procedural)
    Transition.tsx             # whip wipe / mask reveal wrappers
    ClosingSequence.tsx
    audio/
      Voiceover.tsx            # 10 <Audio> cues from assets/audio/voiceover
      BackgroundMusic.tsx      # bed with ducking envelope
      SoundEffects.tsx         # SFX cues from cue sheet
  styles/theme.ts              # palette, type scale, font families, spacing
  utils/
    timing.ts                  # ACTS, fps constants, helpers (sec->frames)
    animations.ts              # ease curves, spring presets, interpolation helpers
    cues.ts                    # single source of truth: VO/SFX/music cue frames
```

### 9.2 Determinism & timing
- All timing lives in `src/utils/timing.ts` + `src/utils/cues.ts`. No magic numbers in components.
- Animation uses `interpolate`/`spring` on `useCurrentFrame()` only — zero CSS keyframes, zero
  `setTimeout`, zero `Math.random()` without a seeded PRNG (grain uses a seeded hash).
- Footage playback positions are computed from `frame` (never from media callbacks), so renders are
  frame-accurate; `<OffthreadVideo>` with `startFrom`/`endAt` per shot.

### 9.3 Audio implementation
- VO segments are individual WAVs; each is placed at its cue frame with `<Audio startFrom>` so the
  spoken phrase lands on the intended shot. Cue frames are derived from the measured duration of each
  generated segment (scripted, then written into `cues.ts`).
- Music is a single generated WAV; volume is an `interpolate` envelope over narration windows (ducking).
- SFX are separate short WAVs triggered per cue; SFX frames align with the animating element's hit
  frame (e.g. rule draw completion), not with the cut.

### 9.4 Fonts
Loaded with `@remotion/google-fonts`-free approach: `@fontsource` packages import WOFF2 locally,
declared in `styles/fonts.css` and referenced by family name in `theme.ts`. `delayRender` is not needed
because fonts are bundled and load before paint; a `continueRender` guard is added on the root anyway.

### 9.5 Rendering settings
- Composition: 1920×1080, 30 fps, 6720 frames, H.264 (`--codec=h264`), `--crf=16`,
  `--pixel-format=yuv420p`, `--audio-codec=aac --audio-bitrate=320k`, `--concurrency` tuned to CPU,
  `--gl=swiftshader` (software GL in this headless environment).
- Source intermediate: H.264 High, CRF 16, GOP 30, `+faststart`, no audio, so seeking is exact.
- Final master: MP4 (H.264 High, yuv420p, AAC 320 kb/s), then loudness-normalised to -14 LUFS
  with a true-peak limiter if the render's integrated loudness lands outside ±1 LU.

### 9.6 Export
`final-video.mp4` at the repository root, plus a poster frame for documentation.

---

## 10. Final Quality Checklist

**Visual**
- [ ] 1920×1080, 30 fps, exactly 6720 frames, no black frames except the intentional 12-frame cold-open fade.
- [ ] Every graphic sits inside safe margins; no text is clipped or overlapped.
- [ ] All factual on-screen text matches the footage (commands, host, port, labels, indices).
- [ ] Footage legible: no screen text smaller than 22 px effective size after crops.
- [ ] Typography consistent (3 families, defined scale); amber/cyan usage follows the palette rule.
- [ ] No transition longer than 12 frames; no animation continues past its scene.

**Audio**
- [ ] Narration present in all 10 segments, intelligible, no clipping, no dropouts.
- [ ] Voice/visual sync: each spoken claim lands within ±0.4 s of its evidence.
- [ ] Music ducks under every narration window; no music mask on consonants.
- [ ] SFX hit the element they accent (±2 frames); no SFX over a spoken punchline.
- [ ] Integrated loudness -14 ±1 LUFS; true peak ≤ -1 dBTP; no unintended silence > 0.6 s.

**Story**
- [ ] Cold open poses a question in ≤10 s.
- [ ] The three-option reasoning and the semicolon mechanism are understandable without prior CTF knowledge.
- [ ] Payoff (flag) is set up, delivered, verified, and closed by "Correct flag!".
- [ ] End card resolves the film instead of stopping it.

**Technical**
- [ ] `final-video.mp4` is a valid MP4, streams: H.264 + AAC.
- [ ] The original `.webm` source is untouched (checksum verified).
- [ ] `npx remotion render` reproduces the deliverable from a clean checkout (documented in README).
- [ ] `assets/ASSET_MANIFEST.md` covers every non-code asset with source and license.

---

## 11. Production Revision (as built)

The plan above was written before the audio and render were measured. The following deviations were made deliberately and are reflected in the code:

- **Duration:** the film is **160 s**, not 224 s. The narration measures 131 s (`VO` in `src/utils/timing.ts`), and the edit was tightened to match it rather than stretching the narration. This follows the brief's rule not to speed up or pad the voiceover.
- **Source mapping:** shot windows are defined in `SHOTS` (timeline seconds → source in-points). They were checked against a 1 fps contact sheet of the full footage and against the verified beat list in §2.2. Sub-beat positions are approximate to ±5 s.
- **Flag callout:** the bracket box is anchored to the flag line on screen (`FLAG_CALLOUT`), limited to 4.5 s because the terminal output scrolls.
- **Schematic:** the line-index diagram runs over the dimmed footage during the narration of the mechanism (86–105 s). It is an illustration of the observed mechanism, not a recording of it.
- **Transitions:** two mask wipes (105 s, 137 s) and one fade from black. Hard cuts everywhere else.
- **Music:** the bed is one synthesised track with a frame-accurate ducking envelope (`src/utils/duck.ts`), not a sidechain compressor.
- **Rendering:** Remotion with a headless Chromium binary from the npm registry (`@sparticuz/chromium`), because Chrome's CDN was not reachable from the sandbox. See `README.md`.
