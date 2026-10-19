import argparse
import calendar
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from . import report
from .config import LIBRARY_FILE, ConfigError, Settings, load_settings
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
                   existing: dict | None, today: date) -> dict:
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
                record = base_record(local)
                record["error"] = f"Sin resultados en TMDB para '{local.title}'. Asigna tmdbId y usa 'fix'."
                return record
            tmdb_id = match["id"]
        return evaluate(local, client.get_tv(tmdb_id), today)
    except TmdbError as exc:
        # Un fallo de red no debe borrar lo que ya sabiamos de la serie
        record = dict(existing) if existing and existing.get("seasons") else base_record(local)
        record["tmdbId"] = tmdb_id
        if not record.get("seasons"):
            record["tag"] = ERROR
        record["error"] = str(exc)
        return record


# ---------------------------------------------------------------- comandos

def cmd_scan(settings: Settings, name: str | None = None, full: bool = False) -> None:
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
                            (existing or {}).get("tmdbId"), existing, today): path
                for path, root, existing in jobs
            }
            for future in as_completed(futures):
                record = future.result()
                library.series[record["path"]] = record
                scanned.append(record)
                progress.update(task, advance=1, description=f"Escaneando · {record['folder'][:40]}")
    finally:
        library.save()

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


def cmd_status(name: str | None = None) -> None:
    library = Library()
    if name:
        report.render_series_detail(console, find_series(library, name), date.today())
    else:
        require_data(library)
        report.render_tv_status(console, library)


def cmd_updates() -> None:
    library = Library()
    require_data(library)
    today = date.today()
    report.render_updates(console, library, today, months_ago(today, 2), today + timedelta(days=7))


def cmd_list() -> None:
    library = Library()
    require_data(library)
    report.render_list(console, library)


def cmd_fix(settings: Settings, name: str, tmdb_id: int | None = None, search: bool = False) -> None:
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
                                None, date.today())
    if record.get("error"):
        raise AppError(f"No se aplicó el fix, la serie queda como estaba: {record['error']}")
    library.series[record["path"]] = record
    library.save(touch_scan=False)
    console.print(f"[green]✔ {series['folder']} actualizado con TMDB {tmdb_id}.\n")
    report.render_series_detail(console, record, date.today())


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
    ("4", "Listar series", "list"),
    ("5", "Scan (omite series terminadas y completas)", "scan"),
    ("6", "Scan completo (todas)", "scan --full"),
    ("7", "Scan de una serie", "scan -sn"),
    ("8", "Fix: corregir tmdbId de una serie", "fix -sn"),
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
                cmd_list()
            elif choice == "5":
                cmd_scan(settings_loader())
            elif choice == "6":
                cmd_scan(settings_loader(), full=True)
            elif choice == "7":
                cmd_scan(settings_loader(), Prompt.ask("Serie"))
            elif choice == "8":
                name = Prompt.ask("Serie")
                mode = Prompt.ask("¿Usar tmdbId del JSON (j), escribir uno (i) o buscar (b)?",
                                  choices=["j", "i", "b"], default="j")
                tmdb_id = IntPrompt.ask("tmdbId") if mode == "i" else None
                cmd_fix(settings_loader(), name, tmdb_id, search=mode == "b")
        except (AppError, ConfigError, TmdbError) as exc:
            console.print(f"[red]✘ {exc}")
        Prompt.ask("[grey50]Enter para continuar", default="", show_default=False)


# ---------------------------------------------------------------- entrada

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="TMDB", description="Revisa tu biblioteca de series contra TMDB. "
                                                              "Sin argumentos abre el menú interactivo.")
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Estado de la biblioteca o de una serie")
    group = status.add_mutually_exclusive_group()
    group.add_argument("-tv", action="store_true", help="Resumen de todas las series (default)")
    group.add_argument("-sn", metavar="NOMBRE", help="Detalle de una serie")

    sub.add_parser("updates", help="Episodios faltantes o por salir (hoy -2 meses .. hoy +1 semana)")
    sub.add_parser("list", help="Lista de series con su status de TMDB")

    scan = sub.add_parser("scan", help="Escanea la biblioteca y actualiza data/library.json")
    scan.add_argument("-sn", metavar="NOMBRE", help="Escanear solo esta serie")
    scan.add_argument("--full", action="store_true", help="Incluir series terminadas y completas")

    fix = sub.add_parser("fix", help="Recarga una serie usando su tmdbId")
    fix.add_argument("-sn", metavar="NOMBRE", required=True, help="Serie a corregir")
    fix_source = fix.add_mutually_exclusive_group()
    fix_source.add_argument("--id", type=int, help="Asignar este tmdbId")
    fix_source.add_argument("--search", action="store_true", help="Buscar en TMDB y elegir de una lista")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command is None:
            run_menu(load_settings)
        elif args.command == "status":
            cmd_status(args.sn)
        elif args.command == "updates":
            cmd_updates()
        elif args.command == "list":
            cmd_list()
        elif args.command == "scan":
            cmd_scan(load_settings(), args.sn, args.full)
        elif args.command == "fix":
            cmd_fix(load_settings(), args.sn, args.id, args.search)
    except (AppError, ConfigError, TmdbError) as exc:
        console.print(f"[red]✘ {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado.")
        return 130
    except EOFError:
        console.print("\n[red]✘ No hay entrada interactiva disponible.")
        return 1
    return 0
