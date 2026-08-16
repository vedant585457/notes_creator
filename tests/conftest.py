from __future__ import annotations

from pathlib import Path

import pytest

from watchlisten.config import Config
from watchlisten.models import (
    Chapter,
    FrameDescription,
    TranscriptSegment,
    VideoMetadata,
)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.export.output_dir = str(tmp_path / "notes")
    cfg.cache_dir = str(tmp_path / "cache")
    return cfg


@pytest.fixture
def metadata() -> VideoMetadata:
    return VideoMetadata(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_id="dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        duration=213.0,
        description="Official video",
        uploader="Rick Astley",
        channel="Rick Astley",
        chapters=[
            Chapter(title="Intro", start=0.0, end=30.0),
            Chapter(title="Chorus", start=30.0, end=213.0),
        ],
        has_captions=True,
        caption_langs=["en"],
    )


@pytest.fixture
def transcript() -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start=0.0, end=4.0, text="We're no strangers to love"),
        TranscriptSegment(start=4.5, end=9.0, text="You know the rules and so do I"),
        TranscriptSegment(start=40.0, end=45.0, text="Never gonna give you up"),
    ]


@pytest.fixture
def frames(tmp_path: Path) -> list[FrameDescription]:
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_bytes(b"fake")
    b.write_bytes(b"fake")
    return [
        FrameDescription(timestamp=1.2, path=a, description="Title card: Rick Astley", ocr_text="RICK ASTLEY"),
        FrameDescription(timestamp=42.0, path=b, description="Singer dancing in a studio"),
    ]
