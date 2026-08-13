import os
import shutil
import subprocess
import sys
from typing import Any
import yt_dlp
from PySide6.QtCore import QObject, Signal, Slot


def _normalize_candidate(path: str) -> str | None:
    if os.path.isfile(path):
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        return os.path.abspath(path)
    return None


def _candidate_paths(base_dir: str | None, tool_name: str) -> list[str]:
    names = [tool_name, f"{tool_name}.exe"]
    candidates: list[str] = []

    if base_dir:
        for name in names:
            candidates.append(os.path.join(base_dir, name))
            candidates.append(os.path.join(base_dir, "vendor", name))

    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir:
            for name in names:
                candidates.append(os.path.join(exe_dir, name))
                candidates.append(os.path.join(exe_dir, "vendor", name))

    return candidates


def _resolve_tool_path(tool_name: str) -> str | None:
    candidates: list[str] = []
    meipass_dir = getattr(sys, "_MEIPASS", None)
    candidates.extend(_candidate_paths(meipass_dir, tool_name))

    for candidate in candidates:
        resolved = _normalize_candidate(candidate)
        if resolved:
            return resolved

    resolved = shutil.which(tool_name)
    if resolved:
        return os.path.abspath(resolved)

    for candidate in [tool_name, f"{tool_name}.exe"]:
        resolved = _normalize_candidate(candidate)
        if resolved:
            return resolved

    return None


class _StopRequested(Exception):
    pass


class DownloadWorker(QObject):
    started = Signal()
    finished = Signal(int)
    error = Signal(str)
    output = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._process = None
        self._stopped = False

    def _set_tool_env(self, ffmpeg_path: str | None, ffprobe_path: str | None) -> None:
        if not ffmpeg_path:
            return

        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path.split(os.pathsep):
            os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}" if current_path else ffmpeg_dir
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        if ffprobe_path is not None:
            os.environ["FFPROBE_BINARY"] = ffprobe_path

    def _build_ydl_options(self, outtmpl: str, ffmpeg_path: str | None, ffprobe_path: str | None, formats: list[str]) -> dict[str, Any]:
        options: dict[str, Any] = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
        }

        if ffmpeg_path:
            options["ffmpeg_location"] = ffmpeg_path
        if ffprobe_path:
            options["ffprobe_location"] = ffprobe_path

        if "mp4" in formats:
            options.update({
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
            })
        elif "mp3" in formats and len(formats) == 1:
            options.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "2",
                }],
            })

        return options

    def _extract_mp3_from_mp4(self, mp4_path: str, ffmpeg_path: str | None) -> int:
        mp3_path = os.path.splitext(mp4_path)[0] + ".mp3"
        command = [ffmpeg_path or "ffmpeg", "-y", "-i", mp4_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", mp3_path]

        try:
            self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert self._process.stdout is not None
            for line in self._process.stdout:
                self.output.emit(line.rstrip())
            rc = self._process.wait()
            if rc != 0:
                self.output.emit(f"ffmpeg returned {rc}")
                return rc
            return 0
        except Exception as exc:
            self.error.emit(f"ffmpeg failed: {exc}")
            return 1

    def _resolve_mp4_path(self, expected_path: str | None, outdir: str) -> str | None:
        if expected_path:
            mp4_path = os.path.splitext(expected_path)[0] + ".mp4"
            if os.path.exists(mp4_path):
                return mp4_path

        candidates = [
            os.path.join(outdir, filename)
            for filename in os.listdir(outdir)
            if filename.lower().endswith(".mp4")
        ]
        if not candidates:
            return None
        return max(candidates, key=os.path.getmtime)

    @Slot(str, list, str)
    def start_download(self, url: str, formats: list, outdir: str) -> None:
        if not url:
            self.error.emit("URL vacía")
            return

        outtmpl = os.path.join(outdir, "%(title)s.%(ext)s")
        needs_ffmpeg = ("mp4" in formats and "mp3" in formats) or ("mp3" in formats)
        ffmpeg_path = _resolve_tool_path("ffmpeg") if needs_ffmpeg else None
        ffprobe_path = _resolve_tool_path("ffprobe") if needs_ffmpeg else None

        if needs_ffmpeg and not ffmpeg_path:
            self.error.emit("ffmpeg no encontrado. Instale ffmpeg para recodificar/extraer audio.")
            return
        if needs_ffmpeg and not ffprobe_path:
            self.error.emit("ffprobe no encontrado. Instale ffmpeg para recodificar/extraer audio.")
            return

        self._set_tool_env(ffmpeg_path, ffprobe_path)
        self.started.emit()

        try:
            self._stopped = False
            last_ret = 0

            expected_path = None
            try:
                with yt_dlp.YoutubeDL({"outtmpl": outtmpl, "noplaylist": True}) as probe_ydl:
                    info = probe_ydl.extract_info(url, download=False)
                    expected_path = probe_ydl.prepare_filename(info)
            except Exception:
                expected_path = None

            def progress_hook(d):
                status = d.get("status")
                if status == "downloading":
                    downloaded = d.get("downloaded_bytes") or 0
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    if total:
                        pct = downloaded * 100 / total
                        self.output.emit(f"descargando: {pct:.1f}%")
                    else:
                        self.output.emit(f"descargando: {d.get('eta', '')} ETA")
                elif status == "finished":
                    self.output.emit("descarga completada, procesando...")
                if self._stopped:
                    raise _StopRequested()

            ydl_opts: Any = self._build_ydl_options(outtmpl, ffmpeg_path, ffprobe_path, formats)
            ydl_opts["progress_hooks"] = [progress_hook]

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except _StopRequested:
                last_ret = 1
                self.output.emit("Descarga cancelada por el usuario.")
            except Exception as exc:
                last_ret = 1
                self.error.emit(f"yt_dlp error: {exc}")

            if last_ret == 0 and "mp4" in formats and "mp3" in formats:
                mp4_path = self._resolve_mp4_path(expected_path, outdir)
                if mp4_path and os.path.exists(mp4_path):
                    last_ret = self._extract_mp3_from_mp4(mp4_path, ffmpeg_path)
                else:
                    self.output.emit("No se pudo localizar el archivo MP4 resultante para extraer MP3.")

            self.finished.emit(last_ret)
        except _StopRequested:
            self.finished.emit(1)
        except Exception as exc:
            self.error.emit(str(exc))

    @Slot()
    def stop(self) -> None:
        self._stopped = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
