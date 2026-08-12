import os
import shutil
import subprocess
from PySide6.QtCore import QObject, Signal, Slot

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

    # Construir lista de tareas (comandos) a ejecutar en secuencia según formatos seleccionados
    tasks: list[list[str]] = []

    if "mp4" in formats and "mp3" in formats:
      # Queremos evitar re-descargar: descargamos/recodificamos a MP4 y luego extraemos MP3 con ffmpeg.
      # Primero obtenemos el nombre de archivo esperado para construir rutas.
      try:
        get_name_proc = subprocess.run(["yt-dlp", "--get-filename", "-o", outtmpl, url], capture_output=True, text=True, check=True)
        expected_path = get_name_proc.stdout.strip()
      except Exception:
        expected_path = None

      cmd_mp4 = ["yt-dlp", "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4", "--recode-video", "mp4", "-o", outtmpl, url]
      tasks = [cmd_mp4]
    elif "mp4" in formats:
      cmd_mp4 = ["yt-dlp", "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4", "--recode-video", "mp4", "-o", outtmpl, url]
      tasks = [cmd_mp4]
    elif "mp3" in formats:
      cmd_mp3 = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", outtmpl, url]
      tasks = [cmd_mp3]
    else:
      tasks = [["yt-dlp", "-f", "bestaudio/best", "-o", outtmpl, url]]

    # Si alguna tarea requiere ffmpeg (recode o extract), verificar disponibilidad
    needs_ffmpeg = any(('--recode-video' in cmd) or ('-x' in cmd) for cmd in tasks)
    if needs_ffmpeg and not shutil.which("ffmpeg"):
      self.error.emit("ffmpeg no encontrado. Instale ffmpeg para recodificar/extraer audio.")
      return

    self.started.emit()
    try:
      self._stopped = False
      last_ret = 0
      for cmd in tasks:
        self._process = subprocess.Popen(
          cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          text=True,
          bufsize=1,
        )

        assert self._process.stdout is not None
        for line in self._process.stdout:
          self.output.emit(line.rstrip())
          if self._stopped:
            try:
              self._process.terminate()
            except Exception:
              pass
            break

        last_ret = self._process.wait()
        self._process = None
        if last_ret != 0:
          # Stop executing further tasks on error
          break

      # Si se solicitó MP3 además de MP4 y la descarga/recodificación a MP4 fue exitosa,
      # extraemos audio con ffmpeg desde el archivo resultante.
      if last_ret == 0 and "mp4" in formats and "mp3" in formats:
        # Si tuvimos el nombre esperado, construir rutas; si no, buscar archivo .mp4 más reciente en outdir
        mp4_path = None
        if expected_path:
          base = os.path.splitext(expected_path)[0]
          mp4_path = f"{base}.mp4"

        if not mp4_path or not os.path.exists(mp4_path):
          # intentar encontrar el archivo mp4 más reciente en outdir
          candidates = [os.path.join(outdir, f) for f in os.listdir(outdir) if f.lower().endswith(".mp4")]
          if candidates:
            mp4_path = max(candidates, key=os.path.getmtime)

        if mp4_path and os.path.exists(mp4_path):
          mp3_path = os.path.splitext(mp4_path)[0] + ".mp3"
          ff_cmd = ["ffmpeg", "-y", "-i", mp4_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", mp3_path]
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
          # No se encontró el archivo mp4 resultante
          self.output.emit("No se pudo localizar el archivo MP4 resultante para extraer MP3.")

      self.finished.emit(last_ret)
    except FileNotFoundError:
      self.error.emit("yt-dlp no encontrado. Instale yt-dlp en el PATH.")
    except Exception as e:
      self.error.emit(str(e))

  @Slot()
  def stop(self) -> None:
    self._stopped = True
    if self._process:
      try:
        self._process.terminate()
      except Exception:
        pass
