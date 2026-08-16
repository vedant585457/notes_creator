from __future__ import annotations

from pathlib import Path

from watchlisten.config import Config
from watchlisten.core.downloader import parse_caption_file
from watchlisten.core.exporter import Exporter
from watchlisten.core.notes_generator import _strip_fences
from watchlisten.core.watcher import _cap_timestamps, _parse_noteworthy
from watchlisten.models import ExportFormat, FrameDescription, NotesDocument, VideoMetadata


def test_export_markdown_and_html(tmp_path: Path):
    cfg = Config()
    cfg.export.embed_frames = True
    meta = VideoMetadata(
        url="https://www.youtube.com/watch?v=aaaaaaaaaaa",
        video_id="aaaaaaaaaaa",
        title="Hello World Notes",
        duration=30,
        channel="Lab",
    )
    notes = NotesDocument(
        markdown="# Hello World Notes\n\n## TL;DR\nIt works.\n",
        title="Hello World Notes",
        metadata=meta,
    )
    frame_img = tmp_path / "src.jpg"
    frame_img.write_bytes(b"\xff\xd8\xff")  # tiny jpeg-ish
    notes.keyframes = [
        FrameDescription(timestamp=3.0, path=frame_img, description="A slide", noteworthy=True)
    ]
    dest = tmp_path / "out"
    written = Exporter(cfg).export(
        notes, dest, [ExportFormat.MARKDOWN, ExportFormat.HTML], keyframes=notes.keyframes
    )
    assert ExportFormat.MARKDOWN in written
    assert ExportFormat.HTML in written
    md = written[ExportFormat.MARKDOWN].read_text(encoding="utf-8")
    assert md.startswith("# Hello World Notes")
    html = written[ExportFormat.HTML].read_text(encoding="utf-8")
    assert "Hello World Notes" in html
    assert "WatchListen" in html
    assert "assets/" in html
    assert any((dest / "assets").glob("frame_*"))


def test_strip_fences():
    raw = "```markdown\n# Title\n\nHi\n```"
    assert _strip_fences(raw) == "# Title\n\nHi"


def test_parse_noteworthy_yes_and_no():
    desc, flag = _parse_noteworthy("A diagram of queues.\nNOTEWORTHY: yes — architecture")
    assert "diagram" in desc
    assert flag is True
    desc, flag = _parse_noteworthy("Blurry wall.\nNOTEWORTHY: no")
    assert "NOTEWORTHY" not in desc
    assert flag is False


def test_cap_timestamps_even_sample():
    stamps = [float(i) for i in range(0, 100, 2)]
    capped = _cap_timestamps(stamps, 5, 200)
    assert len(capped) == 5
    assert capped[0] == 0
    assert capped[-1] == stamps[-1]


def test_parse_vtt_and_srt(tmp_path: Path):
    vtt = tmp_path / "c.vtt"
    vtt.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:03.000\nHello world\n\n"
        "00:00:03.000 --> 00:00:05.000\nHello world everyone\n",
        encoding="utf-8",
    )
    cues = parse_caption_file(vtt)
    assert cues[0][2] == "Hello world"
    # rolling window: second cue keeps only the new words
    assert any("everyone" in c[2] for c in cues)

    srt = tmp_path / "c.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nFirst line\n\n"
        "2\n00:00:02,000 --> 00:00:03,000\nSecond line\n",
        encoding="utf-8",
    )
    srt_cues = parse_caption_file(srt)
    assert [c[2] for c in srt_cues] == ["First line", "Second line"]
