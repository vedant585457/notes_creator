"""Merge audio transcript + visual frame descriptions into one chronology."""

from __future__ import annotations

from watchlisten.models import Chapter, FrameDescription, TimelineEntry, TranscriptSegment
from watchlisten.utils import format_timestamp


def merge_timeline(
    transcript: list[TranscriptSegment],
    frames: list[FrameDescription],
    chapters: list[Chapter] | None = None,
    *,
    visual_attach_window: float = 4.0,
) -> list[TimelineEntry]:
    """Attach each frame to the overlapping (or nearest) spoken segment.

    Frames that fall in a silence gap longer than `visual_attach_window`
    become their own visual-only entries so diagrams shown without speech
    are not lost.
    """
    chapters = chapters or []
    frames_sorted = sorted(frames, key=lambda f: f.timestamp)
    segs = sorted(transcript, key=lambda s: (s.start, s.end))

    used: set[int] = set()
    entries: list[TimelineEntry] = []

    for seg in segs:
        attached: list[FrameDescription] = []
        for idx, frame in enumerate(frames_sorted):
            if idx in used:
                continue
            if seg.start - visual_attach_window <= frame.timestamp <= seg.end + visual_attach_window:
                attached.append(frame)
                used.add(idx)
        entries.append(
            TimelineEntry(
                start=seg.start,
                end=seg.end,
                audio=seg.text,
                visuals=attached,
                speaker=seg.speaker,
                chapter=_chapter_at(chapters, seg.start),
            )
        )

    orphans = [f for idx, f in enumerate(frames_sorted) if idx not in used]
    for frame in orphans:
        entries.append(
            TimelineEntry(
                start=frame.timestamp,
                end=frame.timestamp,
                audio="",
                visuals=[frame],
                chapter=_chapter_at(chapters, frame.timestamp),
            )
        )

    entries.sort(key=lambda e: (e.start, e.end))
    return _coalesce_tiny_visuals(entries)


def format_timeline(entries: list[TimelineEntry], *, include_ocr: bool = True) -> str:
    """Human-readable script a text-only model can 'experience' the video from."""
    lines: list[str] = []
    last_chapter: str | None = None
    for entry in entries:
        if entry.chapter and entry.chapter != last_chapter:
            lines.append("")
            lines.append(f"## {entry.chapter}")
            last_chapter = entry.chapter
        stamp = _stamp(entry)
        bits: list[str] = []
        if entry.visuals:
            vis_parts = []
            for frame in entry.visuals:
                piece = frame.description.strip() or "(undescribed frame)"
                if include_ocr and frame.ocr_text.strip():
                    piece += f" [OCR: {frame.ocr_text.strip()}]"
                vis_parts.append(piece)
            bits.append(f"(Visual: {' | '.join(vis_parts)})")
        if entry.audio.strip():
            speaker = f"{entry.speaker}: " if entry.speaker else ""
            bits.append(f"(Audio: {speaker}{entry.audio.strip()})")
        if bits:
            lines.append(f"{stamp} {' '.join(bits)}")
    return "\n".join(lines).strip() + ("\n" if entries else "")


def split_timeline_by_duration(
    entries: list[TimelineEntry],
    chunk_seconds: float,
    chapters: list[Chapter] | None = None,
) -> list[list[TimelineEntry]]:
    """Chunk a timeline for map-reduce. Prefer chapter boundaries when present."""
    if not entries:
        return []
    if chunk_seconds <= 0:
        return [entries]

    if chapters:
        chapter_chunks = _split_by_chapters(entries, chapters)
        # If a single chapter is still huge, split it further by duration
        out: list[list[TimelineEntry]] = []
        for group in chapter_chunks:
            out.extend(_split_by_seconds(group, chunk_seconds))
        return out
    return _split_by_seconds(entries, chunk_seconds)


def timeline_plain_text(entries: list[TimelineEntry]) -> str:
    """Flatten just the spoken words, for keyword search / quotes."""
    return " ".join(e.audio.strip() for e in entries if e.audio.strip())


def _split_by_chapters(
    entries: list[TimelineEntry], chapters: list[Chapter]
) -> list[list[TimelineEntry]]:
    buckets: dict[str, list[TimelineEntry]] = {}
    order: list[str] = []
    for ch in chapters:
        order.append(ch.title)
        buckets[ch.title] = []
    leftover_key = "__other__"
    buckets[leftover_key] = []
    for entry in entries:
        key = entry.chapter or leftover_key
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(entry)
    groups = [buckets[k] for k in order if buckets.get(k)]
    if buckets[leftover_key] and leftover_key not in order:
        groups.append(buckets[leftover_key])
    return groups


def _split_by_seconds(entries: list[TimelineEntry], chunk_seconds: float) -> list[list[TimelineEntry]]:
    if not entries:
        return []
    chunks: list[list[TimelineEntry]] = []
    current: list[TimelineEntry] = []
    origin = entries[0].start
    for entry in entries:
        if current and (entry.start - origin) >= chunk_seconds:
            chunks.append(current)
            current = [entry]
            origin = entry.start
        else:
            current.append(entry)
    if current:
        chunks.append(current)
    return chunks


def _chapter_at(chapters: list[Chapter], t: float) -> str | None:
    for ch in chapters:
        end = ch.end if ch.end is not None else float("inf")
        if ch.start <= t < end or (ch.end is not None and t == ch.end and ch == chapters[-1]):
            return ch.title
    return None


def _stamp(entry: TimelineEntry) -> str:
    if abs(entry.end - entry.start) < 0.4:
        return f"[{format_timestamp(entry.start)}]"
    return f"[{format_timestamp(entry.start)}–{format_timestamp(entry.end)}]"


def _coalesce_tiny_visuals(entries: list[TimelineEntry]) -> list[TimelineEntry]:
    """Merge consecutive visual-only entries that sit less than 1.5s apart."""
    if not entries:
        return entries
    out: list[TimelineEntry] = [entries[0]]
    for entry in entries[1:]:
        prev = out[-1]
        both_visual = not prev.audio and not entry.audio
        close = abs(entry.start - prev.end) <= 1.5
        if both_visual and close:
            prev.visuals.extend(entry.visuals)
            prev.end = max(prev.end, entry.end)
            continue
        out.append(entry)
    return out
