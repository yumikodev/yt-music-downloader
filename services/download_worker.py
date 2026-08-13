import os
import shutil
import subprocess
import sys
import yt_dlp
from typing import Any
from PySide6.QtCore import QObject, Signal, Slot


def _resolve_tool_path(tool_name: str) -> str | None:
  candidates: list[str] = []

  if getattr(sys, "_MEIPASS", None):
    candidates.append(os.path.join(sys._MEIPASS, tool_name))
    candidates.append(os.path.join(sys._MEIPASS, f"{tool_name}.exe"))

  if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(exe_dir, tool_name))
    candidates.append(os.path.join(exe_dir, f"{tool_name}.exe"))

  for candidate in candidates:
    if os.path.isfile(candidate):
      return candidate

  resolved = shutil.which(tool_name)
  if resolved:
    return resolved

  for candidate in [tool_name, f"{tool_name}.exe"]:
    if os.path.isfile(candidate):
      return os.path.abspath(candidate)

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

  @Slot(str, list, str)
  def start_download(self, url: str, formats: list, outdir: str) -> None:
    if not url:
      self.error.emit("URL vacía")
      return
    outtmpl = os.path.join(outdir, "%(title)s.%(ext)s")
    # Usar la API Python de yt_dlp para evitar depender del binario
    if yt_dlp is None:
      self.error.emit("paquete yt_dlp no instalado. Instale 'yt-dlp' vía pip.")
      return

    # comprobar ffmpeg si la operación lo requiere
    needs_ffmpeg = ("mp4" in formats and "mp3" in formats) or ("mp3" in formats)
    ffmpeg_path = _resolve_tool_path("ffmpeg") if needs_ffmpeg else None
    ffprobe_path = _resolve_tool_path("ffprobe") if needs_ffmpeg else None
    if needs_ffmpeg and not ffmpeg_path:
      self.error.emit("ffmpeg no encontrado. Instale ffmpeg para recodificar/extraer audio.")
      return
    if needs_ffmpeg and not ffprobe_path:
      self.error.emit("ffprobe no encontrado. Instale ffmpeg para recodificar/extraer audio.")
      return

    if ffmpeg_path:
      ffmpeg_dir = os.path.dirname(ffmpeg_path)
      current_path = os.environ.get("PATH", "")
      if ffmpeg_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}" if current_path else ffmpeg_dir

    self.started.emit()
    try:
      self._stopped = False
      last_ret = 0

      # Preparar un YDL temporal para obtener metadata y nombre esperado
      try:
        with yt_dlp.YoutubeDL({"outtmpl": outtmpl, "noplaylist": True}) as probe_ydl:
          info = probe_ydl.extract_info(url, download=False)
          expected_path = probe_ydl.prepare_filename(info)
      except Exception:
        info = None
        expected_path = None

      # Hook de progreso para emitir salida y permitir parada
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

      # Construir opciones según formato solicitado
      ydl_opts: Any = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
      }
      if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = ffmpeg_path
      if ffprobe_path:
        ydl_opts["ffprobe_location"] = ffprobe_path

      if "mp4" in formats:
        ydl_opts.update({"format": "bestvideo+bestaudio/best", "merge_output_format": "mp4"})
      elif "mp3" in formats and len(formats) == 1:
        # Extraer audio directamente con postprocessor (requiere ffmpeg)
        ydl_opts.update({
          "format": "bestaudio/best",
          "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "2",
          }],
        })

      # Ejecutar la descarga con yt_dlp API
      try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
          ydl.download([url])
      except _StopRequested:
        last_ret = 1
        self.output.emit("Descarga cancelada por el usuario.")
      except Exception as e:
        last_ret = 1
        self.error.emit(f"yt_dlp error: {e}")

      # Si se pidió MP4 y MP3, y la descarga a MP4 fue exitosa, extraer MP3 con ffmpeg
      if last_ret == 0 and "mp4" in formats and "mp3" in formats:
        mp4_path = None
        if expected_path:
          base = os.path.splitext(expected_path)[0]
          mp4_path = f"{base}.mp4"

        if not mp4_path or not os.path.exists(mp4_path):
          candidates = [os.path.join(outdir, f) for f in os.listdir(outdir) if f.lower().endswith(".mp4")]
          if candidates:
            mp4_path = max(candidates, key=os.path.getmtime)

        if mp4_path and os.path.exists(mp4_path):
          mp3_path = os.path.splitext(mp4_path)[0] + ".mp3"
          ff_cmd = [ffmpeg_path or "ffmpeg", "-y", "-i", mp4_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", mp3_path]
          try:
            ff_proc = subprocess.Popen(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert ff_proc.stdout is not None
            for line in ff_proc.stdout:
              self.output.emit(line.rstrip())
            rc = ff_proc.wait()
            if rc != 0:
              last_ret = rc
              self.output.emit(f"ffmpeg returned {rc}")
          except Exception as e:
            self.error.emit(f"ffmpeg failed: {e}")
            last_ret = 1
        else:
          self.output.emit("No se pudo localizar el archivo MP4 resultante para extraer MP3.")

      self.finished.emit(last_ret)
    except _StopRequested:
      self.finished.emit(1)
    except Exception as e:
      self.error.emit(str(e))

  @Slot()
  def stop(self) -> None:
    self._stopped = True
    # Si hay un proceso ffmpeg activo, terminarlo
    if self._process:
      try:
        self._process.terminate()
      except Exception:
        pass
