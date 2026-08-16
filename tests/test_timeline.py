from __future__ import annotations

from pathlib import Path

from watchlisten.core.timeline import (
    format_timeline,
    merge_timeline,
    split_timeline_by_duration,
    timeline_plain_text,
)
from watchlisten.models import Chapter, FrameDescription, TranscriptSegment


def _frame(ts: float, desc: str, tmp_path: Path) -> FrameDescription:
    path = tmp_path / f"{int(ts * 1000)}.jpg"
    path.write_text("x")
    return FrameDescription(timestamp=ts, path=path, description=desc)


def test_merge_attaches_frame_to_overlapping_speech(tmp_path: Path):
    transcript = [
        TranscriptSegment(start=0, end=5, text="hello there"),
        TranscriptSegment(start=10, end=15, text="later on"),
    ]
    frames = [_frame(2.0, "a whiteboard", tmp_path), _frame(12.5, "a diagram", tmp_path)]
    entries = merge_timeline(transcript, frames)
    assert len(entries) == 2
    assert entries[0].audio == "hello there"
    assert entries[0].visuals[0].description == "a whiteboard"
    assert entries[1].visuals[0].description == "a diagram"


def test_orphan_frame_becomes_visual_only_entry(tmp_path: Path):
    transcript = [TranscriptSegment(start=0, end=2, text="hi")]
    frames = [_frame(40.0, "silent slide", tmp_path)]
    entries = merge_timeline(transcript, frames, visual_attach_window=4.0)
    assert len(entries) == 2
    assert entries[1].audio == ""
    assert entries[1].visuals[0].description == "silent slide"


def test_chapters_label_entries(tmp_path: Path):
    transcript = [
        TranscriptSegment(start=1, end=3, text="intro talk"),
        TranscriptSegment(start=20, end=22, text="deep dive"),
    ]
    chapters = [
        Chapter(title="Intro", start=0, end=10),
        Chapter(title="Deep", start=10, end=30),
    ]
    entries = merge_timeline(transcript, [], chapters)
    assert entries[0].chapter == "Intro"
    assert entries[1].chapter == "Deep"


def test_format_timeline_includes_visual_and_audio(tmp_path: Path):
    transcript = [TranscriptSegment(start=5, end=8, text="look at this API flow")]
    frames = [_frame(6.0, "diagram labelled API Flow", tmp_path,)]
    frames[0].ocr_text = "API Flow"
    text = format_timeline(merge_timeline(transcript, frames))
    assert "0:05–0:08" in text
    assert "Visual:" in text
    assert "API Flow" in text
    assert "Audio:" in text
    assert "look at this API flow" in text


def test_split_prefers_chapter_boundaries(tmp_path: Path):
    transcript = [
        TranscriptSegment(start=0, end=2, text="a"),
        TranscriptSegment(start=3, end=5, text="b"),
        TranscriptSegment(start=20, end=22, text="c"),
    ]
    chapters = [
        Chapter(title="One", start=0, end=10),
        Chapter(title="Two", start=10, end=30),
    ]
    entries = merge_timeline(transcript, [], chapters)
    chunks = split_timeline_by_duration(entries, chunk_seconds=1000, chapters=chapters)
    assert len(chunks) == 2
    assert chunks[0][0].chapter == "One"
    assert chunks[1][0].chapter == "Two"


def test_split_by_seconds_when_no_chapters():
    transcript = [
        TranscriptSegment(start=float(i * 10), end=float(i * 10 + 2), text=f"s{i}")
        for i in range(6)
    ]
    entries = merge_timeline(transcript, [])
    chunks = split_timeline_by_duration(entries, chunk_seconds=25)
    assert len(chunks) >= 2
    assert sum(len(c) for c in chunks) == 6


def test_timeline_plain_text():
    entries = merge_timeline(
        [
            TranscriptSegment(start=0, end=1, text="alpha"),
            TranscriptSegment(start=2, end=3, text="beta"),
        ],
        [],
    )
    assert timeline_plain_text(entries) == "alpha beta"
