from __future__ import annotations

from pathlib import Path

import pytest

from watchlisten.config import Config
from watchlisten.core.downloader import Downloader
from watchlisten.core.yt_resilience import (
    FORMAT_AUDIO,
    FORMAT_VIDEO_720,
    backoff_seconds,
    build_attempt_plan,
    is_rate_limited,
    is_recoverable,
    parse_cookies_from_browser,
    parse_rate,
)
from watchlisten.utils import MediaError


@pytest.mark.parametrize(
    "message",
    [
        "ERROR: HTTP Error 429: Too Many Requests",
        "Sign in to confirm you’re not a bot",
        "This content isn't available, try again later",
        "has been rate-limited by YouTube",
    ],
)
def test_detects_rate_limit(message):
    assert is_rate_limited(message)
    assert is_recoverable(message)


def test_private_video_is_not_recoverable():
    assert is_recoverable("This video is private") is False
    assert is_rate_limited("This video is private") is False


def test_403_is_recoverable_but_not_rate_limit():
    assert is_recoverable("HTTP Error 403: Forbidden")
    assert is_rate_limited("HTTP Error 403: Forbidden") is False


def test_backoff_grows_and_caps():
    assert backoff_seconds(0, base=8, cap=60) == 8
    assert backoff_seconds(1, base=8, cap=60) == pytest.approx(12.8)
    assert backoff_seconds(10, base=8, cap=60) == 60


def test_parse_rate():
    assert parse_rate("2.5M") == int(2.5 * 1024 * 1024)
    assert parse_rate("500K") == 500 * 1024
    assert parse_rate(0) is None
    assert parse_rate("nope") is None


def test_parse_cookies_from_browser():
    assert parse_cookies_from_browser("firefox") == ("firefox",)
    assert parse_cookies_from_browser("chrome:Default") == ("chrome", "Default")
    assert parse_cookies_from_browser("auto") is None
    assert parse_cookies_from_browser("") is None


def test_attempt_plan_uses_one_client_at_a_time():
    plan = build_attempt_plan(cookies_configured=False)
    assert plan[0].client == "android_vr"
    assert plan[0].format_spec == FORMAT_VIDEO_720
    assert plan[0].use_cookies is False
    clients_in_first_two = {plan[0].client, plan[1].client}
    assert clients_in_first_two == {"android_vr"}
    assert any(a.format_spec == FORMAT_AUDIO for a in plan)
    assert all(not a.use_cookies for a in plan)


def test_attempt_plan_inserts_cookie_retry_when_configured():
    plan = build_attempt_plan(cookies_configured=True)
    cookie_attempts = [a for a in plan if a.use_cookies]
    assert cookie_attempts
    assert cookie_attempts[0].client == "android_vr"


class _ScriptedYDL:
    """Stand-in for the yt_dlp module. `script` is Exceptions or 'ok'."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.opts_log: list[dict] = []

    def YoutubeDL(self, opts):  # noqa: N802
        return _Session(self, opts)


class _Session:
    def __init__(self, parent: _ScriptedYDL, opts: dict) -> None:
        self.parent = parent
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def download(self, _urls):
        self.parent.opts_log.append(self.opts)
        item = self.parent.script.pop(0)
        if isinstance(item, Exception):
            raise item
        outtmpl = str(self.opts["outtmpl"])
        Path(outtmpl.replace("%(ext)s", "mp4")).write_bytes(b"fake-mp4")

    def extract_info(self, _url, download=False):
        self.parent.opts_log.append(self.opts)
        item = self.parent.script.pop(0) if self.parent.script else {"id": "dQw4w9WgXcQ"}
        if isinstance(item, Exception):
            raise item
        if isinstance(item, dict):
            return item
        return {
            "id": "dQw4w9WgXcQ",
            "title": "Demo",
            "duration": 12,
            "channel": "Lab",
        }


def _downloader(tmp_path: Path, script: list) -> tuple[Downloader, list[float], _ScriptedYDL]:
    sleeps: list[float] = []
    fake = _ScriptedYDL(script)
    cfg = Config()
    cfg.cache_dir = str(tmp_path / "cache")
    cfg.download.sleep_requests = 0
    dl = Downloader(
        cfg,
        sleeper=sleeps.append,
        ydl_factory=lambda: fake,
    )
    return dl, sleeps, fake


def test_download_retries_after_429_then_succeeds(tmp_path: Path):
    dl, sleeps, fake = _downloader(
        tmp_path,
        [Exception("HTTP Error 429: Too Many Requests"), "ok"],
    )
    bundle = dl.download("https://youtu.be/dQw4w9WgXcQ", tmp_path / "work")
    assert bundle.video_path is not None
    assert bundle.video_path.exists()
    assert sleeps  # waited before the second strategy
    assert fake.opts_log[0]["extractor_args"]["youtube"]["player_client"] == ["android_vr"]
    assert fake.opts_log[0]["source_address"] == "0.0.0.0"
    assert fake.opts_log[0]["concurrent_fragment_downloads"] == 1


def test_download_does_not_retry_private_video(tmp_path: Path):
    dl, sleeps, fake = _downloader(tmp_path, [Exception("This video is private")])
    with pytest.raises(MediaError, match="private"):
        dl.download("https://youtu.be/dQw4w9WgXcQ", tmp_path / "work")
    assert sleeps == []
    assert len(fake.opts_log) == 1


def test_download_reuses_cached_file(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    cached = work / "dQw4w9WgXcQ.mp4"
    cached.write_bytes(b"already-here")
    dl, _sleeps, fake = _downloader(tmp_path, [Exception("should not be called")])
    bundle = dl.download("https://youtu.be/dQw4w9WgXcQ", work)
    assert bundle.video_path == cached
    assert fake.opts_log == []


def test_metadata_retries_then_returns(tmp_path: Path):
    dl, sleeps, _fake = _downloader(
        tmp_path,
        [
            Exception("HTTP Error 429: Too Many Requests"),
            {
                "id": "dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "duration": 213,
                "channel": "Rick Astley",
            },
        ],
    )
    meta = dl.fetch_metadata("https://youtu.be/dQw4w9WgXcQ")
    assert meta.title == "Never Gonna Give You Up"
    assert meta.duration == 213
    assert sleeps


def test_download_config_roundtrip(tmp_path: Path):
    cfg = Config()
    cfg.download.cookies_from_browser = "firefox"
    cfg.download.force_ipv4 = True
    path = tmp_path / "cfg.toml"
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded.download.cookies_from_browser == "firefox"
    assert loaded.download.force_ipv4 is True
    assert loaded.download.keep_cache is True
