from typing import Any 
from yt_dlp import YoutubeDL

def credits():
  print("############################")
  print("# YouTube Music Downloader #")
  print("# Created by: Edwin Jibaja #")
  print("############################")

class Downloader:
  songs_list: list[str] = []

  def __init__(self) -> None:
    credits()
    self.options_handler()

  def options_handler(self) -> None:
    print("------------------------------")
    print("[1] Agregar una canción de YT")
    print("[2] Descargar canciones")
    print("[3] Ver lista de canciones")
    print("[4] Eliminar canción de la lista")
    print("[0] Salir")
    print("------------------------------")

    option = int(input("Selecione la acción a realizar: "))

    match option:
      case 0:
        return
      case 1:
        self.append_new_url()
        self.options_handler()
      case 2:
        self.ytdlp_process()
      case 3:
        self.view_songs_list()
        self.options_handler() 
      case 4:
        self.remove_song()
        self.options_handler()
      case _:
        print("¡Debes ingresar una opción válida!")
        self.options_handler()

  def view_songs_list(self) -> None:
    if len(self.songs_list) == 0:
      print("La lista de canciones está vacía. Nada por hacer.")
      return

    for idx, song in enumerate(self.songs_list):
      print(f"[#{idx}] {song}")

  def remove_song(self) -> None:
    idx = int(input("Ingrese el índice de la canción en la lista: "))

    if 0 <= idx < len(self.songs_list):
      del self.songs_list[idx]
    else:
      print("¡El índice no existe en la lista!")
      return self.remove_song()  


  def append_new_url(self) -> None:
    url = input("Ingrese la URL: ")
    self.songs_list.append(url);

  def ytdlp_process(self) -> None:
    songs_list_count = len(self.songs_list)
    print(f"Enlaces de Youtube: {songs_list_count}")

    if songs_list_count == 0:
      print("No se agregaron canciones. Nada por hacer.")
      return

    print("Iniciando el servicio de yt-dlp")

    options: Any = {
      "format": "bestaudio/best",
      "outtmpl": "downloads/%(title)s.%(ext)s",
      "postprocessors": [
        {
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": "192"
        }
      ],
    }

    try:
      with YoutubeDL(options) as ydl:
        ydl.download(self.songs_list)

      print("Canciones descargadas con éxito")
    except:
      option = input("¿Intentar de nuevo [Y/n]? ").lower() or "y"
      if option == ("y" or "yes"):
        self.ytdlp_process()
      else:
        return  

if __name__ == "__main__":
  Downloader()    

