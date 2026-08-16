from __future__ import annotations

from watchlisten.core.tools import VideoTools, _parse_tool_call
from watchlisten.models import FrameDescription, TranscriptSegment, VideoMetadata


def _tools(tmp_path) -> VideoTools:
    meta = VideoMetadata(
        url="https://www.youtube.com/watch?v=aaaaaaaaaaa",
        video_id="aaaaaaaaaaa",
        title="Demo Video",
        duration=120,
        description="A demo.",
        channel="WatchListen",
    )
    transcript = [
        TranscriptSegment(start=0, end=3, text="Welcome to the API workshop"),
        TranscriptSegment(start=10, end=14, text="We now design the request flow"),
        TranscriptSegment(start=50, end=55, text="And that is the conclusion"),
    ]
    frame = FrameDescription(
        timestamp=11.0,
        path=tmp_path / "f.jpg",
        description="Whiteboard with 'API Flow'",
        ocr_text="API Flow",
    )
    return VideoTools(meta, transcript, [frame])


def test_listen_to_segment(tmp_path):
    tools = _tools(tmp_path)
    heard = tools.listen_to_segment("0:09", "0:15")
    assert "request flow" in heard
    assert "Welcome" not in heard


def test_listen_invalid_timestamp(tmp_path):
    tools = _tools(tmp_path)
    assert "Invalid timestamp" in tools.listen_to_segment("nope", "0:01")


def test_watch_frame_at_nearest(tmp_path):
    tools = _tools(tmp_path)
    seen = tools.watch_frame_at("0:12")
    assert "API Flow" in seen
    assert "Whiteboard" in seen


def test_search_transcript(tmp_path):
    tools = _tools(tmp_path)
    hits = tools.search_transcript("api")
    assert "workshop" in hits
    assert "No transcript" in tools.search_transcript("bananas")
    assert "empty" in tools.search_transcript("  ").lower()


def test_get_video_metadata(tmp_path):
    tools = _tools(tmp_path)
    blob = tools.get_video_metadata()
    assert "Demo Video" in blob
    assert "WatchListen" in blob


def test_dispatch_unknown(tmp_path):
    tools = _tools(tmp_path)
    assert "Unknown tool" in tools.dispatch("dance", {})


def test_parse_tool_call_json_arguments():
    name, args, call_id = _parse_tool_call(
        {
            "id": "c1",
            "function": {"name": "search_transcript", "arguments": '{"keyword": "flow"}'},
        }
    )
    assert name == "search_transcript"
    assert args == {"keyword": "flow"}
    assert call_id == "c1"
