from __future__ import annotations

from watchlisten.__main__ import _build_parser, main


def test_parser_accepts_common_flags():
    args = _build_parser().parse_args(
        [
            "https://youtu.be/dQw4w9WgXcQ",
            "-f",
            "md,html",
            "--skip-vision",
            "--captions-only",
            "--cli",
        ]
    )
    assert args.skip_vision is True
    assert args.cli is True
    assert args.formats == "md,html"


def test_version_exits_zero():
    assert main(["--version"]) == 0
