"""Domain models shared across the WatchListen pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Stage(str, Enum):
    """Ordered pipeline stages shown in the TUI / CLI progress view."""

    VALIDATE = "validate"
    METADATA = "metadata"
    DOWNLOAD = "download"
    LISTEN = "listen"
    WATCH = "watch"
    TIMELINE = "timeline"
    NOTES = "notes"
    EXPORT = "export"

    @property
    def label(self) -> str:
        return {
            Stage.VALIDATE: "Validate URL",
            Stage.METADATA: "Fetch metadata",
            Stage.DOWNLOAD: "Download media",
            Stage.LISTEN: "Listen (transcribe)",
            Stage.WATCH: "Watch (vision)",
            Stage.TIMELINE: "Unify timeline",
            Stage.NOTES: "Generate notes",
            Stage.EXPORT: "Export",
        }[self]


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


class ExportFormat(str, Enum):
    MARKDOWN = "md"
    HTML = "html"
    PDF = "pdf"

    @classmethod
    def parse_many(cls, raw: str | list[str] | None) -> list[ExportFormat]:
        if raw is None:
            return [cls.MARKDOWN]
        if isinstance(raw, list):
            parts = raw
        else:
            parts = [p.strip().lower() for p in raw.replace(";", ",").split(",") if p.strip()]
        out: list[ExportFormat] = []
        aliases = {
            "md": cls.MARKDOWN,
            "markdown": cls.MARKDOWN,
            "html": cls.HTML,
            "htm": cls.HTML,
            "pdf": cls.PDF,
        }
        for part in parts:
            key = part.lower().lstrip(".")
            if key not in aliases:
                raise ValueError(f"Unknown export format: {part!r} (use md, html, pdf)")
            fmt = aliases[key]
            if fmt not in out:
                out.append(fmt)
        return out or [cls.MARKDOWN]


@dataclass(slots=True)
class Chapter:
    title: str
    start: float
    end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "start": self.start, "end": self.end}


@dataclass(slots=True)
class VideoMetadata:
    url: str
    video_id: str
    title: str
    duration: float
    description: str = ""
    uploader: str = ""
    channel: str = ""
    upload_date: str = ""
    thumbnail: str = ""
    webpage_url: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    language: str = ""
    has_captions: bool = False
    caption_langs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "video_id": self.video_id,
            "title": self.title,
            "duration": self.duration,
            "description": self.description,
            "uploader": self.uploader,
            "channel": self.channel,
            "upload_date": self.upload_date,
            "thumbnail": self.thumbnail,
            "webpage_url": self.webpage_url,
            "chapters": [c.to_dict() for c in self.chapters],
            "categories": list(self.categories),
            "tags": list(self.tags),
            "language": self.language,
            "has_captions": self.has_captions,
            "caption_langs": list(self.caption_langs),
        }


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    speaker: str | None = None
    source: str = "whisper"  # whisper | captions

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "source": self.source,
        }


@dataclass(slots=True)
class FrameDescription:
    timestamp: float
    path: Path
    description: str = ""
    ocr_text: str = ""
    scene_score: float = 0.0
    noteworthy: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "path": str(self.path),
            "description": self.description,
            "ocr_text": self.ocr_text,
            "scene_score": self.scene_score,
            "noteworthy": self.noteworthy,
        }


@dataclass(slots=True)
class TimelineEntry:
    start: float
    end: float
    audio: str = ""
    visuals: list[FrameDescription] = field(default_factory=list)
    speaker: str | None = None
    chapter: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "audio": self.audio,
            "visuals": [v.to_dict() for v in self.visuals],
            "speaker": self.speaker,
            "chapter": self.chapter,
        }


@dataclass(slots=True)
class NotesDocument:
    markdown: str
    title: str
    metadata: VideoMetadata
    keyframes: list[FrameDescription] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "markdown": self.markdown,
            "title": self.title,
            "metadata": self.metadata.to_dict(),
            "keyframes": [k.to_dict() for k in self.keyframes],
        }


@dataclass(slots=True)
class MediaBundle:
    """On-disk artefacts produced by the downloader."""

    workdir: Path
    video_path: Path | None = None
    audio_path: Path | None = None
    caption_path: Path | None = None
    thumbnail_path: Path | None = None


@dataclass(slots=True)
class PipelineResult:
    metadata: VideoMetadata
    media: MediaBundle
    transcript: list[TranscriptSegment]
    frames: list[FrameDescription]
    timeline: list[TimelineEntry]
    notes: NotesDocument
    exports: dict[ExportFormat, Path] = field(default_factory=dict)
    workdir: Path | None = None


@dataclass(slots=True)
class DepStatus:
    ffmpeg: bool = False
    ollama: bool = False
    ollama_reachable: bool = False
    whisper: bool = False
    tesseract: bool = False
    weasyprint: bool = False
    scenedetect: bool = False
    opencv: bool = False
    vision_models: list[str] = field(default_factory=list)
    text_models: list[str] = field(default_factory=list)
    all_models: list[str] = field(default_factory=list)

    @property
    def ready_to_run(self) -> bool:
        return self.ffmpeg and self.ollama_reachable
