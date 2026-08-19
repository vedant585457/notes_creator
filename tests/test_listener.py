from __future__ import annotations

from pathlib import Path

import pytest

from watchlisten.config import Config
from watchlisten.core.listener import Listener, WhisperUnavailable
from watchlisten.models import MediaBundle
from watchlisten.utils import WatchListenError


def test_missing_audio_is_unavailable(tmp_path: Path):
    media = MediaBundle(workdir=tmp_path, audio_path=None)
    with pytest.raises(WhisperUnavailable, match="No extracted audio"):
        Listener(Config()).from_whisper(media.audio_path)


def test_crash_does_not_say_install_whisper(tmp_path: Path, monkeypatch):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"x")
    media = MediaBundle(workdir=tmp_path, audio_path=wav)
    listener = Listener(Config())

    def boom(*_a, **_k):
        raise RuntimeError("bad value(s) in fds to keep")

    monkeypatch.setattr(listener, "from_whisper", boom)
    with pytest.raises(WatchListenError, match="crashed") as exc:
        listener.transcribe(media)
    assert "pip install faster-whisper" not in str(exc.value)


def test_whisper_worker_usage_exit():
    from watchlisten.core.whisper_worker import main

    assert main([]) == 2
