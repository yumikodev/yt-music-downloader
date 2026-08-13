import os
import sys


def configure_ssl_env() -> str:
  cert_candidates = []

  try:
    import certifi
    cert_candidates.append(certifi.where())
  except ModuleNotFoundError:
    pass

  cert_candidates.extend([
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/ssl/cert.pem",
    "/etc/pki/tls/certs/ca-bundle.crt",
  ])

  for cert_path in cert_candidates:
    if not cert_path or not os.path.exists(cert_path):
      continue

    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["SSL_CERT_DIR"] = os.path.dirname(cert_path)
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path
    os.environ["CURL_CA_BUNDLE"] = cert_path
    return cert_path

  return ""


configure_ssl_env()

from PySide6.QtWidgets import QApplication
from services.main_window import MainWindow

if __name__ == "__main__":
  app = QApplication(sys.argv)
  win = MainWindow()
  win.show()
  sys.exit(app.exec())
