import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from rich.console import Console

from . import export, report
from .albums import AlbumFinder
from .api import Client, Setlist, SetlistFMError, only_band, parse_all
from .cache import SetlistCache
from .config import (
    CACHE_FILE, CMD, DATE_FORMAT, DEFAULT_CONFIG, DESCRIPTION, SETLIST_CACHE_DIR, load_config, output_dir,
    safe_filename,
)
from .songs import find_song, song_key

console = Console()


# ---------------------------------------------------------------- helpers

def find_albums(setlist: Setlist, country: str) -> list[str | None]:
    """Album de cada cancion (iTunes). Si iTunes falla, sigue sin albums."""
    finder = AlbumFinder(country, CACHE_FILE)
    albums: list[str | None] = []
    try:
        with console.status("[dim]Buscando álbumes...[/dim]", spinner="dots") as status:
            for i, song in enumerate(setlist.songs, start=1):
                status.update(f"[dim]Buscando álbumes ({i}/{len(setlist.songs)}): {song.title}[/dim]")
                albums.append(finder.song_album(song.title, setlist.artist, song.cover))
    except requests.RequestException as exc:
        console.print(f"[yellow]No se pudo consultar iTunes ({exc.__class__.__name__}); "
                      f"se continúa sin álbumes.[/yellow]")
    finally:
        finder.save()
    return albums + [None] * (len(setlist.songs) - len(albums))


def save_json(data: dict, target: Path, default_name: str) -> Path:
    """target puede ser un archivo .json o una carpeta (se usa default_name)."""
    path = target if target.suffix.lower() == ".json" else target / f"{safe_filename(default_name)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    console.print(f"[green]✔ Guardado en[/green] {path}", soft_wrap=True)
    return path


def print_json(data: dict) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- comandos

def cmd_setlist(client: Client, config: dict, band: str, on: date, as_json: bool, out: Path | None,
                albums_on: bool) -> int:
    with console.status(f"[dim]Buscando {band} el {on.strftime(DATE_FORMAT)}...[/dim]", spinner="dots"):
        setlists = client.search_all(band, on=on)
    if not setlists:
        console.print(f"[red]No se encontró ningún setlist de[/red] [bold]{band}[/bold] "
                      f"[red]el[/red] {on.strftime(DATE_FORMAT)}")
        return 1

    if len(setlists) == 1:
        setlist = setlists[0]
    elif as_json or not sys.stdin.isatty():
        setlist = setlists[0]
        console.print(f"[yellow]{len(setlists)} setlists en esa fecha; se usa el primero "
                      f"({setlist.title}).[/yellow]", soft_wrap=True)
    else:
        setlist = report.ask_setlist(console, setlists)

    albums = find_albums(setlist, config["ITUNES_COUNTRY"]) if albums_on else [None] * len(setlist.songs)
    data = export.playlist_json(setlist, albums, config["PRIVACY"])
    if as_json:
        print_json(data)
    else:
        report.render_setlist(console, setlist, albums)
    if out is not None:
        save_json(data, out, data["name"])
    return 0


def years_label(years: tuple[int, int]) -> str:
    """(2026, 2026) -> '2026'; (2020, 2026) -> '2020-2026'"""
    return str(years[0]) if years[0] == years[1] else f"{years[0]}-{years[1]}"


def fetch_years(cache: SetlistCache, band: str, years: tuple[int, int], refresh: bool) -> list[Setlist]:
    """Setlists de la banda en el rango, del mas reciente al mas antiguo (cada año sale de la cache si sigue
    vigente)."""
    raw: list[dict] = []
    with console.status("[dim]Buscando...[/dim]", spinner="dots") as status:
        for year in range(years[1], years[0] - 1, -1):
            status.update(f"[dim]Buscando conciertos de {band} en {year}...[/dim]")
            raw.extend(cache.year(band, year, refresh))
    setlists = only_band(parse_all(raw), band)
    return sorted(setlists, key=lambda s: s.date, reverse=True)


def cmd_year(cache: SetlistCache, band: str, years: tuple[int, int], as_json: bool, out: Path | None) -> int:
    # El listado siempre pide los datos a la API (y de paso actualiza la cache que usa -s)
    setlists = fetch_years(cache, band, years, refresh=True)
    label = years_label(years)
    if not setlists:
        console.print(f"[red]No se encontraron conciertos de[/red] [bold]{band}[/bold] [red]en[/red] {label}")
        return 1
    band = setlists[0].artist or band   # nombre como lo escribe setlist.fm ("gorillaz" -> "Gorillaz")
    data = export.year_json(band, label, setlists)
    if as_json:
        print_json(data)
    else:
        report.render_year(console, band, label, setlists)
    if out is not None:
        save_json(data, out, f"{band} {label}")
    return 0


def cmd_song(cache: SetlistCache, band: str, song: str, years: tuple[int, int], as_json: bool, out: Path | None,
             refresh: bool) -> int:
    setlists = fetch_years(cache, band, years, refresh)
    label = years_label(years)
    if not setlists:
        console.print(f"[red]No se encontraron conciertos de[/red] [bold]{band}[/bold] [red]en[/red] {label}")
        return 1
    band = setlists[0].artist or band
    search = find_song(setlists, song)
    data = export.song_json(band, label, search)
    if as_json:
        print_json(data)
    else:
        report.render_song(console, band, label, search)
    if cache.downloaded:
        console.print(f"[dim]Años descargados de la API: {cache.downloaded} (peticiones: {cache.client.requests}); "
                      f"el resto salió de la caché.[/dim]")
    if out is not None:
        save_json(data, out, f"{band} {song} {label}")
    return 0


# ---------------------------------------------------------------- entrada

HELP_EPILOG = f"""
modos:
  {CMD} -b BANDA -d MM/DD/YYYY          setlist del concierto en esa fecha (canción / álbum)
  {CMD} -b BANDA -y AÑOS                conciertos de la banda en ese año o rango
  {CMD} -b BANDA -s TEXTO -y AÑOS       conciertos donde se tocó una canción que contiene TEXTO
                                        (-y es obligatorio: la API no busca por canción y hay que
                                        revisar los setlists de cada año)

  AÑOS: un año (2026) o un rango (2020-2026)

opciones:
  --json                         imprime el resultado como JSON en stdout (mensajes a stderr).
                                 Con -d es el formato de playlist de yt-music-playlist
  -o, --out [RUTA]               guarda el JSON en un archivo. RUTA puede ser un .json o una
                                 carpeta; sin RUTA usa OUTPUT_DIR de la configuración
  --no-album                     no busca el álbum de cada canción (más rápido)
  --refresh                      con -s: vuelve a pedir todos los años a la API (ignora la caché)
  -c, --config ARCHIVO           usar otro settings.json

caché de -s: cache\\setlists\\<banda>\\<año>.json. El año actual se vuelve a pedir cada 6 h, el
anterior cada 7 días y los demás no caducan. -y siempre pide los datos y actualiza la caché.

ejemplos:
  {CMD} -b "Gorillaz" -d "11/20/2026"
  {CMD} -b "Gorillaz" -d "11/20/2026" --json
  {CMD} -b "Gorillaz" -d "11/20/2026" -o "Z:\\dev\\py\\python-labs\\yt-music-playlist\\Inputs"
  {CMD} -b "Gorillaz" -y 2026
  {CMD} -b "Gorillaz" -y 2024-2026 --json
  {CMD} -b "Gorillaz" -s "Clint Eastwood" -y 2026
  {CMD} -b "Gorillaz" -s "eastwood" -y 2018-2026 --json
"""
MAX_YEARS = 30   # evita un rango por error (1900-2026) que gaste el limite diario de la API


def parse_date(text: str) -> date:
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"fecha inválida '{text}': usa MM/DD/YYYY (p. ej. 11/20/2026)")


def parse_years(text: str) -> tuple[int, int]:
    """'2026' -> (2026, 2026); '2020-2026' -> (2020, 2026)."""
    parts = [p.strip() for p in text.split("-")]
    if not (1 <= len(parts) <= 2 and all(p.isdigit() and len(p) == 4 for p in parts)):
        raise argparse.ArgumentTypeError(f"año inválido '{text}': usa YYYY o YYYY-YYYY (p. ej. 2026 o 2020-2026)")
    first, last = sorted(int(p) for p in (parts * 2)[:2])
    if last - first + 1 > MAX_YEARS:
        raise argparse.ArgumentTypeError(f"rango demasiado grande '{text}': máximo {MAX_YEARS} años")
    return first, last


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=CMD, description=DESCRIPTION, epilog=HELP_EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-b", "--band", required=True, metavar="BANDA", help="nombre de la banda o artista")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-d", "--date", type=parse_date, metavar="MM/DD/YYYY", help="fecha del concierto")
    mode.add_argument("-y", "--year", type=parse_years, metavar="AÑOS",
                      help="año (2026) o rango (2020-2026): lista los conciertos, o el rango donde busca -s")
    parser.add_argument("-s", "--song", metavar="TEXTO",
                        help="conciertos donde se tocó una canción que contiene TEXTO (requiere -y)")
    parser.add_argument("--json", action="store_true", help="imprime el resultado como JSON (mensajes a stderr)")
    parser.add_argument("-o", "--out", nargs="?", const="", metavar="RUTA",
                        help="guarda el JSON en RUTA (.json o carpeta); sin RUTA usa OUTPUT_DIR")
    parser.add_argument("--no-album", action="store_true", help="no buscar el álbum de cada canción")
    parser.add_argument("--refresh", action="store_true", help="con -s: ignorar la caché de setlists")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="archivo JSON de configuración")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.song is not None:
        if not args.year:
            parser.error("-s/--song requiere -y con un año o rango (p. ej. -y 2020-2026)")
        if not song_key(args.song):
            parser.error("-s/--song no puede estar vacío")
    if args.json:
        # stdout queda solo para el JSON; progreso, avisos y errores van a stderr.
        console.file = sys.stderr
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        console.print(f"[bold red]Error de configuración:[/bold red] {exc}")
        console.print(f"[dim]Tip: copia config\\settings.example.json a config\\settings.json y pon tu API key "
                      f"(https://www.setlist.fm/settings/api).[/dim]", soft_wrap=True)
        return 1

    out = None if args.out is None else (Path(args.out) if args.out else output_dir(config))
    client = Client(config["API_KEY"], config["API_URL"], config["LANGUAGE"])
    cache = SetlistCache(client, SETLIST_CACHE_DIR)
    band = " ".join(args.band.split())
    try:
        if args.date:
            return cmd_setlist(client, config, band, args.date, args.json, out, not args.no_album)
        if args.song is not None:
            return cmd_song(cache, band, " ".join(args.song.split()), args.year, args.json, out, args.refresh)
        return cmd_year(cache, band, args.year, args.json, out)
    except SetlistFMError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return 1
    except requests.RequestException as exc:
        console.print(f"[bold red]Error de red:[/bold red] {exc.__class__.__name__}: {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado.[/yellow]")
        return 130
    except EOFError:
        console.print("\n[red]No hay entrada interactiva disponible.[/red]")
        return 1
