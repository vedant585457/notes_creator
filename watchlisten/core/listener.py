"""Audio transcription via faster-whisper, with YouTube captions as fallback."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from watchlisten.config import Config
from watchlisten.core.downloader import parse_caption_file
from watchlisten.models import MediaBundle, TranscriptSegment
from watchlisten.utils import WatchListenError

LogHook = Callable[[str], None]
ProgressHook = Callable[[str, int, int, str], None]


class Listener:
    def __init__(
        self,
        config: Config,
        *,
        on_progress: ProgressHook | None = None,
        on_log: LogHook | None = None,
    ) -> None:
        self.config = config
        self.on_progress = on_progress or (lambda *_a: None)
        self.on_log = on_log or (lambda _m: None)

    def transcribe(
        self,
        media: MediaBundle,
        *,
        captions_only: bool = False,
        duration: float | None = None,
    ) -> list[TranscriptSegment]:
        prefer_captions = self.config.whisper.prefer_captions or captions_only
        if prefer_captions and media.caption_path and media.caption_path.exists():
            segs = self.from_captions(media.caption_path)
            if segs:
                self.on_log(f"Using YouTube captions ({len(segs)} cues) from {media.caption_path.name}")
                return segs
            if captions_only:
                raise WatchListenError("Captions-only was requested but no usable caption file was found.")

        if not captions_only:
            try:
                segs = self.from_whisper(media.audio_path, duration=duration)
                if segs:
                    return segs
            except WhisperUnavailable as exc:
                self.on_log(str(exc))
            except Exception as exc:
                self.on_log(f"Whisper failed ({exc}); trying captions fallback.")

        if media.caption_path and media.caption_path.exists():
            segs = self.from_captions(media.caption_path)
            if segs:
                self.on_log(f"Fell back to YouTube captions ({len(segs)} cues).")
                return segs

        raise WatchListenError(
            "Could not transcribe audio. Install faster-whisper "
            "(`pip install faster-whisper`) or use a video that has captions."
        )

    def from_captions(self, path: Path) -> list[TranscriptSegment]:
        cues = parse_caption_file(path)
        return [
            TranscriptSegment(start=s, end=e, text=t, source="captions")
            for s, e, t in cues
            if t.strip()
        ]

    def from_whisper(
        self,
        audio_path: Path | None,
        *,
        duration: float | None = None,
    ) -> list[TranscriptSegment]:
        if audio_path is None or not audio_path.exists():
            raise WhisperUnavailable("No extracted audio file is available for Whisper.")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise WhisperUnavailable(
                "faster-whisper is not installed. `pip install faster-whisper` "
                "or pass --captions-only to use YouTube captions."
            ) from exc

        device, compute = _resolve_device(self.config.whisper.device, self.config.whisper.compute_type)
        model_size = self.config.models.whisper
        self.on_log(f"Loading Whisper model '{model_size}' ({device}/{compute})")
        self.on_progress("listen", 0, 1, f"loading {model_size}")
        model = WhisperModel(model_size, device=device, compute_type=compute)

        language = None if self.config.whisper.language in {"", "auto"} else self.config.whisper.language
        self.on_log("Transcribing audio (this is the 'listen' pass)…")
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=self.config.whisper.vad_filter,
            beam_size=5,
        )
        detected = getattr(info, "language", None)
        if detected:
            self.on_log(f"Detected spoken language: {detected}")

        out: list[TranscriptSegment] = []
        total = duration or getattr(info, "duration", None) or 0.0
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            item = TranscriptSegment(
                start=float(seg.start or 0.0),
                end=float(seg.end or seg.start or 0.0),
                text=text,
                source="whisper",
            )
            out.append(item)
            current = int(item.end)
            denom = int(total) if total else max(current, 1)
            preview = text[:60] + ("…" if len(text) > 60 else "")
            self.on_progress("listen", min(current, denom), denom, preview)
        self.on_progress("listen", 1, 1, f"{len(out)} segments")
        self.on_log(f"Transcript ready: {len(out)} segments")
        return out


class WhisperUnavailable(WatchListenError):
    pass


def _resolve_device(device: str, compute_type: str) -> tuple[str, str]:
    device = (device or "auto").lower()
    compute_type = (compute_type or "auto").lower()
    if device == "auto":
        device = "cuda" if _cuda_usable() else "cpu"
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def _cuda_usable() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False
