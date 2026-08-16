"""Generate structured notes from a unified watch+listen timeline via Ollama."""

from __future__ import annotations

from collections.abc import Callable

from watchlisten.config import Config
from watchlisten.core.timeline import format_timeline, split_timeline_by_duration
from watchlisten.models import NotesDocument, TimelineEntry, VideoMetadata
from watchlisten.utils import ModelError, format_duration, format_timestamp

LogHook = Callable[[str], None]
ProgressHook = Callable[[str, int, int, str], None]

SYSTEM_PROMPT = """You are WatchListen, an expert note-taker who has just watched and listened
to a video. You do not invent facts that are not supported by the timeline.
Write clean GitHub-flavoured Markdown. Use the video's language if it is consistent;
otherwise write in clear English. Do not wrap the whole answer in a code fence.
"""

NOTES_INSTRUCTIONS = """Produce notes with EXACTLY this structure (include a heading even if a
section is short):

# {title}

**Source:** {url}
**Channel:** {channel}
**Duration:** {duration}

## TL;DR
A tight 4–8 sentence executive summary of the whole video.

## Detailed Notes
Section-wise notes. Prefer the video's own chapters when present. Each section
heading should include a timestamp like `### Setup [3:12]`. Use bullet points.
Quote on-screen text / code / slide titles when they appear in Visual lines.

## Key Visuals
Bullet list of diagrams, slides, code, whiteboards, charts that appeared.
Format: `- [M:SS] what was on screen — why it matters`

## Notable Quotes
2–8 verbatim (or tightly paraphrased) quotes. Format:
> quote
> — [M:SS]

## Glossary
Markdown table:
| Term | Meaning |

If there are no specialised terms, write `_None_`.

## Takeaways
5–10 actionable bullets a viewer should remember or do next.
"""


class NotesGenerator:
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

    def generate(
        self,
        metadata: VideoMetadata,
        timeline: list[TimelineEntry],
    ) -> NotesDocument:
        if not timeline:
            raise ModelError("Cannot generate notes: the unified timeline is empty.")

        chunk_seconds = max(self.config.notes.chunk_minutes, 1.0) * 60.0
        chunks = split_timeline_by_duration(timeline, chunk_seconds, metadata.chapters)
        self.on_log(f"Notes map-reduce over {len(chunks)} chunk(s)")

        if len(chunks) == 1:
            self.on_progress("notes", 0, 1, "single-pass generation")
            markdown = self._complete_notes(metadata, format_timeline(chunks[0]))
            self.on_progress("notes", 1, 1, "done")
            return NotesDocument(markdown=markdown, title=metadata.title, metadata=metadata)

        partials: list[str] = []
        total = len(chunks) + 1
        for idx, chunk in enumerate(chunks, start=1):
            start = format_timestamp(chunk[0].start)
            end = format_timestamp(chunk[-1].end)
            self.on_progress("notes", idx - 1, total, f"summarising {start}–{end}")
            self.on_log(f"Map pass {idx}/{len(chunks)} ({start}–{end})")
            partials.append(self._summarise_chunk(metadata, chunk, idx, len(chunks)))

        self.on_progress("notes", len(chunks), total, "reducing into final notes")
        markdown = self._reduce(metadata, partials)
        self.on_progress("notes", total, total, "done")
        return NotesDocument(markdown=markdown, title=metadata.title, metadata=metadata)

    def generate_with_tools(
        self,
        metadata: VideoMetadata,
        timeline: list[TimelineEntry],
        tool_runner: Callable[[str, dict], str],
        tool_schemas: list[dict],
    ) -> NotesDocument:
        """Optional agentic pass: the text model may re-watch / re-listen first."""
        from watchlisten.core.tools import TOOL_SYSTEM, run_tool_loop

        preview = format_timeline(timeline)
        # Keep the seed context bounded so the model is forced to use tools
        seed = preview[:4000]
        user = (
            f"Video: {metadata.title} ({format_duration(metadata.duration)})\n"
            f"URL: {metadata.webpage_url or metadata.url}\n"
            f"Channel: {metadata.channel or metadata.uploader}\n\n"
            f"A condensed preview of the unified timeline follows. "
            f"Use tools to inspect anything you need before writing notes.\n\n"
            f"{seed}\n\n"
            f"{NOTES_INSTRUCTIONS.format(title=metadata.title, url=metadata.webpage_url or metadata.url, channel=metadata.channel or metadata.uploader, duration=format_duration(metadata.duration))}"
        )
        self.on_log("Agentic notes pass (model may watch/listen selectively)")
        markdown = run_tool_loop(
            client=self._client(),
            model=self.config.models.text,
            system=TOOL_SYSTEM,
            user=user,
            tools=tool_schemas,
            runner=tool_runner,
            max_rounds=self.config.notes.max_tool_rounds,
            temperature=self.config.notes.temperature,
            on_log=self.on_log,
        )
        if not markdown.strip():
            self.on_log("Agentic pass returned empty notes; falling back to map-reduce.")
            return self.generate(metadata, timeline)
        return NotesDocument(markdown=_strip_fences(markdown), title=metadata.title, metadata=metadata)

    def _complete_notes(self, metadata: VideoMetadata, timeline_text: str) -> str:
        user = _header(metadata) + "\n\n## Unified timeline (watch + listen)\n\n" + timeline_text
        user += "\n\n" + NOTES_INSTRUCTIONS.format(
            title=metadata.title,
            url=metadata.webpage_url or metadata.url,
            channel=metadata.channel or metadata.uploader,
            duration=format_duration(metadata.duration),
        )
        if self.config.notes.language not in {"", "auto"}:
            user += f"\nWrite the notes in {self.config.notes.language}."
        return _strip_fences(self._chat(SYSTEM_PROMPT, user))

    def _summarise_chunk(
        self,
        metadata: VideoMetadata,
        chunk: list[TimelineEntry],
        index: int,
        total: int,
    ) -> str:
        start = format_timestamp(chunk[0].start)
        end = format_timestamp(chunk[-1].end)
        user = (
            f"{_header(metadata)}\n\n"
            f"This is chunk {index}/{total} covering {start}–{end}.\n"
            f"Write a detailed section summary the final note-taker can merge later.\n"
            f"Keep timestamps. Quote important spoken lines and describe key visuals.\n"
            f"Use Markdown with a heading `## Chunk {index}: {start}–{end}`.\n\n"
            f"{format_timeline(chunk)}"
        )
        return self._chat(
            "You summarise one slice of a watched/listened video. Be faithful and dense.",
            user,
        )

    def _reduce(self, metadata: VideoMetadata, partials: list[str]) -> str:
        joined = "\n\n---\n\n".join(partials)
        user = (
            f"{_header(metadata)}\n\n"
            "Below are sequential chunk summaries covering the whole video. "
            "Merge them into ONE polished notes document. Deduplicate, keep "
            "the best timestamps, and follow the required structure.\n\n"
            f"{NOTES_INSTRUCTIONS.format(title=metadata.title, url=metadata.webpage_url or metadata.url, channel=metadata.channel or metadata.uploader, duration=format_duration(metadata.duration))}\n\n"
            f"{joined}"
        )
        if self.config.notes.language not in {"", "auto"}:
            user += f"\nWrite the notes in {self.config.notes.language}."
        return _strip_fences(self._chat(SYSTEM_PROMPT, user))

    def _chat(self, system: str, user: str) -> str:
        try:
            response = self._client().chat(
                model=self.config.models.text,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                options={"temperature": self.config.notes.temperature},
            )
        except Exception as exc:
            raise ModelError(
                f"Ollama text model '{self.config.models.text}' failed: {exc}. "
                f"Is Ollama running and has the model been pulled?"
            ) from exc
        content = _content_of(response).strip()
        if not content:
            raise ModelError("The text model returned an empty response.")
        return content

    def _client(self):
        import ollama

        return ollama.Client(host=self.config.resolved_ollama_host())


def _header(metadata: VideoMetadata) -> str:
    chapters = ""
    if metadata.chapters:
        items = ", ".join(
            f"{ch.title} ({format_timestamp(ch.start)})" for ch in metadata.chapters
        )
        chapters = f"\nChapters: {items}"
    return (
        f"Title: {metadata.title}\n"
        f"URL: {metadata.webpage_url or metadata.url}\n"
        f"Channel: {metadata.channel or metadata.uploader}\n"
        f"Duration: {format_duration(metadata.duration)}"
        f"{chapters}"
    )


def _content_of(response: object) -> str:
    if isinstance(response, dict):
        msg = response.get("message") or {}
        if isinstance(msg, dict):
            return str(msg.get("content") or "")
    message = getattr(response, "message", None)
    if message is not None:
        return str(getattr(message, "content", "") or "")
    return str(response or "")


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped
