import os
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
  QLabel,
  QPushButton,
  QVBoxLayout,
  QWidget,
  QLineEdit,
  QHBoxLayout,
  QCheckBox,
  QListWidget,
  QListWidgetItem,
  QFileDialog,
  QMessageBox,
)
from services.download_worker import DownloadWorker

class MainWindow(QWidget):
  def __init__(self) -> None:
    super().__init__()
    self.setWindowTitle("YT Downloader")
    self.setFixedSize(500, 600)

    self.worker: DownloadWorker = DownloadWorker()
    self.thread: QThread = QThread()
    self.worker.moveToThread(self.thread)
    self.thread.start()

    self._setup_ui()
    self._connect_signals()

    self._running = False

  def _setup_ui(self) -> None:
    main_layout = QVBoxLayout()

    # URL input
    label = QLabel("Enlace de Youtube:")
    main_layout.addWidget(label)
    self.url_input = QLineEdit()
    self.url_input.setPlaceholderText("Insertar enlace de Youtube...")
    main_layout.addWidget(self.url_input)

    # Format checkboxes
    format_layout = QHBoxLayout()
    self.mp3_cb = QCheckBox("MP3 (Audio)")
    self.mp4_cb = QCheckBox("MP4 (Vídeo)")
    self.mp3_cb.setChecked(True)
    format_layout.addWidget(self.mp3_cb)
    format_layout.addWidget(self.mp4_cb)
    main_layout.addLayout(format_layout)

    # Output folder selector
    folder_layout = QHBoxLayout()
    label = QLabel("Carpeta de descargas:")
    main_layout.addWidget(label)
    self.folder_input = QLineEdit()
    # Default to the user's Downloads folder
    self.default_outdir = os.path.join(os.path.expanduser("~"), "Downloads")
    self.folder_input.setText(self.default_outdir)
    self.folder_input.setPlaceholderText(f"Carpeta de descargas (por defecto: {self.default_outdir})")
    browse_btn = QPushButton("Examinar")
    browse_btn.clicked.connect(self.browse_folder)
    folder_layout.addWidget(self.folder_input)
    folder_layout.addWidget(browse_btn)
    main_layout.addLayout(folder_layout)

    # Log list
    label = QLabel("Registro de actividad:")
    main_layout.addWidget(label)
    self.log_list = QListWidget()
    main_layout.addWidget(self.log_list)

    # Footer buttons
    footer_layout = QHBoxLayout()
    self.start_btn = QPushButton("Comenzar")
    self.stop_btn = QPushButton("Detener")
    self.close_btn = QPushButton("Cerrar")

    footer_layout.addWidget(self.start_btn)
    footer_layout.addWidget(self.stop_btn)
    footer_layout.addWidget(self.close_btn)
    main_layout.addLayout(footer_layout)

    self.setLayout(main_layout)

    # Initial states
    self.stop_btn.setEnabled(False)

  def _connect_signals(self) -> None:
    self.start_btn.clicked.connect(self.on_start)
    self.stop_btn.clicked.connect(self.on_stop)
    self.close_btn.clicked.connect(self.on_close)

    self.worker.started.connect(self.on_worker_started)
    self.worker.output.connect(self.on_worker_output)
    self.worker.finished.connect(self.on_worker_finished)
    self.worker.error.connect(self.on_worker_error)

  def browse_folder(self) -> None:
    dirpath = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", self.default_outdir)
    if dirpath:
      self.folder_input.setText(dirpath)

  def _append_log(self, text: str) -> None:
    item = QListWidgetItem(text)
    self.log_list.addItem(item)
    self.log_list.scrollToBottom()

  def _get_outdir(self) -> str:
    d = self.folder_input.text().strip() or self.default_outdir
    if not os.path.exists(d):
      try:
        os.makedirs(d, exist_ok=True)
      except Exception:
        pass
    return d

  def _get_formats(self) -> list:
    fmts = []
    if self.mp3_cb.isChecked():
      fmts.append("mp3")
    if self.mp4_cb.isChecked():
      fmts.append("mp4")
    return fmts

  def on_start(self) -> None:
    url = self.url_input.text().strip()
    if not url:
      QMessageBox.warning(self, "URL vacía", "Por favor ingrese un enlace de Youtube.")
      return

    fmts = self._get_formats()
    if not fmts:
      QMessageBox.warning(self, "Formato", "Seleccione al menos un formato (MP3 o MP4).")
      return

    outdir = self._get_outdir()
    self.log_list.clear()
    self._append_log("Iniciando descarga...")

    class Starter(QObject):
      trigger = Signal(str, list, str)

    self._starter = Starter()
    self._starter.trigger.connect(self.worker.start_download)
    self._starter.trigger.emit(url, fmts, outdir)

    self._running = True
    self.start_btn.setEnabled(False)
    self.stop_btn.setEnabled(True)

  def on_stop(self) -> None:
    if not self._running:
      return
    self._append_log("Solicitando detener...")
    self.worker.stop()
    self.stop_btn.setEnabled(False)
    
  def on_close(self) -> None:
    if self._running:
      reply = QMessageBox.question(
        self,
        "Salir",
        "Hay una descarga en curso. ¿Desea detenerla y cerrar?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
      )
      if reply == QMessageBox.StandardButton.No:
        return
      self.worker.stop()

    self.thread.quit()
    self.thread.wait()
    self.close()

  def on_worker_started(self) -> None:
    self._append_log("Worker iniciado")

  def on_worker_output(self, line: str) -> None:
    self._append_log(line)

  def on_worker_finished(self, code: int) -> None:
    self._append_log(f"Proceso terminado con código {code}")
    self._running = False
    self.start_btn.setEnabled(True)
    self.stop_btn.setEnabled(False)
    if code == 0:
      QMessageBox.information(self, "Éxito", "Descarga completada correctamente.")
    else:
      QMessageBox.warning(self, "Terminado con errores", f"El proceso terminó con código {code}.")

  def on_worker_error(self, msg: str) -> None:
    self._append_log(f"Error: {msg}")
    QMessageBox.critical(self, "Error", msg)
    self._running = False
    self.start_btn.setEnabled(True)
    self.stop_btn.setEnabled(False)