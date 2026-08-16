from __future__ import annotations

from pathlib import Path

from watchlisten.config import Config, ModelsConfig
from watchlisten.models import Chapter, ExportFormat, Stage, VideoMetadata


def test_config_roundtrip(tmp_path: Path):
    cfg = Config()
    cfg.models.vision = "llava"
    cfg.models.text = "qwen2.5"
    cfg.export.formats = ["md", "pdf"]
    cfg.notes.agentic = True
    path = tmp_path / "cfg.toml"
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded.models.vision == "llava"
    assert loaded.models.text == "qwen2.5"
    assert loaded.notes.agentic is True
    assert ExportFormat.PDF in loaded.export_formats


def test_config_from_partial_dict():
    cfg = Config.from_dict({"models": {"text": "phi3"}, "keep_media": True})
    assert cfg.models.text == "phi3"
    assert cfg.models.vision == ModelsConfig().vision
    assert cfg.keep_media is True


def test_unknown_keys_ignored():
    cfg = Config.from_dict({"models": {"nope": 1, "whisper": "small"}})
    assert cfg.models.whisper == "small"


def test_stage_labels_cover_all():
    for stage in Stage:
        assert stage.label


def test_metadata_to_dict():
    meta = VideoMetadata(
        url="u",
        video_id="ididididid1",
        title="T",
        duration=9,
        chapters=[Chapter(title="A", start=0, end=9)],
    )
    blob = meta.to_dict()
    assert blob["title"] == "T"
    assert blob["chapters"][0]["title"] == "A"
