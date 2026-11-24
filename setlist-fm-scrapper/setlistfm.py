"""SetList FM Scrapper: busca setlists de conciertos en setlist.fm (API oficial).

Uso:
    python setlistfm.py -b "Gorillaz" -d "11/20/2026"            setlist del concierto (cancion / album)
    python setlistfm.py -b "Gorillaz" -d "11/20/2026" --json     playlist JSON para yt-music-playlist
    python setlistfm.py -b "Gorillaz" -d "11/20/2026" -o         guarda el JSON en OUTPUT_DIR
    python setlistfm.py -b "Gorillaz" -y 2026                    conciertos de la banda en ese año
    python setlistfm.py -b "Gorillaz" -y 2026 --json             la lista como JSON
    python setlistfm.py -h                                       ayuda con todos los comandos
"""
import sys

from setlistfm_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
