from __future__ import annotations

import pytest

from watchlisten.models import ExportFormat
from watchlisten.utils import (
    URLValidationError,
    extract_video_id,
    format_duration,
    format_timestamp,
    is_youtube_url,
    normalize_youtube_url,
    parse_timestamp,
    sanitize_filename,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1:02", 62.0),
        ("01:02", 62.0),
        ("1:02:03", 3723.0),
        ("00:00:03.5", 3.5),
        ("90", 90.0),
        (12, 12.0),
        (3.25, 3.25),
        ("  4:05  ", 245.0),
    ],
)
def test_parse_timestamp(raw, expected):
    assert parse_timestamp(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "nope", "1:2:3:4", "-3"])
def test_parse_timestamp_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_timestamp(raw)


def test_format_timestamp_under_hour():
    assert format_timestamp(62) == "1:02"
    assert format_timestamp(9) == "0:09"


def test_format_timestamp_hour_and_millis():
    assert format_timestamp(3723) == "1:02:03"
    assert format_timestamp(1.5, millis=True) == "0:01.500"


def test_format_duration():
    assert format_duration(8) == "8s"
    assert format_duration(68) == "1m 08s"
    assert format_duration(3723) == "1h 02m"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
        "dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=12s",
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == "dQw4w9WgXcQ"
    assert is_youtube_url(url)


def test_normalize_youtube_url():
    assert normalize_youtube_url("youtu.be/dQw4w9WgXcQ") == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


@pytest.mark.parametrize(
    "url",
    ["", "https://vimeo.com/123", "https://example.com", "not a url"],
)
def test_reject_non_youtube(url):
    assert is_youtube_url(url) is False
    with pytest.raises(URLValidationError):
        extract_video_id(url)


def test_sanitize_filename():
    assert sanitize_filename('My Video: "Final"?') == "My_Video_Final"
    assert sanitize_filename("...") == "notes"
    assert len(sanitize_filename("x" * 200)) == 80


def test_export_format_parse():
    assert ExportFormat.parse_many("md,html,pdf") == [
        ExportFormat.MARKDOWN,
        ExportFormat.HTML,
        ExportFormat.PDF,
    ]
    assert ExportFormat.parse_many("markdown") == [ExportFormat.MARKDOWN]
    assert ExportFormat.parse_many(None) == [ExportFormat.MARKDOWN]
    with pytest.raises(ValueError):
        ExportFormat.parse_many("docx")
