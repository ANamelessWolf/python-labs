import argparse
import calendar
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn, DownloadColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn,
    TimeRemainingColumn, TransferSpeedColumn,
)
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from . import export, movielib, report
from .config import LIBRARY_FILE, ConfigError, Settings, load_settings
from .movie import (
    Genre, MoveResult, MovieError, find_genre, format_movie, list_genres, move_folder, repair_windows_argv, resolve_folder,
    safe_genre_name,
)
from .scanner import (
    ERROR, base_record, discover_series, evaluate, pick_match, scan_local_series, strip_year,
)
from .store import Library, find_by_name
from .tmdb_client import TmdbClient, TmdbError

console = Console(highlight=False)
SCAN_WORKERS = 6


class AppError(Exception):
    pass


def months_ago(d: date, months: int) -> date:
    year_offset, month_index = divmod(d.month - 1 - months, 12)
    year, month = d.year + year_offset, month_index + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def interactive() -> bool:
    return sys.stdin.isatty()


def choose(items: list, label_of, what: str, name: str):
    """Regresa un elemento; si hay varios coincidentes pregunta cual (solo en modo interactivo)."""
    if not items:
        raise AppError(f"No encontré ninguna serie que coincida con '{name}'.")
    if len(items) == 1:
        return items[0]
    console.print(f"[yellow]Hay {len(items)} {what} que coinciden con '{name}':")
    for i, item in enumerate(items, start=1):
        console.print(f"  [bold]{i}[/]. {label_of(item)}")
    if not interactive():
        raise AppError("Usa un nombre más específico.")
    index = IntPrompt.ask("Elige", choices=[str(i) for i in range(1, len(items) + 1)], show_choices=False)
    return items[index - 1]


def make_client(settings: Settings) -> TmdbClient:
    return TmdbClient(settings.api_key, settings.base_url, settings.language)


def process_series(client: TmdbClient, path: Path, library_root: Path, tmdb_id: int | None,
                   existing: dict | None, today: date, max_season: int | None = None) -> dict:
    """Escanea una carpeta y la cruza con TMDB. Usa el tmdbId guardado si existe."""
    try:
        local = scan_local_series(path, library_root)
    except OSError as exc:
        record = dict(existing) if existing else {"folder": path.name, "path": str(path),
                                                   "library": str(library_root), "seasons": [], "tag": ERROR}
        record["error"] = f"No se pudo leer la carpeta: {exc}"
        return record

    try:
        if tmdb_id is None:
            match = pick_match(client.search_tv(local.title, local.year), local.title, local.year)
            if match is None:
                record = base_record(local, max_season)
                record["error"] = f"Sin resultados en TMDB para '{local.title}'. Asigna tmdbId y usa 'fix'."
                return record
            tmdb_id = match["id"]
        return evaluate(local, client.get_tv(tmdb_id), today, max_season)
    except TmdbError as exc:
        # Un fallo de red no debe borrar lo que ya sabiamos de la serie
        record = dict(existing) if existing and existing.get("seasons") else base_record(local, max_season)
        record["tmdbId"] = tmdb_id
        if not record.get("seasons"):
            record["tag"] = ERROR
        record["error"] = str(exc)
        return record


# ---------------------------------------------------------------- comandos

def cmd_scan(settings: Settings, name: str | None = None, full: bool = False, as_json: bool = False) -> dict | None:
    library = Library()
    today = date.today()
    folders, unavailable = discover_series(settings.tv_paths)
    configured = {str(p) for p in settings.tv_paths}
    available = configured - {str(p) for p in unavailable}

    removed: list[str] = []
    if name:
        matches = find_by_name(folders, name, lambda f: (f[0].name, (library.series.get(str(f[0])) or {}).get("tmdbName") or ""))
        targets = [choose(matches, lambda f: str(f[0]), "carpetas", name)]
    else:
        targets = folders
        present = {str(p) for p, _ in folders}
        for key, series in list(library.series.items()):
            if key not in present and (series["library"] in available or series["library"] not in configured):
                removed.append(key)
                del library.series[key]

    jobs, skipped = [], 0
    for path, root in targets:
        existing = library.series.get(str(path))
        if existing and existing.get("finished") and not full and not name:
            skipped += 1
            continue
        jobs.append((path, root, existing))

    client = make_client(settings)
    scanned: list[dict] = []
    progress = Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(),
                        MofNCompleteColumn(), TimeElapsedColumn(), console=console, transient=True)
    try:
        with progress, ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
            task = progress.add_task("Escaneando", total=len(jobs))
            futures = {
                pool.submit(process_series, client, path, root,
                            (existing or {}).get("tmdbId"), existing, today,
                            (existing or {}).get("maxSeason")): path
                for path, root, existing in jobs
            }
            for future in as_completed(futures):
                record = future.result()
                library.series[record["path"]] = record
                scanned.append(record)
                progress.update(task, advance=1, description=f"Escaneando · {record['folder'][:40]}")
    finally:
        library.save()

    if as_json:
        return export.scan_result(library, scanned, skipped, removed, unavailable, today, detail=bool(name))
    report.render_scan_result(console, scanned, skipped, removed, unavailable)
    if name and scanned:
        console.print()
        report.render_series_detail(console, scanned[0], today)


def require_data(library: Library) -> None:
    if not library.series:
        raise AppError(f"No hay datos todavía ({LIBRARY_FILE}). Ejecuta primero: TMDB scan")


def find_series(library: Library, name: str) -> dict:
    require_data(library)
    return choose(library.find(name), lambda s: f"{s['folder']}  [grey50]({s['library']})", "series", name)


def cmd_status(name: str | None = None, as_json: bool = False) -> dict | None:
    library = Library()
    today = date.today()
    if name:
        series = find_series(library, name)
        if as_json:
            return export.status_series(library, series, today)
        report.render_series_detail(console, series, today)
    else:
        require_data(library)
        if as_json:
            return export.status_tv(library, today)
        report.render_tv_status(console, library)
    return None


def cmd_updates(as_json: bool = False) -> dict | None:
    library = Library()
    require_data(library)
    today = date.today()
    start, end = months_ago(today, 2), today + timedelta(days=7)
    if as_json:
        return export.updates(library, today, start, end)
    report.render_updates(console, library, today, start, end)
    return None


def cmd_missing(name: str | None = None, as_json: bool = False) -> dict | None:
    library = Library()
    if name:
        series_list = [find_series(library, name)]
    else:
        require_data(library)
        series_list = library.sorted_series()
    if as_json:
        return export.missing(library, series_list, date.today())
    report.render_missing(console, library, series_list, date.today())
    return None


def cmd_list(as_json: bool = False) -> dict | None:
    library = Library()
    require_data(library)
    if as_json:
        return export.series_list(library)
    report.render_list(console, library)
    return None


def cmd_fix(settings: Settings, name: str, tmdb_id: int | None = None, search: bool = False,
            as_json: bool = False) -> dict | None:
    library = Library()
    series = find_series(library, name)
    client = make_client(settings)

    if search:
        tmdb_id = pick_from_search(client, series)
    tmdb_id = tmdb_id or series.get("tmdbId")
    if not tmdb_id:
        raise AppError(f"'{series['folder']}' no tiene tmdbId. Edita {LIBRARY_FILE}, o usa --id N o --search.")

    with console.status(f"Consultando TMDB {tmdb_id}…"):
        record = process_series(client, Path(series["path"]), Path(series["library"]), int(tmdb_id),
                                None, date.today(), series.get("maxSeason"))
    if record.get("error"):
        raise AppError(f"No se aplicó el fix, la serie queda como estaba: {record['error']}")
    library.series[record["path"]] = record
    library.save(touch_scan=False)
    message = f"{series['folder']} actualizado con TMDB {tmdb_id}."
    if as_json:
        return export.series_change("fix", library, record, message, date.today())
    console.print(f"[green]✔ {message}\n")
    report.render_series_detail(console, record, date.today())
    return None


def cmd_unfollow(settings: Settings, name: str, max_season: int | None, as_json: bool = False) -> dict | None:
    """Limita la serie hasta max_season (None = seguir todas otra vez) y la vuelve a escanear."""
    if max_season is not None and max_season < 1:
        raise AppError("La temporada debe ser 1 o mayor.")
    library = Library()
    series = find_series(library, name)
    if not series.get("tmdbId"):
        raise AppError(f"'{series['folder']}' no tiene tmdbId. Usa primero: TMDB fix -sn \"{series['folder']}\" --search")

    with console.status(f"Actualizando {series['folder']}…"):
        record = process_series(make_client(settings), Path(series["path"]), Path(series["library"]),
                                int(series["tmdbId"]), series, date.today(), max_season)
    if record.get("error"):
        raise AppError(f"No se aplicó el cambio, la serie queda como estaba: {record['error']}")
    library.series[record["path"]] = record
    library.save(touch_scan=False)
    if max_season is None:
        message = f"{series['folder']}: se vuelven a revisar todas las temporadas."
    else:
        message = (f"{series['folder']}: solo se revisa hasta la temporada {max_season}; "
                   f"las posteriores se ignoran.")
    if as_json:
        return export.series_change("unfollow", library, record, message, date.today())
    console.print(f"[green]✔ {message}\n")
    report.render_series_detail(console, record, date.today())
    return None


def cmd_movie(settings: Settings, directory: str, name: str, year: int | None,
              as_json: bool = False) -> dict | None:
    """Renombra la carpeta a 'Nombre (Año)' y guarda el poster de TMDB como folder.jpg/png."""
    if year is not None and not 1870 <= year <= 2200:
        raise AppError(f"Año inválido: {year}")
    folder = resolve_folder(directory, settings.movie_paths)
    with console.status("Buscando en TMDB…") as spinner:
        result = format_movie(make_client(settings), folder, name.strip(), year, spinner.update)
    for warning in result.warnings:
        console.print(f"[yellow]⚠ {warning}")
    if as_json:
        return result.to_json()
    console.print(f"[green]✔ TMDB {result.tmdb_id}: {result.title}" + (f" ({result.year})" if result.year else ""))
    if result.renamed:
        console.print(f"  [grey50]{result.previous_path.name}[/] → [bold]{result.path.name}")
    else:
        console.print(f"  [grey50]La carpeta ya se llamaba[/] [bold]{result.path.name}")
    if result.poster:
        console.print(f"  [grey50]Poster:[/] {result.poster.name}")
    console.print(f"  {result.path}")
    return None


def ask_genre(genres: list[Genre], multiple_roots: bool) -> str:
    """Muestra los géneros en columnas y regresa el nombre elegido (número o un nombre nuevo)."""
    if not interactive():
        raise AppError("Falta -g GENERO (no hay consola interactiva para elegirlo).")
    labels = [f"[bold bright_blue]{i:>2}[/] {g.name}" + (f" [grey50]({g.path.parent})" if multiple_roots else "")
              for i, g in enumerate(genres, start=1)]
    columns = 3 if len(labels) > 12 else 1
    rows = (len(labels) + columns - 1) // columns
    grid = Table.grid(padding=(0, 3))
    for row in range(rows):
        grid.add_row(*[labels[row + col * rows] if row + col * rows < len(labels) else ""
                       for col in range(columns)])
    console.print(Panel(grid, title="[bold]Géneros", border_style="bright_blue", expand=False))
    while True:
        answer = Prompt.ask("Número de género, o escribe un nombre nuevo").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(genres):
            return genres[int(answer) - 1].name
        if answer and not answer.isdigit():
            return answer
        console.print("[red]Opción inválida.")


def movie_roots(settings: Settings) -> list[Path]:
    if not settings.movie_paths:
        raise AppError("MEDIA.MOVIE_PATHS está vacío en config/settings.json.")
    roots = [r for r in settings.movie_paths if r.is_dir()]
    if not roots:
        raise AppError("No está disponible ninguna carpeta de MOVIE_PATHS: "
                       + ", ".join(str(r) for r in settings.movie_paths))
    return roots


def cmd_movie_list(settings: Settings, genre_name: str | None, as_json: bool = False, refresh: bool = False,
                   posters: bool = True, out: str | None = None) -> dict | None:
    """Lista películas y colecciones por género (recursivo), valida los nombres contra TMDB usando
    data/movies.json como cache y baja el poster a las carpetas que no lo tienen."""
    roots = movie_roots(settings)
    genres = list_genres(roots)
    if genre_name:
        exact = find_genre(genres, genre_name)
        wanted = genre_name.strip().lower()
        genres = [exact] if exact else [g for g in genres if wanted in g.name.lower()]
        if not genres:
            raise AppError(f"No existe el género '{genre_name}'.")

    with console.status("Leyendo carpetas…"):
        listing = [(g, movielib.scan_genre(g)) for g in genres]
    nodes = [n for _, items in listing for top in items for n in top.walk()]

    cache = movielib.MovieCache()
    client = make_client(settings)
    pending = [n for n in nodes if not n.error and cache.needs_lookup(n, refresh)]
    progress = Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(),
                        MofNCompleteColumn(), TimeElapsedColumn(), console=console, transient=True)
    try:
        if pending:
            # Primero las películas: las colecciones se validan con los tmdbId de las películas de adentro
            movies_first = [n for n in pending if n.kind == movielib.MOVIE]
            collections = [n for n in pending if n.kind == movielib.COLLECTION]
            with progress, ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
                task = progress.add_task("Validando con TMDB", total=len(pending))
                for batch in (movies_first, collections):
                    futures = {
                        (pool.submit(movielib.lookup_movie, client, n, cache.get(n)) if n.kind == movielib.MOVIE
                         else pool.submit(movielib.lookup_collection, client, n, cache.get(n),
                                          movielib.child_movie_ids(n, cache))): n
                        for n in batch
                    }
                    for future in as_completed(futures):
                        node = futures[future]
                        try:
                            cache.put(node, future.result())
                        except TmdbError as exc:
                            node.error = str(exc)
                        progress.update(task, advance=1, description=f"Validando · {node.name[:40]}")
        # Con -g solo se limpia ese género; sin -g, todo lo que esté bajo MOVIE_PATHS disponibles
        removed = cache.prune(nodes, [g.path for g in genres] if genre_name else roots, full=not genre_name)
        for genre, items in listing:
            cache.locate(genre, items)
        for node in nodes:
            movielib.apply_status(node, cache.get(node))
    finally:
        cache.save()

    to_download = [n for n in nodes if posters and movielib.wants_poster(n)]
    if to_download:
        with progress, ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
            task = progress.add_task("Bajando posters", total=len(to_download))
            for future in as_completed([pool.submit(movielib.download_poster, client, n) for n in to_download]):
                future.result()
                progress.advance(task)

    movies = [n for n in nodes if n.kind == movielib.MOVIE]
    counts = {status: sum(1 for n in movies if n.status == status)
              for status in (movielib.OK, movielib.RENAME, movielib.REVIEW, movielib.NOT_FOUND)}
    payload = {
        "command": "movie-list",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "cache": str(cache.path),
        "totalMovies": len(movies),
        "totalCollections": sum(1 for n in nodes if n.kind == movielib.COLLECTION),
        "totalGenres": len(listing),
        "status": counts,
        "removedFromCache": removed,
        "withoutPoster": sum(1 for n in nodes if not n.poster),
        "postersCreated": sum(1 for n in nodes if n.poster_created),
        "genres": [{"name": g.name, "path": str(g.path), "count": sum(i.movie_count for i in items),
                    "items": [i.to_json() for i in items]} for g, items in listing],
    }
    if out:
        out_path = Path(out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if as_json:
        return payload

    multiple_roots = len(roots) > 1
    for genre, items in listing:
        title = f"[bold bright_blue]{genre.name}[/] [grey50]({sum(i.movie_count for i in items)})"
        if multiple_roots:
            title += f" [grey50]{genre.path.parent}"
        tree = Tree(title, guide_style="grey50")
        for item in items:
            add_movie_node(tree, item)
        console.print(tree)

    summary = (f"[bold]{len(movies)}[/] películas · [bold]{payload['totalCollections']}[/] colecciones · "
               f"[bold]{len(listing)}[/] géneros\n[green]{counts['OK']} OK[/]")
    for status, style in ((movielib.RENAME, "yellow"), (movielib.REVIEW, "magenta"), (movielib.NOT_FOUND, "red")):
        if counts[status]:
            summary += f" · [{style}]{counts[status]} {STATUS_LABELS[status]}[/]"
    if payload["postersCreated"]:
        summary += f" · [green]{payload['postersCreated']} posters nuevos[/]"
    if payload["withoutPoster"]:
        summary += f" · [grey50]{payload['withoutPoster']} sin poster[/]"
    console.print()
    console.print(summary)
    if removed:
        console.print(f"[grey50]Quitadas del cache (ya no existen): {', '.join(removed)}")
    if out:
        console.print(f"[grey50]JSON exportado a[/] {Path(out).expanduser().resolve()}")
    return None


STATUS_LABELS = {"RENAME": "renombrar", "REVIEW": "revisar", "NOT_FOUND": "no están en TMDB"}


def add_movie_node(parent: Tree, node) -> None:
    e = node.entry or {}
    label = Text()
    if node.kind == movielib.COLLECTION:
        label.append(f"{node.name}", style="bold")
        label.append(f" ({node.movie_count})", style="grey50")
        if node.status == movielib.NOT_FOUND:
            label.append("  colección no encontrada", style="grey50")
        elif node.status == movielib.REVIEW:
            label.append(f"  ¿{e.get('title')}?", style="magenta")
    else:
        label.append(node.name)
        if node.status == movielib.RENAME:
            label.append(f"  → {node.suggested}", style="yellow")
        elif node.status == movielib.REVIEW:
            label.append(f"  ¿{node.suggested}?", style="magenta")
        elif node.status == movielib.NOT_FOUND:
            label.append("  no está en TMDB", style="red")
    if node.poster_created:
        label.append("  +poster", style="green")
    elif not node.poster:
        label.append("  sin poster", style="grey50")
    if node.error:
        label.append(f"  ✘ {node.error}", style="red")
    branch = parent.add(label)
    for child in node.children:
        add_movie_node(branch, child)


def cmd_movie_move(settings: Settings, directory: str, genre_name: str | None, as_json: bool = False) -> dict | None:
    """Mueve la carpeta de la película a MOVIE_PATHS/<género>; crea el género si no existe."""
    roots = movie_roots(settings)
    folder = resolve_folder(directory, [])
    genres = list_genres(roots)
    if not genre_name:
        genre_name = ask_genre(genres, len(roots) > 1)

    genre = find_genre(genres, genre_name)
    created = genre is None
    if created:
        name = safe_genre_name(genre_name)
        genre = Genre(name, roots[0] / name)

    target = genre.path / folder.name
    moved = os.path.normcase(folder.parent) != os.path.normcase(genre.path.resolve())
    if moved:
        if target.exists():
            raise AppError(f"Ya existe '{target}'.")
        if os.path.normcase(genre.path.resolve()).startswith(os.path.normcase(folder) + os.sep):
            raise AppError("No se puede mover una carpeta dentro de sí misma.")
        if created:
            genre.path.mkdir(parents=True, exist_ok=True)
            console.print(f"[yellow]Género nuevo:[/] {genre.path}")
        progress = Progress(TextColumn("[bold blue]Moviendo"), BarColumn(), DownloadColumn(),
                            TransferSpeedColumn(), TimeRemainingColumn(), console=console, transient=True)
        with progress:
            task = progress.add_task("mover", total=None, visible=False)
            move_folder(folder, target,
                        start=lambda total: progress.update(task, total=total, visible=True),
                        advance=lambda n: progress.advance(task, n))

    result = MoveResult(folder, target if moved else folder, genre, created and moved, moved)
    if as_json:
        return result.to_json()
    if moved:
        console.print(f"[green]✔ {folder.name}[/] → [bold]{genre.name}")
        console.print(f"  {result.path}")
    else:
        console.print(f"[yellow]'{folder.name}' ya está en {genre.name}.")
    return None


def pick_from_search(client: TmdbClient, series: dict) -> int:
    if not interactive():
        raise AppError("--search necesita una consola interactiva.")
    query = Prompt.ask("Buscar en TMDB", default=strip_year(series["folder"]))
    results = client.search_tv(query)[:10]
    if not results:
        raise AppError(f"Sin resultados para '{query}'.")
    table = Table(header_style="bold bright_blue")
    for col in ("#", "TMDB id", "Nombre", "Año", "País", "Resumen"):
        table.add_column(col)
    for i, r in enumerate(results, start=1):
        table.add_row(str(i), str(r["id"]), r.get("name", ""), (r.get("first_air_date") or "")[:4],
                      ",".join(r.get("origin_country", [])), (r.get("overview") or "")[:70])
    console.print(table)
    index = IntPrompt.ask("Elige", choices=[str(i) for i in range(1, len(results) + 1)], show_choices=False)
    return results[index - 1]["id"]


# ---------------------------------------------------------------- menu

MENU = [
    ("1", "Estado de todas las series", "status -tv"),
    ("2", "Detalle de una serie", "status -sn"),
    ("3", "Próximos episodios / pendientes", "updates"),
    ("4", "Episodios faltantes por serie", "missing"),
    ("5", "Episodios faltantes de una serie", "missing -sn"),
    ("6", "Listar series", "list"),
    ("7", "Scan (omite series terminadas y completas)", "scan"),
    ("8", "Scan completo (todas)", "scan --full"),
    ("9", "Scan de una serie", "scan -sn"),
    ("10", "Fix: corregir tmdbId de una serie", "fix -sn"),
    ("11", "Unfollow: revisar una serie solo hasta cierta temporada", "unfollow -sn"),
    ("0", "Salir", ""),
]


def run_menu(settings_loader) -> None:
    while True:
        console.print()
        table = Table.grid(padding=(0, 2))
        for key, label, command in MENU:
            table.add_row(Text(key, style="bold bright_blue"), label, Text(f"TMDB {command}" if command else "",
                                                                             style="grey50"))
        console.print(Panel(table, title="[bold]🎬 TMDB Updates", border_style="bright_blue", expand=False))
        choice = Prompt.ask("Opción", choices=[k for k, _, _ in MENU], show_choices=False)
        if choice == "0":
            return
        try:
            if choice == "1":
                cmd_status()
            elif choice == "2":
                cmd_status(Prompt.ask("Serie"))
            elif choice == "3":
                cmd_updates()
            elif choice == "4":
                cmd_missing()
            elif choice == "5":
                cmd_missing(Prompt.ask("Serie"))
            elif choice == "6":
                cmd_list()
            elif choice == "7":
                cmd_scan(settings_loader())
            elif choice == "8":
                cmd_scan(settings_loader(), full=True)
            elif choice == "9":
                cmd_scan(settings_loader(), Prompt.ask("Serie"))
            elif choice == "10":
                name = Prompt.ask("Serie")
                mode = Prompt.ask("¿Usar tmdbId del JSON (j), escribir uno (i) o buscar (b)?",
                                  choices=["j", "i", "b"], default="j")
                tmdb_id = IntPrompt.ask("tmdbId") if mode == "i" else None
                cmd_fix(settings_loader(), name, tmdb_id, search=mode == "b")
            elif choice == "11":
                name = Prompt.ask("Serie")
                season = IntPrompt.ask("Última temporada a revisar (0 = todas)")
                cmd_unfollow(settings_loader(), name, season or None)
        except (AppError, ConfigError, TmdbError) as exc:
            console.print(f"[red]✘ {exc}")
        Prompt.ask("[grey50]Enter para continuar", default="", show_default=False)


# ---------------------------------------------------------------- entrada

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="TMDB", description="Revisa tu biblioteca de series contra TMDB. "
                                                              "Sin argumentos abre el menú interactivo.")
    sub = parser.add_subparsers(dest="command")
    # --json va después del subcomando: TMDB status --json
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true",
                        help="Imprime el resultado como JSON (los mensajes y el progreso van a stderr)")

    status = sub.add_parser("status", parents=[common], help="Estado de la biblioteca o de una serie")
    group = status.add_mutually_exclusive_group()
    group.add_argument("-tv", action="store_true", help="Resumen de todas las series (default)")
    group.add_argument("-sn", metavar="NOMBRE", help="Detalle de una serie")

    sub.add_parser("updates", parents=[common], help="Episodios faltantes o por salir (hoy -2 meses .. hoy +1 semana)")
    missing = sub.add_parser("missing", parents=[common], help="Solo los episodios ya emitidos que te faltan, por serie")
    missing.add_argument("-sn", metavar="NOMBRE", help="Solo esta serie")
    sub.add_parser("list", parents=[common], help="Lista de series con su status de TMDB")

    scan = sub.add_parser("scan", parents=[common], help="Escanea la biblioteca y actualiza data/library.json")
    scan.add_argument("-sn", metavar="NOMBRE", help="Escanear solo esta serie")
    scan.add_argument("--full", action="store_true", help="Incluir series terminadas y completas")

    fix = sub.add_parser("fix", parents=[common], help="Recarga una serie usando su tmdbId")
    fix.add_argument("-sn", metavar="NOMBRE", required=True, help="Serie a corregir")
    fix_source = fix.add_mutually_exclusive_group()
    fix_source.add_argument("--id", type=int, help="Asignar este tmdbId")
    fix_source.add_argument("--search", action="store_true", help="Buscar en TMDB y elegir de una lista")

    unfollow = sub.add_parser("unfollow", parents=[common], help="Revisa una serie solo hasta cierta temporada")
    unfollow.add_argument("-sn", metavar="NOMBRE", required=True, help="Serie a limitar")
    unfollow_target = unfollow.add_mutually_exclusive_group(required=True)
    unfollow_target.add_argument("-s", type=int, metavar="TEMPORADA", help="Última temporada a revisar")
    unfollow_target.add_argument("--all", action="store_true", help="Quitar el límite y revisar todas")

    movie = sub.add_parser(
        "movie", parents=[common],
        help="Películas: -d renombra a 'Nombre (Año)' + poster; -mv mueve a un género; -ls lista por género",
        usage="TMDB movie -d CARPETA -n NOMBRE [-y AÑO] [--json]\n"
              "       TMDB movie -mv CARPETA [-g GENERO] [--json]\n"
              "       TMDB movie -ls [-g GENERO] [--refresh] [--no-posters] [-o ARCHIVO.json] [--json]")
    movie_action = movie.add_mutually_exclusive_group(required=True)
    movie_action.add_argument("-d", metavar="CARPETA",
                              help="Renombrar esta carpeta a 'Nombre (Año)' y bajar el poster (acepta Tab)")
    movie_action.add_argument("-mv", metavar="CARPETA",
                              help="Mover esta carpeta a MOVIE_PATHS/<género> (acepta Tab)")
    movie_action.add_argument("-ls", action="store_true", help="Listar las películas por género")
    movie.add_argument("-n", metavar="NOMBRE", help="Con -d: nombre de la película (obligatorio)")
    movie.add_argument("-y", type=int, metavar="AÑO", help="Con -d: año de estreno (opcional, ayuda a encontrarla)")
    movie.add_argument("--refresh", action="store_true",
                       help="Con -ls: vuelve a validar todo con TMDB (ignora data/movies.json)")
    movie.add_argument("--no-posters", action="store_true", help="Con -ls: no bajar posters faltantes")
    movie.add_argument("-o", "--out", metavar="ARCHIVO", help="Con -ls: exporta el resultado a un archivo JSON")
    movie.add_argument("-g", metavar="GENERO",
                       help="Con -mv: género destino (si no existe se crea; sin -g te deja elegir). "
                            "Con -ls: solo ese género (acepta parte del nombre)")
    movie.set_defaults(movie_parser=movie)
    return parser


def check_movie_args(args) -> None:
    error = args.movie_parser.error
    if args.d is not None:
        if not args.n:
            error("-d necesita -n NOMBRE")
        if args.g:
            error("-g solo se usa con -mv o -ls")
    elif args.n or args.y:
        error("-n y -y solo se usan con -d")
    if not args.ls and (args.refresh or args.no_posters or args.out):
        error("--refresh, --no-posters y -o solo se usan con -ls")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = repair_windows_argv(sys.argv[1:])
    args = build_parser().parse_args(argv)
    as_json = getattr(args, "json", False)
    if as_json:
        # stdout queda solo para el JSON; avisos, progreso y errores van a stderr.
        console.file = sys.stderr
    try:
        result = None
        if args.command is None:
            run_menu(load_settings)
        elif args.command == "status":
            result = cmd_status(args.sn, as_json)
        elif args.command == "updates":
            result = cmd_updates(as_json)
        elif args.command == "missing":
            result = cmd_missing(args.sn, as_json)
        elif args.command == "list":
            result = cmd_list(as_json)
        elif args.command == "scan":
            result = cmd_scan(load_settings(), args.sn, args.full, as_json)
        elif args.command == "fix":
            result = cmd_fix(load_settings(), args.sn, args.id, args.search, as_json)
        elif args.command == "unfollow":
            result = cmd_unfollow(load_settings(), args.sn, None if args.all else args.s, as_json)
        elif args.command == "movie":
            check_movie_args(args)
            if args.d is not None:
                result = cmd_movie(load_settings(require_tv=False), args.d, args.n, args.y, as_json)
            elif args.ls:
                result = cmd_movie_list(load_settings(require_tv=False), args.g, as_json, args.refresh,
                                        not args.no_posters, args.out)
            else:
                result = cmd_movie_move(load_settings(require_tv=False), args.mv, args.g, as_json)
        if as_json:
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (AppError, ConfigError, TmdbError, MovieError) as exc:
        console.print(f"[red]✘ {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado.")
        return 130
    except EOFError:
        console.print("\n[red]✘ No hay entrada interactiva disponible.")
        return 1
    return 0
