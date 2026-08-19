"""Run faster-whisper in a fresh process so the TUI's open FDs cannot break it.

CTranslate2/faster-whisper spawn helper processes. When the parent is a
Textual worker thread, those helpers inherit invalid file descriptors and
die with: ``bad value(s) in fds to keep``. A spawned interpreter has a
clean FD table.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Must be set before importing faster_whisper / ctranslate2.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("CT2_USE_EXPERIMENTAL_PACKED_GEMM", "0")


def transcribe_file(
    audio_path: str,
    *,
    model_size: str,
    device: str,
    compute_type: str,
    language: str | None,
    vad_filter: bool,
) -> dict:
    from faster_whisper import WhisperModel

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=max(1, os.cpu_count() or 4),
        num_workers=1,
    )
    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=vad_filter,
        beam_size=5,
    )
    segments = []
    for seg in segments_iter:
        text = (seg.text or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start": float(seg.start or 0.0),
                "end": float(seg.end or seg.start or 0.0),
                "text": text,
            }
        )
    return {
        "ok": True,
        "language": getattr(info, "language", None),
        "duration": getattr(info, "duration", None),
        "segments": segments,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print("usage: python -m watchlisten.core.whisper_worker JOB.json OUT.json", file=sys.stderr)
        return 2
    job_path = Path(argv[0])
    out_path = Path(argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    language = job.get("language")
    if language in {"", "auto", None}:
        language = None
    try:
        payload = transcribe_file(
            job["audio_path"],
            model_size=job["model_size"],
            device=job["device"],
            compute_type=job["compute_type"],
            language=language,
            vad_filter=bool(job.get("vad_filter", True)),
        )
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    out_path.write_text(json.dumps(payload), encoding="utf-8")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
