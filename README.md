# YT Downloader

Aplicación de escritorio para descargar videos o audio desde YouTube con interfaz gráfica desarrollada en Python usando PySide6.

## Descripción

YT Downloader permite:

- Descargar videos en formato MP4
- Extraer audio en formato MP3
- Elegir la carpeta de destino
- Ver el progreso del proceso en una interfaz gráfica
- Ejecutarse como aplicación de escritorio en Windows y Linux

## Requisitos

- Python 3.10 o superior
- `pip` actualizado
- `ffmpeg` instalado y disponible en el PATH
- `deno` instalado y disponible en el PATH

## Instalación

### 1) Clonar el repositorio

```bash
git clone https://github.com/yumikodev/yt-music-downloader.git
cd yt-downloader
```

### 2) Crear entorno virtual

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Instalación de ffmpeg

`ffmpeg` es necesario para convertir o extraer audio, especialmente al trabajar con MP3 o cuando se convierte entre formatos.

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y ffmpeg
```

Verificar:

```bash
ffmpeg -version
```

### Windows

Puedes instalarlo con `winget` o `choco`:

```powershell
winget install Gyan.Dev.FFmpeg
```

o bien:

```powershell
choco install ffmpeg -y
```

Verificar:

```powershell
ffmpeg -version
```

## Instalación de Deno

El proyecto usa `deno` como dependencia auxiliar para algunos procesos del flujo de trabajo y para los binarios empaquetados.

### Linux/macOS

```bash
curl -fsSL https://deno.land/install.sh | sh
```

Luego agrega el binario al PATH si tu shell lo requiere:

```bash
export PATH="/home/$USER/.deno/bin:$PATH"
```

Verificar:

```bash
deno --version
```

### Windows

```powershell
winget install deno
```

o bien:

```powershell
choco install deno -y
```

Verificar:

```powershell
deno --version
```

## Ejecutar la aplicación

Desde la raíz del proyecto:

```bash
python main.py
```

La ventana principal te permitirá:

- ingresar la URL de YouTube
- seleccionar MP3 o MP4
- elegir la carpeta de descarga
- iniciar o detener la descarga
- ver el registro del proceso

## Estructura del proyecto

```text
.
├── main.py
├── requirements.txt
├── services/
│   ├── download_worker.py
│   └── main_window.py
├── vendor/
│   ├── ffmpeg
│   └── deno
└── .github/workflows/build.yml
```

## Compilar el binario

El proyecto incluye configuración de PyInstaller para generar ejecutables.

### Linux

```bash
pyinstaller --noconfirm --clean --windowed --onefile --name yt-downloader \
  --add-data "services:services" \
  --add-binary "vendor/ffmpeg:." \
  --add-binary "vendor/ffprobe:." \
  --add-binary "vendor/deno:." \
  --hidden-import yt_dlp main.py
```

### Windows (PowerShell)

```powershell
pyinstaller --noconfirm --clean --windowed --onefile --name yt-downloader `
  --add-data 'services;services' `
  --add-binary 'vendor\ffmpeg.exe;.' `
  --add-binary 'vendor\ffprobe.exe;.' `
  --add-binary 'vendor\deno.exe;.' `
  --hidden-import yt_dlp main.py
```

> Se usa `--windowed` para que la aplicación se ejecute sin mostrar una terminal de consola en Windows.

## Nota importante

- La herramienta depende de `ffmpeg` para las conversiones de audio y video.
- El proyecto usa `yt-dlp` para interactuar con YouTube.
- El binario interno debe incluir `ffmpeg` y `deno` en la carpeta `vendor` o en el PATH según el caso.

## Licencia

Este proyecto está bajo la [licencia MIT](LICENSE)
