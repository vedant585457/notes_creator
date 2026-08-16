"""Orchestrate validate → download → listen → watch → timeline → notes → export."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from watchlisten.config import Config
from watchlisten.core.downloader import Downloader
from watchlisten.core.exporter import Exporter
from watchlisten.core.listener import Listener
from watchlisten.core.notes_generator import NotesGenerator
from watchlisten.core.timeline import format_timeline, merge_timeline
from watchlisten.core.tools import TOOL_SCHEMAS, VideoTools
from watchlisten.core.watcher import Watcher
from watchlisten.models import (
    ExportFormat,
    FrameDescription,
    PipelineResult,
    Stage,
    StageStatus,
    VideoMetadata,
)
from watchlisten.utils import (
    CancelledError,
    WatchListenError,
    extract_video_id,
    normalize_youtube_url,
    sanitize_filename,
)

LogHook = Callable[[str], None]
ProgressHook = Callable[[str, int, int, str], None]
StageHook = Callable[[Stage, StageStatus, str], None]
CancelHook = Callable[[], bool]


@dataclass
class PipelineHooks:
    on_log: LogHook = field(default_factory=lambda: (lambda _m: None))
    on_progress: ProgressHook = field(default_factory=lambda: (lambda *_a: None))
    on_stage: StageHook = field(default_factory=lambda: (lambda *_a: None))
    is_cancelled: CancelHook = field(default_factory=lambda: (lambda: False))


class Pipeline:
    def __init__(self, config: Config, hooks: PipelineHooks | None = None) -> None:
        self.config = config
        self.hooks = hooks or PipelineHooks()

    def run(
        self,
        url: str,
        *,
        formats: list[ExportFormat] | None = None,
        skip_vision: bool = False,
        captions_only: bool = False,
        output_dir: Path | None = None,
    ) -> PipelineResult:
        formats = formats or self.config.export_formats
        self._check_cancel()

        self._stage(Stage.VALIDATE, StageStatus.RUNNING)
        url = normalize_youtube_url(url)
        video_id = extract_video_id(url)
        self.hooks.on_log(f"Accepted YouTube id {video_id}")
        self._stage(Stage.VALIDATE, StageStatus.DONE, video_id)

        downloader = Downloader(
            self.config,
            on_progress=self.hooks.on_progress,
            on_log=self.hooks.on_log,
            is_cancelled=self.hooks.is_cancelled,
        )
        self._stage(Stage.METADATA, StageStatus.RUNNING)
        metadata = downloader.fetch_metadata(url)
        self.hooks.on_log(
            f"{metadata.title} — {int(metadata.duration)}s — {metadata.channel or metadata.uploader}"
        )
        self._stage(Stage.METADATA, StageStatus.DONE, metadata.title)

        workdir = self.config.cache_path / "work" / video_id
        workdir.mkdir(parents=True, exist_ok=True)

        self._check_cancel()
        self._stage(Stage.DOWNLOAD, StageStatus.RUNNING)
        media = downloader.download(url, workdir, metadata)
        self._stage(Stage.DOWNLOAD, StageStatus.DONE, media.video_path.name if media.video_path else "")

        self._check_cancel()
        self._stage(Stage.LISTEN, StageStatus.RUNNING)
        listener = Listener(
            self.config, on_progress=self.hooks.on_progress, on_log=self.hooks.on_log
        )
        transcript = listener.transcribe(
            media, captions_only=captions_only, duration=metadata.duration
        )
        self._stage(Stage.LISTEN, StageStatus.DONE, f"{len(transcript)} segments")

        frames: list[FrameDescription] = []
        if skip_vision:
            self._stage(Stage.WATCH, StageStatus.SKIPPED, "skipped by user")
        elif media.video_path is None:
            self._stage(Stage.WATCH, StageStatus.SKIPPED, "no video file")
        else:
            self._check_cancel()
            self._stage(Stage.WATCH, StageStatus.RUNNING)
            watcher = Watcher(
                self.config,
                on_progress=self.hooks.on_progress,
                on_log=self.hooks.on_log,
                is_cancelled=self.hooks.is_cancelled,
            )
            frames = watcher.analyze(media.video_path, workdir, metadata.duration)
            self._stage(Stage.WATCH, StageStatus.DONE, f"{len(frames)} frames")

        self._check_cancel()
        self._stage(Stage.TIMELINE, StageStatus.RUNNING)
        timeline = merge_timeline(transcript, frames, metadata.chapters)
        script_path = workdir / "timeline.md"
        script_path.write_text(format_timeline(timeline), encoding="utf-8")
        self.hooks.on_log(f"Unified timeline: {len(timeline)} entries → {script_path.name}")
        self._stage(Stage.TIMELINE, StageStatus.DONE, f"{len(timeline)} entries")

        self._check_cancel()
        self._stage(Stage.NOTES, StageStatus.RUNNING)
        generator = NotesGenerator(
            self.config, on_progress=self.hooks.on_progress, on_log=self.hooks.on_log
        )
        if self.config.notes.agentic:
            tools = VideoTools(
                metadata,
                transcript,
                frames,
                watch_fallback=_make_watch_fallback(self.config, media.video_path, workdir),
            )
            notes = generator.generate_with_tools(
                metadata, timeline, tools.dispatch, TOOL_SCHEMAS
            )
        else:
            notes = generator.generate(metadata, timeline)
        notes.keyframes = [f for f in frames if f.noteworthy] or frames
        self._stage(Stage.NOTES, StageStatus.DONE)

        self._check_cancel()
        self._stage(Stage.EXPORT, StageStatus.RUNNING)
        dest = _resolve_output_dir(output_dir or self.config.output_path, metadata)
        exporter = Exporter(self.config, on_log=self.hooks.on_log)
        exports = exporter.export(notes, dest, formats, keyframes=notes.keyframes)
        # Always persist the raw timeline next to the notes for debugging / reuse
        shutil.copy2(script_path, dest / "timeline.md")
        self._stage(Stage.EXPORT, StageStatus.DONE, str(dest))

        if not self.config.keep_media and not self.config.download.keep_cache:
            for bulky in (media.video_path, media.audio_path):
                if bulky and bulky.exists():
                    try:
                        bulky.unlink()
                    except OSError:
                        pass

        return PipelineResult(
            metadata=metadata,
            media=media,
            transcript=transcript,
            frames=frames,
            timeline=timeline,
            notes=notes,
            exports=exports,
            workdir=workdir,
        )

    def fetch_metadata(self, url: str) -> VideoMetadata:
        downloader = Downloader(
            self.config,
            on_progress=self.hooks.on_progress,
            on_log=self.hooks.on_log,
            is_cancelled=self.hooks.is_cancelled,
        )
        return downloader.fetch_metadata(url)

    def _stage(self, stage: Stage, status: StageStatus, detail: str = "") -> None:
        self.hooks.on_stage(stage, status, detail)

    def _check_cancel(self) -> None:
        if self.hooks.is_cancelled():
            raise PipelineCancelled("Cancelled by user.")


class PipelineCancelled(WatchListenError):
    pass


def _resolve_output_dir(base: Path, metadata: VideoMetadata) -> Path:
    folder = f"{sanitize_filename(metadata.title)}_{metadata.video_id}"
    dest = Path(base) / folder
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _make_watch_fallback(
    config: Config, video_path: Path | None, workdir: Path
) -> Callable[[float], FrameDescription] | None:
    if video_path is None:
        return None

    def _fallback(ts: float) -> FrameDescription:
        watcher = Watcher(config)
        return watcher.describe_at(video_path, workdir / "frames", ts)

    return _fallback
