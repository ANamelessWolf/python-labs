"""TMDB Updates: revisa tu biblioteca de series contra The Movie Database.

Uso:
    python tmdb.py                     menu interactivo
    python tmdb.py scan [--full]       escanea la biblioteca
    python tmdb.py scan -sn "Serie"    escanea una sola serie
    python tmdb.py status -tv          resumen de todas las series
    python tmdb.py status -sn "Serie"  detalle de una serie
    python tmdb.py updates             episodios faltantes / por salir
    python tmdb.py list                lista de series
    python tmdb.py fix -sn "Serie"     recarga la serie con su tmdbId (--id N / --search)
"""
import sys

from tmdb_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
