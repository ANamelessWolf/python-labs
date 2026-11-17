import argparse
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.text import Text

from . import export, report
from .config import (
    CMD, DEFAULT_CONFIG, DEFAULT_SITE, DESCRIPTION, EXAMPLE_QUERY, GENERAL_FILE, OUTPUT_DIR, PLACEHOLDER,
    camel_case_filename, load_config,
)
from .scraper import new_session
from .search import Output

console = Console()


# ---------------------------------------------------------------- comandos

def cmd_series(config: dict, delay: float, auto: bool, as_json: bool = False) -> dict | int:
    """Busca cada episodio de la config. En modo JSON devuelve el dict; si no, dibuja el resumen y regresa
    el codigo de salida."""
    serie = config["SERIE"]
    console.print(Panel(Text(serie, style="bold magenta", justify="center"),
                        subtitle=f"[dim]{config['SITE']}[/dim]", border_style="magenta"))

    session = new_session()
    # Si el archivo ya existe (mismo SERIE, otro QUERY) se anexan solo los magnets nuevos
    with Output(OUTPUT_DIR / camel_case_filename(serie), console) as output:
        for season in config["SEASON"]:
            index, start, end = int(season["INDEX"]), int(season["START"]), int(season["END"])
            console.print(Rule(f"[bold yellow]Season {index}[/bold yellow]  [dim]E{start:02d}-E{end:02d}[/dim]",
                               style="yellow", align="left"))
            for episode in range(start, end + 1):
                code = f"S{index:02d}E{episode:02d}"
                output.handle(session, config["SITE"], config["QUERY"].replace(PLACEHOLDER, code),
                              f"Episode {episode}", code, auto, index, episode)
                time.sleep(delay)

    if as_json:
        return export.search_result("series", output, site=config["SITE"], serie=serie, query=config["QUERY"],
                                    auto=auto)
    return report.render_summary(console, output)


def cmd_query(site: str, query: str, auto: bool, as_json: bool = False) -> dict | int:
    """Una sola busqueda; el magnet va a output/general.txt."""
    console.print(Panel(Text(query, style="bold magenta", justify="center"),
                        subtitle=f"[dim]{site}[/dim]", border_style="magenta"))
    with Output(GENERAL_FILE, console) as output:
        output.handle(new_session(), site, query, "Query", query, auto)

    if as_json:
        return export.search_result("query", output, site=site, serie=None, query=query, auto=auto)
    return report.render_summary(console, output)


# ---------------------------------------------------------------- wizard

def ask_int(label: str, default: int | None = None, minimum: int = 1) -> int:
    while True:
        value = IntPrompt.ask(label, default=default)
        if value >= minimum:
            return value
        console.print(f"[red]Debe ser {minimum} o mayor.[/red]")


def wizard(config_path: Path) -> dict:
    """Pregunta los datos en consola y guarda el settings.json. Usa la config actual como valores por defecto."""
    try:
        current = load_config(config_path)
    except (OSError, ValueError):
        current = {}
    seasons_now = {int(s["INDEX"]): s for s in current.get("SEASON", [])}

    console.print(Panel("[bold]Configura la búsqueda[/bold]\n[dim]Enter acepta el valor entre paréntesis.[/dim]",
                        title="🧙 Wizard", border_style="magenta", expand=False))
    site = Prompt.ask("[cyan]Sitio[/cyan]", default=current.get("SITE", DEFAULT_SITE))
    serie = Prompt.ask("[cyan]Serie[/cyan]", default=current.get("SERIE"))
    while not serie or not serie.strip():
        serie = Prompt.ask("[cyan]Serie[/cyan]")
    serie = serie.strip()

    query_default = current.get("QUERY") if current.get("SERIE") == serie else f"{serie} {PLACEHOLDER}"
    console.print(f"[dim]El query debe incluir {PLACEHOLDER}; se reemplaza por S01E01, S01E02, ...[/dim]")
    while True:
        query = Prompt.ask("[cyan]Query[/cyan]", default=query_default).strip()
        if PLACEHOLDER in query:
            break
        console.print(f"[red]Falta {PLACEHOLDER} en el query.[/red]")

    first = ask_int("[cyan]Temporada inicial[/cyan]", default=min(seasons_now) if seasons_now else 1)
    last_raw = Prompt.ask("[cyan]Temporada final[/cyan] [dim](vacío = solo una)[/dim]", default="", show_default=False)
    while last_raw.strip() and (not last_raw.strip().isdigit() or int(last_raw) < first):
        console.print(f"[red]Escribe un número mayor o igual a {first}, o déjalo vacío.[/red]")
        last_raw = Prompt.ask("[cyan]Temporada final[/cyan] [dim](vacío = solo una)[/dim]", default="",
                              show_default=False)
    last = int(last_raw) if last_raw.strip() else first

    seasons = []
    for index in range(first, last + 1):
        console.print(Rule(f"[bold yellow]Season {index}[/bold yellow]", style="yellow", align="left"))
        prev = seasons_now.get(index, {})
        start = ask_int("    [cyan]Episodio inicial[/cyan]", default=int(prev.get("START", 1)))
        end = ask_int("    [cyan]Episodio final[/cyan]", default=int(prev["END"]) if "END" in prev else None,
                      minimum=start)
        seasons.append({"INDEX": index, "START": start, "END": end})

    config = {"SITE": site, "SERIE": serie, "QUERY": query, "SEASON": seasons}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total = sum(s["END"] - s["START"] + 1 for s in seasons)
    console.print(f"\n[green]✔ Guardado en[/green] {config_path} [dim]({len(seasons)} temporada(s), "
                  f"{total} episodio(s) → output\\{camel_case_filename(serie)})[/dim]", soft_wrap=True)
    return config


# ---------------------------------------------------------------- entrada

HELP_EPILOG = f"""
modos:
  {CMD}                      busca la serie de config\\settings.json
  {CMD} -w                   wizard: pregunta serie, query, temporadas y episodios,
                             guarda settings.json y busca
  {CMD} -q "texto"           una sola búsqueda; el magnet se agrega a output\\general.txt

opciones que se combinan con cualquier modo:
  -a, --auto                 no preguntar: tomar siempre el primer resultado
  -c, --config ARCHIVO       usar otro settings.json (también lo que guarda el wizard)
  --delay N                  segundos entre búsquedas (default 1)
  --json                     imprime el resultado como JSON en stdout (mensajes y progreso
                             a stderr); implica --auto y no se combina con -w

ejemplos:
  {CMD} -a
  {CMD} -w --auto
  {CMD} -q "{EXAMPLE_QUERY}" -a
  {CMD} -c config\\otra.json
  {CMD} -q "{EXAMPLE_QUERY}" --json

al elegir: número de la fila, Enter = 1, 0 = omitir.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=CMD, description=DESCRIPTION, epilog=HELP_EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-w", "--wizard", action="store_true", help="configurar settings.json paso a paso y buscar")
    mode.add_argument("-q", "--query", metavar="TEXTO", help="una sola búsqueda; se agrega a output\\general.txt")
    parser.add_argument("-a", "--auto", action="store_true", help="no preguntar: tomar siempre el primer resultado")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="archivo JSON de configuración")
    parser.add_argument("--delay", type=float, default=1.0, help="segundos entre búsquedas (default 1)")
    # Sin subcomandos: --json es una opción más (PBAY -q "texto" --json)
    parser.add_argument("--json", action="store_true",
                        help="imprime el resultado como JSON (mensajes y progreso van a stderr); implica --auto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    as_json = args.json
    if as_json:
        # stdout queda solo para el JSON; paneles, progreso, avisos y errores van a stderr.
        console.file = sys.stderr
        if args.wizard:
            console.print("[bold red]El wizard es interactivo y no se combina con --json.[/bold red]")
            return 1

    interactive = sys.stdin.isatty()
    if args.wizard and not interactive:
        console.print("[bold red]El wizard necesita una consola interactiva.[/bold red]")
        return 1
    # Con --json nadie puede elegir: se toma el primer resultado, igual que sin consola interactiva.
    auto = args.auto or as_json or not interactive
    if auto and not args.auto and not as_json:
        console.print("[yellow]Sin consola interactiva: se toma el primer resultado de cada búsqueda.[/yellow]")

    try:
        if args.query:
            try:
                site = load_config(args.config)["SITE"]
            except (OSError, ValueError):
                site = DEFAULT_SITE
            result = cmd_query(site, args.query, auto, as_json)
        else:
            if args.wizard:
                config = wizard(args.config)
                if not Confirm.ask("¿Buscar ahora?", default=True):
                    return 0
                console.print()
            else:
                try:
                    config = load_config(args.config)
                except (OSError, ValueError) as exc:
                    console.print(f"[bold red]Error de configuración:[/bold red] {exc}")
                    console.print(f"[dim]Tip: {CMD} -w para crearla paso a paso.[/dim]")
                    return 1
            result = cmd_series(config, args.delay, auto, as_json)

        if as_json:
            # Los fallos de cada busqueda van en items (state ERROR); el JSON se imprime igual.
            sys.stdout.reconfigure(encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return result
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado. Lo elegido hasta ahora ya está guardado.[/yellow]")
        return 130
    except EOFError:
        console.print("\n[red]No hay entrada interactiva disponible.[/red]")
        return 1
