import os
import sys

from services import download_worker as dw


def test_requires_ffmpeg_for_mp4_only():
    assert dw._requires_ffmpeg(["mp4"]) is True
    assert dw._requires_ffmpeg(["mp3"]) is True
    assert dw._requires_ffmpeg(["mp4", "mp3"]) is True
    assert dw._requires_ffmpeg([]) is False


def test_resolve_tool_paths_handles_frozen_bundle(tmp_path, monkeypatch):
    ffmpeg_path = tmp_path / "ffmpeg"
    ffprobe_path = tmp_path / "ffprobe"

    ffmpeg_path.write_text("binary", encoding="utf-8")
    ffprobe_path.write_text("binary", encoding="utf-8")
    os.chmod(ffmpeg_path, 0o755)
    os.chmod(ffprobe_path, 0o755)

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    resolved_ffmpeg, resolved_ffprobe = dw._resolve_tool_paths("ffmpeg", "ffprobe")

    assert resolved_ffmpeg == str(ffmpeg_path.resolve())
    assert resolved_ffprobe == str(ffprobe_path.resolve())
