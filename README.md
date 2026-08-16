# WatchListen AI Notes

Local, privacy-first notes from any YouTube video.

Paste a link. WatchListen **watches** the video with an Ollama vision model and **listens** with Whisper (or the video’s own captions), merges both into one chronological script, then asks a local text model to write structured notes. Export Markdown, HTML, or PDF. Nothing is sent to a cloud API.

```
youtube url
    │
    ▼
 yt-dlp  ── video + 16 kHz wav + captions + chapters
    │
    ├──────────────┐
    ▼              ▼
 listen          watch
 (Whisper /      (scene-change frames
  captions)       → Ollama vision
                  → optional OCR)
    │              │
    └──────┬───────┘
           ▼
   unified timeline
   [02:15] (Visual: whiteboard “API Flow”)
           (Audio: “request pehle gateway…”)
           ▼
   Ollama text model  (map-reduce if long)
           ▼
     notes.md → notes.html → notes.pdf
```

Built for a developer sitting next to their own Ollama daemon. The default interface is a **Textual TUI**; a headless CLI is one flag away.

## Why this exists

A normal (non-multimodal) LLM cannot see slides or hear speech. WatchListen turns a video into a **unified timeline** — the same notes you would jot if you actually watched and listened — then lets a local text model write them up. An optional **agentic** mode goes further: the text model can call `listen_to_segment`, `watch_frame_at`, `search_transcript`, and `get_video_metadata` the way a human scrubs a video.

## Requirements

| Layer | What |
| --- | --- |
| Python | 3.11+ |
| System | [`ffmpeg`](https://ffmpeg.org/) (required), [`tesseract`](https://github.com/tesseract-ocr/tesseract) (optional OCR), cairo/pango (optional, PDF) |
| Local models | [Ollama](https://ollama.com/) with a **text** model and a **vision** model |
| GPU | Optional. Whisper falls back to `int8` on CPU; vision is slower but works. |

```bash
# Debian / Ubuntu
sudo apt install ffmpeg tesseract-ocr
# PDF extras (only if you want WeasyPrint)
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0

# Ollama models (pick any you already run)
ollama pull llama3.1
ollama pull llama3.2-vision
```

## Install

```bash
git clone https://github.com/vedant585457/notes_creator.git
cd notes_creator
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"
```

`[all]` pulls faster-whisper, pytesseract, and weasyprint. Skip it if you only want captions + Markdown/HTML:

```bash
pip install -e .
```

## Usage

### Terminal UI (default)

```bash
watchlisten
# or
python main.py
```

1. Paste a YouTube URL (Enter fetches the title).
2. Tick Markdown / HTML / PDF.
3. Pick vision + text + Whisper models.
4. Hit **Watch · Listen · Note**.
5. Preview tabs: Notes, Timeline, Transcript, Visuals.

Keys: `s` settings · `?` help · `ctrl+n` new · `q` quit.

### CLI

```bash
watchlisten "https://www.youtube.com/watch?v=…" -f md,html,pdf -o ./notes

watchlisten URL --skip-vision --captions-only     # fast, audio/captions only
watchlisten URL --agentic                         # model may re-watch / re-listen
watchlisten URL --vision-model llava --text-model qwen2.5 --whisper-model small
watchlisten --check                               # probe ffmpeg / ollama / whisper
```

Omit the URL and you get the TUI. Pass `--cli` to forbid that fallback.

## What the notes look like

The text model is asked for a fixed skeleton so exports stay consistent:

- Title + source metadata
- **TL;DR**
- **Detailed notes** (chapters / timestamps)
- **Key visuals** (slides, diagrams, code, whiteboards)
- **Notable quotes**
- **Glossary**
- **Takeaways**

Canonical form is Markdown. HTML is a styled Jinja template; PDF is that HTML through WeasyPrint, so the three formats stay in sync. Noteworthy keyframes are copied into `assets/` and embedded.

## Pipeline

| Step | Module | Behaviour |
| --- | --- | --- |
| Validate | `utils.py` | Accepts `youtube.com/watch`, `youtu.be`, Shorts, Live, Embed, or a raw 11-char id. |
| Metadata | `core/downloader.py` | Title, duration, chapters, description, caption languages via yt-dlp. |
| Download | `core/downloader.py` | Best ≤1080p + 16 kHz mono WAV. Private / age-gated / region-locked errors are translated, not dumped as stack traces. |
| Listen | `core/listener.py` | `faster-whisper` with VAD. CUDA/`float16` when available, otherwise CPU/`int8`. YouTube captions are a fallback (or a fast path with `--captions-only`). |
| Watch | `core/watcher.py` | PySceneDetect on cuts; interval sampling if there are no cuts. Hard cap on frames (`max_frames`, default 36). Each frame: Ollama vision + optional Tesseract. |
| Timeline | `core/timeline.py` | Frames attach to overlapping speech; silent slides become their own entries. |
| Notes | `core/notes_generator.py` | Single pass for short videos; map-reduce by chapter / `chunk_minutes` for long ones (2h+ will not blow the context window). |
| Tools | `core/tools.py` | Optional agentic review with four Ollama function-calling tools. |
| Export | `core/exporter.py` | `.md` always, then HTML, then PDF. |

Work files live under `$XDG_CACHE_HOME/watchlisten/work/<video_id>/`. Finished notes go to `./notes/<title>_<id>/` (configurable).

## Configuration

First existing file wins:

1. `--config path.toml`
2. `./watchlisten.toml`
3. `~/.config/watchlisten/config.toml`

See [`watchlisten.example.toml`](watchlisten.example.toml). Environment overrides:

```
WATCHLISTEN_VISION_MODEL
WATCHLISTEN_TEXT_MODEL
WATCHLISTEN_WHISPER_MODEL
WATCHLISTEN_OUTPUT_DIR
WATCHLISTEN_OLLAMA_HOST   (or OLLAMA_HOST)
```

The TUI **Settings** screen writes the XDG config file for you.

## Project layout

```
main.py                         thin wrapper
watchlisten/
  __main__.py                   argparse: TUI or CLI
  config.py                     TOML + env
  models.py                     dataclasses (Stage, transcript, frames, notes)
  pipeline.py                   orchestrator + cancel
  utils.py                      URLs, timestamps, dependency probe
  core/
    downloader.py               yt-dlp + ffmpeg + VTT/SRT
    listener.py                 Whisper / captions
    watcher.py                  scenes + vision + OCR
    timeline.py                 merge / format / chunk
    notes_generator.py          Ollama map-reduce + agentic
    tools.py                    listen / watch / search / metadata
    exporter.py                 MD → HTML → PDF
  ui/                           Textual app, screens, cinema-dark theme
  templates/notes.html          print-friendly HTML/PDF
tests/                          no network, no Ollama required
```

## Edge cases that are actually handled

- **Long videos** — timeline is chunked (chapters first, then duration) before the text model sees it.
- **Existing captions** — used as fallback or as the primary listen pass.
- **No GPU** — Whisper `int8` on CPU; fewer frames via `max_frames`.
- **Private / age-restricted / region-locked** — clean `MediaError`, not a yt-dlp traceback.
- **Slow vision** — only scene-change frames, then an even subsample down to `max_frames`.
- **Missing extras** — no Whisper? captions. no Tesseract? skip OCR. no WeasyPrint? Markdown/HTML still work.

## Development

```bash
pip install -e ".[dev]"
pytest
watchlisten --help
watchlisten --check
```

Tests cover URL parsing, timestamps, timeline merge/chunking, caption rolling-window cleanup, tool dispatch, config round-trip, and MD/HTML export. They do **not** hit YouTube or Ollama.

## Privacy

Downloads, transcripts, frames, and notes never leave the machine this process runs on. The only network calls are yt-dlp talking to YouTube and the `ollama` client talking to your local daemon (`127.0.0.1:11434` by default).

## License

MIT. See [LICENSE](LICENSE).
