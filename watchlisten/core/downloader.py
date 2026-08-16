"""yt-dlp wrapper: metadata, media download, audio extract, caption harvest."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from watchlisten.config import Config
from watchlisten.models import Chapter, MediaBundle, VideoMetadata
from watchlisten.utils import (
    MediaError,
    URLValidationError,
    extract_video_id,
    ffmpeg_available,
    normalize_youtube_url,
    run_cmd,
)

ProgressHook = Callable[[str, int, int, str], None]
LogHook = Callable[[str], None]


class Downloader:
    def __init__(
        self,
        config: Config,
        *,
        on_progress: ProgressHook | None = None,
        on_log: LogHook | None = None,
    ) -> None:
        self.config = config
        self.on_progress = on_progress or (lambda *_args: None)
        self.on_log = on_log or (lambda _msg: None)

    def fetch_metadata(self, url: str) -> VideoMetadata:
        url = normalize_youtube_url(url)
        ydl = _yt_dlp()
        opts = self._base_opts()
        opts.update({"skip_download": True, "quiet": True, "noplaylist": True})
        try:
            with ydl.YoutubeDL(opts) as client:
                info = client.extract_info(url, download=False)
        except Exception as exc:
            raise _translate_ytdlp_error(exc, url) from exc
        if not info:
            raise MediaError(f"yt-dlp returned no metadata for {url}")
        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if not entries:
                raise MediaError("This looks like a playlist, not a single video.")
            info = entries[0]
        return _metadata_from_info(url, info)

    def download(self, url: str, workdir: Path, meta: VideoMetadata | None = None) -> MediaBundle:
        if not ffmpeg_available():
            raise MediaError(
                "ffmpeg is required to download and extract audio. "
                "Install it (e.g. `sudo apt install ffmpeg`) and retry."
            )
        url = normalize_youtube_url(url)
        video_id = meta.video_id if meta else extract_video_id(url)
        workdir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(workdir / f"{video_id}.%(ext)s")

        ydl = _yt_dlp()
        opts = self._base_opts()
        opts.update(
            {
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self._ydl_hook],
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "vtt/srt/best",
                "subtitleslangs": ["en", "en-orig", "hi", "en.*", "hi.*"],
                "writethumbnail": True,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "merge_output_format": "mp4",
            }
        )
        self.on_log(f"Downloading {url} → {workdir}")
        try:
            with ydl.YoutubeDL(opts) as client:
                client.download([url])
        except Exception as exc:
            raise _translate_ytdlp_error(exc, url) from exc

        video_path = _find_first(workdir, [f"{video_id}.mp4", f"{video_id}.mkv", f"{video_id}.webm"])
        if video_path is None:
            # fallback: any video-looking file
            video_path = next(
                (
                    p
                    for p in workdir.iterdir()
                    if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
                ),
                None,
            )
        if video_path is None:
            raise MediaError("Download finished but no video file was found.")

        audio_path = workdir / f"{video_id}.wav"
        self._extract_audio(video_path, audio_path)

        caption_path = _pick_caption(workdir, video_id)
        thumb = _find_first(
            workdir,
            [
                f"{video_id}.jpg",
                f"{video_id}.webp",
                f"{video_id}.png",
                f"{video_id}.jpeg",
            ],
        )
        return MediaBundle(
            workdir=workdir,
            video_path=video_path,
            audio_path=audio_path if audio_path.exists() else None,
            caption_path=caption_path,
            thumbnail_path=thumb,
        )

    def _extract_audio(self, video: Path, dest: Path) -> None:
        self.on_log(f"Extracting 16 kHz mono WAV via ffmpeg → {dest.name}")
        result = run_cmd(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(dest),
            ],
            timeout=600,
        )
        if result.returncode != 0 or not dest.exists():
            tail = (result.stderr or result.stdout or "").strip().splitlines()
            hint = tail[-1] if tail else "unknown ffmpeg error"
            raise MediaError(f"ffmpeg failed to extract audio: {hint}")

    def _ydl_hook(self, event: dict[str, Any]) -> None:
        status = event.get("status")
        if status == "downloading":
            downloaded = int(event.get("downloaded_bytes") or 0)
            total = int(event.get("total_bytes") or event.get("total_bytes_estimate") or 0)
            speed = event.get("_speed_str") or ""
            eta = event.get("_eta_str") or ""
            msg = " ".join(p for p in (speed, f"eta {eta}" if eta else "") if p)
            self.on_progress("download", downloaded, total, msg)
        elif status == "finished":
            filename = event.get("filename") or ""
            self.on_log(f"Download finished: {Path(filename).name}")
            self.on_progress("download", 1, 1, "merging streams")

    def _base_opts(self) -> dict[str, Any]:
        return {
            "nocheckcertificate": False,
            "ignoreerrors": False,
            "overwrites": True,
            "cachedir": str(self.config.cache_path / "yt-dlp"),
        }


def parse_caption_file(path: Path) -> list[tuple[float, float, str]]:
    """Parse a small VTT or SRT file into (start, end, text) triples."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".vtt" or text.lstrip().startswith("WEBVTT"):
        return _parse_vtt(text)
    return _parse_srt(text)


def _parse_vtt(text: str) -> list[tuple[float, float, str]]:
    from watchlisten.utils import parse_timestamp

    cues: list[tuple[float, float, str]] = []
    blocks = _split_cue_blocks(text)
    for block in blocks:
        lines = [ln.strip("\ufeff") for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        timing = next((ln for ln in lines if "-->" in ln), None)
        if not timing:
            continue
        start_s, end_s = _split_arrow(timing)
        try:
            start, end = parse_timestamp(_strip_vtt_settings(start_s)), parse_timestamp(
                _strip_vtt_settings(end_s)
            )
        except ValueError:
            continue
        body_lines = []
        seen_timing = False
        for ln in lines:
            if "-->" in ln:
                seen_timing = True
                continue
            if not seen_timing:
                continue
            cleaned = _strip_tags(ln).strip()
            if cleaned:
                body_lines.append(cleaned)
        body = " ".join(body_lines).strip()
        if body:
            cues.append((start, end, body))
    return _dedupe_caption_cues(cues)


def _parse_srt(text: str) -> list[tuple[float, float, str]]:
    from watchlisten.utils import parse_timestamp

    cues: list[tuple[float, float, str]] = []
    for block in _split_cue_blocks(text):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        timing = next((ln for ln in lines if "-->" in ln), None)
        if not timing:
            continue
        start_s, end_s = _split_arrow(timing)
        try:
            start = parse_timestamp(start_s.replace(",", "."))
            end = parse_timestamp(end_s.replace(",", "."))
        except ValueError:
            continue
        body_lines = []
        seen = False
        for ln in lines:
            if "-->" in ln:
                seen = True
                continue
            if not seen:
                continue
            cleaned = _strip_tags(ln).strip()
            if cleaned:
                body_lines.append(cleaned)
        body = " ".join(body_lines).strip()
        if body:
            cues.append((start, end, body))
    return _dedupe_caption_cues(cues)


def _split_cue_blocks(text: str) -> list[str]:
    # Normalise newlines then split on blank lines
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return [b for b in normalised.split("\n\n") if b.strip() and not b.strip().startswith("NOTE")]


def _split_arrow(timing: str) -> tuple[str, str]:
    left, right = timing.split("-->", 1)
    return left.strip(), right.strip()


def _strip_vtt_settings(token: str) -> str:
    # `00:00:01.000 align:start position:0%`
    return token.split()[0].replace(",", ".")


def _strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text)


def _dedupe_caption_cues(
    cues: list[tuple[float, float, str]],
) -> list[tuple[float, float, str]]:
    """YouTube auto-captions repeat rolling windows; keep new words only."""
    if not cues:
        return []
    out: list[tuple[float, float, str]] = []
    prev = ""
    for start, end, text in cues:
        if text == prev:
            continue
        # If this cue is a strict extension of the previous rolling window, keep the delta
        if prev and text.startswith(prev):
            delta = text[len(prev) :].strip()
            if delta:
                out.append((start, end, delta))
            prev = text
            continue
        out.append((start, end, text))
        prev = text
    return out


def _metadata_from_info(url: str, info: dict[str, Any]) -> VideoMetadata:
    video_id = str(info.get("id") or extract_video_id(url))
    chapters: list[Chapter] = []
    raw_chapters = info.get("chapters") or []
    duration = float(info.get("duration") or 0.0)
    for idx, ch in enumerate(raw_chapters):
        start = float(ch.get("start_time") or 0.0)
        end = ch.get("end_time")
        if end is None and idx + 1 < len(raw_chapters):
            end = raw_chapters[idx + 1].get("start_time")
        if end is None:
            end = duration or None
        chapters.append(
            Chapter(
                title=str(ch.get("title") or f"Chapter {idx + 1}"),
                start=start,
                end=float(end) if end is not None else None,
            )
        )
    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}
    langs = sorted({*subs.keys(), *autos.keys()})
    return VideoMetadata(
        url=url,
        video_id=video_id,
        title=str(info.get("title") or video_id),
        duration=duration,
        description=str(info.get("description") or ""),
        uploader=str(info.get("uploader") or info.get("channel") or ""),
        channel=str(info.get("channel") or info.get("uploader") or ""),
        upload_date=str(info.get("upload_date") or ""),
        thumbnail=str(info.get("thumbnail") or ""),
        webpage_url=str(info.get("webpage_url") or url),
        chapters=chapters,
        categories=list(info.get("categories") or []),
        tags=list(info.get("tags") or [])[:24],
        language=str(info.get("language") or ""),
        has_captions=bool(subs or autos),
        caption_langs=langs,
    )


def _find_first(folder: Path, names: list[str]) -> Path | None:
    for name in names:
        candidate = folder / name
        if candidate.exists():
            return candidate
    return None


def _pick_caption(folder: Path, video_id: str) -> Path | None:
    preferred_suffixes = (".en.vtt", ".en-orig.vtt", ".hi.vtt", ".en.srt", ".vtt", ".srt")
    files = list(folder.iterdir())
    for suffix in preferred_suffixes:
        for path in files:
            if path.name.startswith(video_id) and path.name.endswith(suffix.lstrip(".")):
                return path
            if path.name.startswith(video_id) and path.suffix.lower() in {".vtt", ".srt"}:
                # language-tagged: video.en.vtt
                if suffix in path.name or path.suffix.lower() == suffix:
                    return path
    # last resort
    for path in files:
        if path.suffix.lower() in {".vtt", ".srt"}:
            return path
    return None


def _yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover
        raise MediaError("yt-dlp is not installed. `pip install yt-dlp`.") from exc
    return yt_dlp


def _translate_ytdlp_error(exc: Exception, url: str) -> MediaError:
    message = str(exc)
    lowered = message.lower()
    if "private video" in lowered:
        return MediaError("This video is private. WatchListen cannot access it.")
    if "age-restricted" in lowered or "sign in to confirm your age" in lowered:
        return MediaError(
            "This video is age-restricted. yt-dlp needs cookies from a logged-in browser."
        )
    if "video unavailable" in lowered or "not available" in lowered:
        return MediaError(
            "Video unavailable (removed, region-locked, or not a public YouTube video)."
        )
    if "http error 429" in lowered or "too many requests" in lowered:
        return MediaError("YouTube rate-limited the download. Wait a bit and retry.")
    if isinstance(exc, URLValidationError):
        return MediaError(str(exc))
    return MediaError(f"Download failed for {url}: {message}")


def dump_info_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
