"""Textual screens: home, progress, preview, settings, help."""

from __future__ import annotations

from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    Log,
    Markdown,
    ProgressBar,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from watchlisten.config import Config, default_config_path
from watchlisten.core.timeline import format_timeline
from watchlisten.models import DepStatus, ExportFormat, PipelineResult, Stage, StageStatus
from watchlisten.pipeline import Pipeline, PipelineCancelled, PipelineHooks
from watchlisten.ui.widgets import BrandBar, DepBadges, MetaBox, StageList
from watchlisten.utils import (
    URLValidationError,
    WatchListenError,
    extract_video_id,
    format_timestamp,
    is_youtube_url,
    probe_dependencies,
)

WHISPER_CHOICES = [
    ("tiny — fastest", "tiny"),
    ("base — recommended", "base"),
    ("small", "small"),
    ("medium", "medium"),
    ("large-v3 — most accurate", "large-v3"),
]


class HomeScreen(Screen[None]):
    BINDINGS = [
        Binding("s", "open_settings", "Settings"),
        Binding("question_mark", "open_help", "Help"),
        Binding("ctrl+n", "reset", "New"),
    ]

    def compose(self) -> ComposeResult:
        yield BrandBar()
        with VerticalScroll(id="home-body"):
            with Vertical(id="home-card"):
                yield Label("Paste a YouTube URL", id="url-label")
                yield Input(
                    placeholder="https://www.youtube.com/watch?v=…",
                    id="url-input",
                )
                yield Static("Waiting for a link.", id="url-hint")
                yield MetaBox(id="meta-box")
                with Horizontal(id="options-row"):
                    with Vertical(id="formats-col"):
                        yield Label("Export", classes="group-title")
                        yield Checkbox("Markdown", value=True, id="fmt-md")
                        yield Checkbox("HTML", value=True, id="fmt-html")
                        yield Checkbox("PDF", value=False, id="fmt-pdf")
                    with Vertical(id="models-col"):
                        yield Label("Models", classes="group-title")
                        yield Select(
                            [("llama3.2-vision", "llama3.2-vision"), ("llava", "llava")],
                            prompt="Vision model",
                            id="sel-vision",
                        )
                        yield Select(
                            [("llama3.1", "llama3.1"), ("qwen2.5", "qwen2.5")],
                            prompt="Text model",
                            id="sel-text",
                        )
                        yield Select(WHISPER_CHOICES, value="base", id="sel-whisper")
                with Horizontal(id="go-row"):
                    yield Button("▶   Watch · Listen · Note", id="go-btn", disabled=True)
                yield DepBadges(id="dep-row")
        yield Footer()

    def on_mount(self) -> None:
        self._deps: DepStatus | None = None
        self._hydrate_selects()
        url_input = self.query_one("#url-input", Input)
        initial = getattr(self.app, "initial_url", "") or ""
        if initial:
            url_input.value = initial
        url_input.focus()
        self._probe()

    def _hydrate_selects(self) -> None:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        vision_opts = _unique_options(
            [cfg.models.vision, "llama3.2-vision", "llava", "qwen2.5vl", "moondream"]
        )
        text_opts = _unique_options(
            [cfg.models.text, "llama3.1", "qwen2.5", "mistral-nemo", "llama3.2", "gemma2"]
        )
        vision = self.query_one("#sel-vision", Select)
        text = self.query_one("#sel-text", Select)
        whisper = self.query_one("#sel-whisper", Select)
        vision.set_options(vision_opts)
        text.set_options(text_opts)
        try:
            vision.value = cfg.models.vision
        except Exception:
            pass
        try:
            text.value = cfg.models.text
        except Exception:
            pass
        try:
            whisper.value = cfg.models.whisper
        except Exception:
            whisper.value = "base"
        self.query_one("#fmt-md", Checkbox).value = ExportFormat.MARKDOWN in cfg.export_formats
        self.query_one("#fmt-html", Checkbox).value = ExportFormat.HTML in cfg.export_formats
        self.query_one("#fmt-pdf", Checkbox).value = ExportFormat.PDF in cfg.export_formats

    @work(thread=True, exclusive=True, group="probe")
    def _probe(self) -> None:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        deps = probe_dependencies(cfg.resolved_ollama_host())
        self.app.call_from_thread(self._apply_deps, deps)

    def _apply_deps(self, deps: DepStatus) -> None:
        self._deps = deps
        self.query_one(DepBadges).show(deps)
        if deps.all_models:
            vision = self.query_one("#sel-vision", Select)
            text = self.query_one("#sel-text", Select)
            cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
            vision_names = deps.vision_models or deps.all_models
            text_names = deps.text_models or deps.all_models
            vision.set_options(_unique_options([cfg.models.vision, *vision_names]))
            text.set_options(_unique_options([cfg.models.text, *text_names]))
        if not deps.ollama_reachable:
            self.notify("Ollama is not reachable — start `ollama serve`.", severity="warning")
        if not deps.ffmpeg:
            self.notify("ffmpeg is missing — install it before running.", severity="warning")

    @on(Input.Changed, "#url-input")
    def _on_url_changed(self, event: Input.Changed) -> None:
        raw = event.value.strip()
        hint = self.query_one("#url-hint", Static)
        go = self.query_one("#go-btn", Button)
        meta = self.query_one(MetaBox)
        if not raw:
            hint.update("Waiting for a link.")
            hint.set_classes("")
            go.disabled = True
            meta.hide_meta()
            return
        if is_youtube_url(raw):
            vid = extract_video_id(raw)
            hint.update(f"Looks good — video id {vid}. Press Enter to fetch title.")
            hint.set_classes("ok")
            go.disabled = False
        else:
            hint.update("That does not look like a YouTube URL.")
            hint.set_classes("bad")
            go.disabled = True
            meta.hide_meta()

    @on(Input.Submitted, "#url-input")
    def _on_url_submit(self, event: Input.Submitted) -> None:
        if is_youtube_url(event.value):
            self._fetch_meta(event.value.strip())

    @work(thread=True, exclusive=True, group="meta")
    def _fetch_meta(self, url: str) -> None:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        try:
            meta = Pipeline(cfg).fetch_metadata(url)
        except Exception as exc:
            self.app.call_from_thread(self.notify, f"Metadata failed: {exc}", severity="error")
            return
        self.app.call_from_thread(
            self.query_one(MetaBox).show_meta,
            meta.title,
            meta.channel or meta.uploader,
            meta.duration,
            len(meta.chapters),
            meta.has_captions,
        )

    @on(Button.Pressed, "#go-btn")
    def _go(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        if not is_youtube_url(url):
            self.notify("Paste a valid YouTube URL first.", severity="error")
            return
        self._apply_form_to_config()
        formats = self._selected_formats()
        self.app.push_screen(ProgressScreen(url, formats))  # type: ignore[arg-type]

    def _selected_formats(self) -> list[ExportFormat]:
        picked: list[ExportFormat] = []
        if self.query_one("#fmt-md", Checkbox).value:
            picked.append(ExportFormat.MARKDOWN)
        if self.query_one("#fmt-html", Checkbox).value:
            picked.append(ExportFormat.HTML)
        if self.query_one("#fmt-pdf", Checkbox).value:
            picked.append(ExportFormat.PDF)
        return picked or [ExportFormat.MARKDOWN]

    def _apply_form_to_config(self) -> None:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        vision = self.query_one("#sel-vision", Select).value
        text = self.query_one("#sel-text", Select).value
        whisper = self.query_one("#sel-whisper", Select).value
        if isinstance(vision, str) and vision:
            cfg.models.vision = vision
        if isinstance(text, str) and text:
            cfg.models.text = text
        if isinstance(whisper, str) and whisper:
            cfg.models.whisper = whisper
        cfg.export.formats = [f.value for f in self._selected_formats()]

    def action_open_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_open_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_reset(self) -> None:
        self.query_one("#url-input", Input).value = ""
        self.query_one(MetaBox).hide_meta()
        self.query_one("#url-input", Input).focus()


class ProgressScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, url: str, formats: list[ExportFormat]) -> None:
        super().__init__()
        self.url = url
        self.formats = formats
        self._cancel = False
        self._running = False

    def compose(self) -> ComposeResult:
        yield BrandBar()
        with Horizontal(id="progress-split"):
            with Vertical(id="stage-panel"):
                yield Label("PIPELINE", id="stage-heading")
                yield StageList()
            with Vertical(id="live-panel"):
                yield Static("Starting…", id="now-playing")
                yield ProgressBar(total=100, show_eta=False, id="bar")
                yield Log(id="log", highlight=True)
        with Horizontal(id="progress-actions"):
            yield Button("Cancel", id="cancel-btn")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ProgressBar).update(progress=0)
        self._run()

    def action_cancel(self) -> None:
        self._request_cancel()

    @on(Button.Pressed, "#cancel-btn")
    def _cancel_clicked(self) -> None:
        self._request_cancel()

    def _request_cancel(self) -> None:
        if not self._running:
            self.app.pop_screen()
            return
        self._cancel = True
        self.query_one("#now-playing", Static).update("Cancelling after this step…")
        self.query_one(Log).write_line("Cancel requested.")

    @work(thread=True, exclusive=True, group="pipeline")
    def _run(self) -> None:
        self._running = True
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        hooks = PipelineHooks(
            on_log=lambda m: self.app.call_from_thread(self._log, m),
            on_progress=lambda stage, cur, tot, msg: self.app.call_from_thread(
                self._progress, stage, cur, tot, msg
            ),
            on_stage=lambda stage, status, detail: self.app.call_from_thread(
                self._stage, stage, status, detail
            ),
            is_cancelled=lambda: self._cancel,
        )
        try:
            result = Pipeline(cfg, hooks).run(self.url, formats=self.formats)
        except PipelineCancelled:
            self.app.call_from_thread(self._aborted)
            return
        except Exception as exc:
            self.app.call_from_thread(self._failed, exc)
            return
        finally:
            self._running = False
        self.app.call_from_thread(self._finished, result)

    def _log(self, message: str) -> None:
        self.query_one(Log).write_line(message)

    def _progress(self, stage: str, current: int, total: int, message: str) -> None:
        bar = self.query_one(ProgressBar)
        if total > 0:
            bar.update(total=total, progress=min(current, total))
        now = self.query_one("#now-playing", Static)
        now.update(f"{stage}: {message}" if message else stage)

    def _stage(self, stage: Stage, status: StageStatus, detail: str) -> None:
        self.query_one(StageList).set_stage(stage, status, detail)
        if status is StageStatus.RUNNING:
            self.query_one("#now-playing", Static).update(f"{stage.label}…")
            self.query_one(ProgressBar).update(progress=0, total=100)

    def _finished(self, result: PipelineResult) -> None:
        self.app.watch_result = result  # type: ignore[attr-defined]
        paths = ", ".join(p.name for p in result.exports.values())
        self.notify(f"Notes ready: {paths}", severity="information")
        self.app.push_screen(PreviewScreen(result))

    def _failed(self, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        self.query_one("#now-playing", Static).update(f"Failed: {message}")
        self.query_one(Log).write_line(f"ERROR: {message}")
        self.notify(message, severity="error", timeout=8)
        if isinstance(exc, (WatchListenError, URLValidationError)):
            return
        self.query_one(Log).write_line("See the log above; fix the issue and retry from home.")

    def _aborted(self) -> None:
        self.notify("Pipeline cancelled.", severity="warning")
        self.app.pop_screen()


class PreviewScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("ctrl+n", "fresh", "New video"),
    ]

    def __init__(self, result: PipelineResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        yield BrandBar()
        with Vertical(id="preview-head"):
            yield Label(self.result.metadata.title, id="preview-title")
            paths = "   ·   ".join(str(p) for p in self.result.exports.values())
            yield Static(paths or "No files written.", id="preview-paths")
        with TabbedContent():
            with TabPane("Notes", id="tab-notes"):
                yield Markdown(self.result.notes.markdown or "_Empty notes._", classes="md-pane")
            with TabPane("Timeline", id="tab-timeline"):
                yield Markdown(
                    "```\n" + format_timeline(self.result.timeline) + "\n```",
                    classes="md-pane",
                )
            with TabPane("Transcript", id="tab-transcript"):
                yield Markdown(self._transcript_md(), classes="md-pane")
            with TabPane("Visuals", id="tab-visuals"):
                yield Markdown(self._visuals_md(), classes="md-pane")
        with Horizontal(id="preview-actions"):
            yield Button("New video", id="btn-new", classes="secondary")
            yield Button("Open folder", id="btn-folder", classes="secondary")
        yield Footer()

    def _transcript_md(self) -> str:
        if not self.result.transcript:
            return "_No transcript._"
        lines = [
            f"- `{format_timestamp(s.start)}–{format_timestamp(s.end)}` {s.text}"
            for s in self.result.transcript
        ]
        return "\n".join(lines)

    def _visuals_md(self) -> str:
        if not self.result.frames:
            return "_No frames analysed._"
        chunks: list[str] = []
        for frame in self.result.frames:
            flag = "★" if frame.noteworthy else "·"
            desc = frame.description or "_undescribed_"
            ocr = f"\n\nOCR: `{frame.ocr_text}`" if frame.ocr_text else ""
            chunks.append(f"### {flag} {format_timestamp(frame.timestamp)}\n\n{desc}{ocr}")
        return "\n\n".join(chunks)

    @on(Button.Pressed, "#btn-new")
    def _new(self) -> None:
        self.action_fresh()

    @on(Button.Pressed, "#btn-folder")
    def _folder(self) -> None:
        dest = next(iter(self.result.exports.values()), None)
        folder = dest.parent if dest else Path.cwd()
        self.notify(str(folder))
        try:
            import os
            import subprocess
            import sys

            if sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            elif os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            self.notify(f"Could not open folder: {exc}", severity="warning")

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_fresh(self) -> None:
        # Pop preview + progress to land back on home
        self.app.pop_screen()
        if self.app.screen_stack and isinstance(self.app.screen, ProgressScreen):
            self.app.pop_screen()


class SettingsScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        with Vertical(id="modal-card"):
            yield Label("Settings", id="modal-title")
            with Horizontal(id="settings-grid"):
                with Vertical():
                    yield Label("Output directory", classes="label-muted")
                    yield Input(cfg.export.output_dir, id="set-output", classes="setting")
                    yield Label("Max frames to watch", classes="label-muted")
                    yield Input(str(cfg.watcher.max_frames), id="set-frames", classes="setting")
                    yield Label("Chunk size (minutes)", classes="label-muted")
                    yield Input(str(cfg.notes.chunk_minutes), id="set-chunk", classes="setting")
                    yield Label("Notes language (or auto)", classes="label-muted")
                    yield Input(cfg.notes.language, id="set-lang", classes="setting")
                with Vertical():
                    yield Label("Ollama host", classes="label-muted")
                    yield Input(cfg.resolved_ollama_host(), id="set-host", classes="setting")
                    yield Checkbox("Prefer YouTube captions over Whisper", value=cfg.whisper.prefer_captions, id="set-caps")
                    yield Checkbox("Enable OCR on frames", value=cfg.watcher.enable_ocr, id="set-ocr")
                    yield Checkbox("Agentic watch/listen tools", value=cfg.notes.agentic, id="set-agentic")
                    yield Checkbox("Keep downloaded media", value=cfg.keep_media, id="set-keep")
                    yield Checkbox("Embed keyframes in HTML/PDF", value=cfg.export.embed_frames, id="set-embed")
            with Horizontal():
                yield Button("Save", id="set-save")
                yield Button("Cancel", id="set-cancel", classes="secondary")

    @on(Button.Pressed, "#set-cancel")
    def _cancel(self) -> None:
        self.action_close()

    @on(Button.Pressed, "#set-save")
    def _save(self) -> None:
        cfg: Config = self.app.watch_config  # type: ignore[attr-defined]
        cfg.export.output_dir = self.query_one("#set-output", Input).value.strip() or "./notes"
        cfg.ollama_host = self.query_one("#set-host", Input).value.strip()
        cfg.whisper.prefer_captions = self.query_one("#set-caps", Checkbox).value
        cfg.watcher.enable_ocr = self.query_one("#set-ocr", Checkbox).value
        cfg.notes.agentic = self.query_one("#set-agentic", Checkbox).value
        cfg.keep_media = self.query_one("#set-keep", Checkbox).value
        cfg.export.embed_frames = self.query_one("#set-embed", Checkbox).value
        cfg.notes.language = self.query_one("#set-lang", Input).value.strip() or "auto"
        try:
            cfg.watcher.max_frames = max(1, int(self.query_one("#set-frames", Input).value))
        except ValueError:
            self.notify("Max frames must be an integer.", severity="error")
            return
        try:
            cfg.notes.chunk_minutes = max(1.0, float(self.query_one("#set-chunk", Input).value))
        except ValueError:
            self.notify("Chunk size must be a number.", severity="error")
            return
        path = cfg.save(default_config_path())
        self.notify(f"Saved {path}")
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        body = """\
WatchListen **watches** frames with an Ollama vision model and **listens**
with Whisper (or YouTube captions), then merges both into one timeline a
text model turns into notes.

**Pipeline**
1. Fetch title, duration, chapters
2. Download video + extract audio (yt-dlp + ffmpeg)
3. Transcribe speech
4. Detect scene-change frames and describe them
5. Merge audio + visuals on a shared clock
6. Map-reduce notes (long videos are chunked)
7. Export Markdown, HTML, PDF

**Keys**  `s` settings   `?` help   `ctrl+n` new   `q` quit

Nothing is sent to a cloud API. Ollama and Whisper run on this machine.
"""
        with Vertical(id="modal-card"):
            yield Label("How WatchListen works", id="modal-title")
            yield Markdown(body, classes="help-body")
            yield Button("Close", id="help-close", classes="secondary")

    @on(Button.Pressed, "#help-close")
    def _close_btn(self) -> None:
        self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)


def _unique_options(names: list[str]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for name in names:
        key = (name or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append((key, key))
    return out or [("llama3.1", "llama3.1")]
