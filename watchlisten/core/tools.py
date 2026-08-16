"""Ollama tool-calling schemas so a text-only model can watch / listen on demand."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from watchlisten.models import FrameDescription, TranscriptSegment, VideoMetadata
from watchlisten.utils import format_duration, format_timestamp, parse_timestamp

TOOL_SYSTEM = """You are WatchListen. You can selectively re-watch frames and re-listen to
audio the way a human reviews a video — you do not need to consume everything
linearly. Use tools until you understand the video well enough to write notes,
then output the final Markdown notes and stop calling tools.
"""

LISTEN_TO_SEGMENT = {
    "type": "function",
    "function": {
        "name": "listen_to_segment",
        "description": (
            "Return the spoken-word transcript for a time range so you can "
            "'listen' to that part of the video."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": "Start timestamp, MM:SS or HH:MM:SS",
                },
                "end_time": {
                    "type": "string",
                    "description": "End timestamp, MM:SS or HH:MM:SS",
                },
            },
            "required": ["start_time", "end_time"],
        },
    },
}

WATCH_FRAME_AT = {
    "type": "function",
    "function": {
        "name": "watch_frame_at",
        "description": (
            "Return the visual description of the frame nearest to a timestamp "
            "so you can 'watch' that moment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "string",
                    "description": "Timestamp, MM:SS or HH:MM:SS",
                },
            },
            "required": ["timestamp"],
        },
    },
}

SEARCH_TRANSCRIPT = {
    "type": "function",
    "function": {
        "name": "search_transcript",
        "description": (
            "Keyword search over the full transcript. Returns matching lines "
            "with timestamps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Case-insensitive keyword or phrase"},
            },
            "required": ["keyword"],
        },
    },
}

GET_VIDEO_METADATA = {
    "type": "function",
    "function": {
        "name": "get_video_metadata",
        "description": "Return the video title, duration, chapters, and description.",
        "parameters": {"type": "object", "properties": {}},
    },
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    LISTEN_TO_SEGMENT,
    WATCH_FRAME_AT,
    SEARCH_TRANSCRIPT,
    GET_VIDEO_METADATA,
]


class VideoTools:
    """Bound implementations of the four watch/listen tools."""

    def __init__(
        self,
        metadata: VideoMetadata,
        transcript: list[TranscriptSegment],
        frames: list[FrameDescription],
        *,
        watch_fallback: Callable[[float], FrameDescription] | None = None,
    ) -> None:
        self.metadata = metadata
        self.transcript = transcript
        self.frames = list(frames)
        self.watch_fallback = watch_fallback

    def dispatch(self, name: str, arguments: dict[str, Any] | None) -> str:
        args = arguments or {}
        if name == "listen_to_segment":
            return self.listen_to_segment(str(args.get("start_time", "0")), str(args.get("end_time", "0")))
        if name == "watch_frame_at":
            return self.watch_frame_at(str(args.get("timestamp", "0")))
        if name == "search_transcript":
            return self.search_transcript(str(args.get("keyword", "")))
        if name == "get_video_metadata":
            return self.get_video_metadata()
        return f"Unknown tool: {name}"

    def listen_to_segment(self, start_time: str, end_time: str) -> str:
        try:
            start = parse_timestamp(start_time)
            end = parse_timestamp(end_time)
        except ValueError as exc:
            return f"Invalid timestamp: {exc}"
        if end < start:
            start, end = end, start
        hits = [s for s in self.transcript if s.end >= start and s.start <= end]
        if not hits:
            return f"No spoken words between {format_timestamp(start)} and {format_timestamp(end)}."
        lines = [
            f"[{format_timestamp(s.start)}–{format_timestamp(s.end)}] {s.text}" for s in hits
        ]
        return "\n".join(lines)

    def watch_frame_at(self, timestamp: str) -> str:
        try:
            ts = parse_timestamp(timestamp)
        except ValueError as exc:
            return f"Invalid timestamp: {exc}"
        frame = self._nearest_frame(ts)
        if frame is None or abs(frame.timestamp - ts) > 12:
            if self.watch_fallback is not None:
                try:
                    frame = self.watch_fallback(ts)
                    self.frames.append(frame)
                except Exception as exc:
                    return f"Could not watch frame at {format_timestamp(ts)}: {exc}"
            elif frame is None:
                return f"No analysed frames near {format_timestamp(ts)}."
        assert frame is not None
        bits = [
            f"Frame at {format_timestamp(frame.timestamp)} (requested {format_timestamp(ts)}):",
            frame.description or "(no description)",
        ]
        if frame.ocr_text:
            bits.append(f"OCR: {frame.ocr_text}")
        return "\n".join(bits)

    def search_transcript(self, keyword: str) -> str:
        needle = (keyword or "").strip()
        if not needle:
            return "Keyword is empty."
        lowered = needle.lower()
        hits = [s for s in self.transcript if lowered in s.text.lower()]
        if not hits:
            return f"No transcript matches for {needle!r}."
        # Cap so a common word cannot dump the whole video into context
        shown = hits[:25]
        lines = [f"[{format_timestamp(s.start)}] {s.text}" for s in shown]
        if len(hits) > len(shown):
            lines.append(f"… {len(hits) - len(shown)} more matches omitted")
        return "\n".join(lines)

    def get_video_metadata(self) -> str:
        meta = self.metadata
        lines = [
            f"Title: {meta.title}",
            f"URL: {meta.webpage_url or meta.url}",
            f"Channel: {meta.channel or meta.uploader}",
            f"Duration: {format_duration(meta.duration)} ({int(meta.duration)}s)",
        ]
        if meta.upload_date:
            lines.append(f"Uploaded: {meta.upload_date}")
        if meta.chapters:
            lines.append("Chapters:")
            for ch in meta.chapters:
                end = format_timestamp(ch.end) if ch.end is not None else "?"
                lines.append(f"  - {ch.title} [{format_timestamp(ch.start)}–{end}]")
        desc = (meta.description or "").strip()
        if desc:
            lines.append("Description:")
            lines.append(desc[:1200] + ("…" if len(desc) > 1200 else ""))
        return "\n".join(lines)

    def _nearest_frame(self, ts: float) -> FrameDescription | None:
        if not self.frames:
            return None
        return min(self.frames, key=lambda f: abs(f.timestamp - ts))


def run_tool_loop(
    *,
    client: Any,
    model: str,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    runner: Callable[[str, dict[str, Any]], str],
    max_rounds: int = 8,
    temperature: float = 0.3,
    on_log: Callable[[str], None] | None = None,
) -> str:
    """Drive an Ollama chat that may emit tool calls until it writes notes."""
    log = on_log or (lambda _m: None)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last_text = ""
    for round_idx in range(max(1, max_rounds)):
        response = client.chat(
            model=model,
            messages=messages,
            tools=tools,
            options={"temperature": temperature},
        )
        message = _as_message_dict(response)
        messages.append(message)
        tool_calls = message.get("tool_calls") or []
        content = (message.get("content") or "").strip()
        if content:
            last_text = content
        if not tool_calls:
            return last_text
        log(f"Tool round {round_idx + 1}: {len(tool_calls)} call(s)")
        for call in tool_calls:
            name, arguments, call_id = _parse_tool_call(call)
            log(f"  → {name}({arguments})")
            try:
                result = runner(name, arguments)
            except Exception as exc:
                result = f"Tool error: {exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_name": name,
                    "tool_call_id": call_id,
                    "content": result[:8000],
                }
            )
    log("Reached max tool rounds; using last model text.")
    return last_text


def _as_message_dict(response: object) -> dict[str, Any]:
    message = None
    if isinstance(response, dict):
        message = response.get("message")
    else:
        message = getattr(response, "message", None)
    if isinstance(message, dict):
        return {
            "role": message.get("role") or "assistant",
            "content": message.get("content") or "",
            "tool_calls": message.get("tool_calls") or [],
        }
    if message is None:
        return {"role": "assistant", "content": "", "tool_calls": []}
    tool_calls = getattr(message, "tool_calls", None) or []
    serialised = []
    for call in tool_calls:
        if isinstance(call, dict):
            serialised.append(call)
        else:
            fn = getattr(call, "function", None)
            serialised.append(
                {
                    "id": getattr(call, "id", "") or "",
                    "type": "function",
                    "function": {
                        "name": getattr(fn, "name", "") if fn is not None else "",
                        "arguments": getattr(fn, "arguments", {}) if fn is not None else {},
                    },
                }
            )
    return {
        "role": getattr(message, "role", None) or "assistant",
        "content": getattr(message, "content", None) or "",
        "tool_calls": serialised,
    }


def _parse_tool_call(call: object) -> tuple[str, dict[str, Any], str]:
    if isinstance(call, dict):
        fn = call.get("function") or {}
        name = str(fn.get("name") or call.get("name") or "")
        arguments = fn.get("arguments") or call.get("arguments") or {}
        call_id = str(call.get("id") or "")
    else:
        fn = getattr(call, "function", None)
        name = str(getattr(fn, "name", "") if fn is not None else getattr(call, "name", "") or "")
        arguments = getattr(fn, "arguments", {}) if fn is not None else {}
        call_id = str(getattr(call, "id", "") or "")
    if isinstance(arguments, str):
        import json

        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    return name, arguments, call_id
