"""PirateBay Scrapper: busca episodios en un mirror de The Pirate Bay y guarda el magnet link elegido.

Uso:
    python pbay.py                          usa config/settings.json
    python pbay.py -c config/otra.json      usa otro archivo de configuracion
    python pbay.py -a / --auto              no pregunta: toma siempre el primer resultado
    python pbay.py -w / --wizard            configura settings.json paso a paso y busca
    python pbay.py -q "texto"               una sola busqueda; se agrega a output/general.txt
    python pbay.py -h                       ayuda con todos los comandos
    python pbay.py --delay 2                segundos de espera entre busquedas (default 1)
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = APP_DIR / "config" / "settings.json"
OUTPUT_DIR = APP_DIR / "output"
GENERAL_FILE = OUTPUT_DIR / "general.txt"
PLACEHOLDER = "SXXEXX"
DEFAULT_SITE = "https://thepiratebay.bond"
CMD = "PBAY"
DESCRIPTION = "Busca episodios en The Pirate Bay y guarda sus magnet links."
EXAMPLE_QUERY = "Helluva Boss S03E01"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) pbay-scrapper"}

console = Console()


@dataclass
class Result:
    title: str
    magnet: str
    size: str
    seeders: str
    leechers: str


def load_config(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    # Tolera comas finales: { "a": 1, } / [ 1, 2, ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    config = json.loads(raw)
    for key in ("SITE", "SERIE", "QUERY", "SEASON"):
        if key not in config:
            raise ValueError(f"Falta la clave '{key}' en {path}")
    if PLACEHOLDER not in config["QUERY"]:
        raise ValueError(f"QUERY debe contener '{PLACEHOLDER}'")
    return config


def camel_case_filename(serie: str) -> str:
    """'Helluva Boss' -> 'helluvaBoss.txt'"""
    words = serie.split()
    parts = [words[0][:1].lower() + words[0][1:]] + [w[:1].upper() + w[1:] for w in words[1:]]
    name = re.sub(r'[<>:"/\\|?*]', "", "".join(parts))
    return f"{name}.txt"


def build_url(site: str, query: str) -> str:
    # /search/<query>/<pagina>/<orden 99 = default>/<categoria 0 = todas>
    return f"{site.rstrip('/')}/search/{quote(' '.join(query.split()))}/1/99/0"


def fetch_results(session: requests.Session, url: str, retries: int = 3) -> list[Result]:
    for attempt in range(1, retries + 1):
        response = session.get(url, timeout=30)
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 * attempt)
            continue
        response.raise_for_status()
        break
    else:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for row in soup.select("table#searchResult tr"):
        magnet = row.select_one('a[href^="magnet:"]')
        title_link = row.select_one('a[href*="/torrent/"]')
        if magnet is None or title_link is None:
            continue
        cells = row.find_all("td", recursive=False)
        # Columnas: Type | Name | Uploaded | Magnet | Size | SE | LE | ULed by
        size, seeders, leechers = (
            (cells[4].get_text(" ", strip=True), cells[5].get_text(strip=True), cells[6].get_text(strip=True))
            if len(cells) >= 7 else ("?", "?", "?")
        )
        results.append(Result(title_link.get_text(strip=True), magnet["href"], size, seeders, leechers))
    return results


def ask_choice(results: list[Result], episode_code: str) -> Result | None:
    table = Table(title=f"[bold]{episode_code}[/bold] · {len(results)} resultados", title_justify="left",
                  header_style="bold cyan", border_style="grey37", show_lines=False)
    table.add_column("#", style="bold yellow", justify="right")
    table.add_column("Nombre", overflow="fold")
    table.add_column("Tamaño", justify="right", style="magenta", no_wrap=True)
    table.add_column("Seeds", justify="right", style="bold green", no_wrap=True)
    table.add_column("Leechers", justify="right", style="red", no_wrap=True)
    for i, r in enumerate(results, start=1):
        table.add_row(str(i), r.title, r.size, f"▲ {r.seeders}", f"▼ {r.leechers}")
    console.print(table)
    index = IntPrompt.ask("    [bold]¿Cuál agrego?[/bold] [dim](0 = omitir)[/dim]",
                          choices=[str(i) for i in range(len(results) + 1)], show_choices=False, default=1)
    return results[index - 1] if index else None


def episode_line(prefix: str, label: str, status: str, style: str, seeders: str | None = None) -> Text:
    line = Text("    ")
    line.append(f"{prefix}: ", style="bold cyan")
    line.append(label, style="white" if style == "green" else "dim")
    if seeders is not None:
        line.append(f" (▲ {seeders} seeds)", style="green")
    line.append(f" [{status}]", style=f"bold {style}")
    return line


class Output:
    """Archivo de salida en modo anexar; recuerda los magnets ya guardados para no repetirlos."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.saved: set[str] = set()
        if path.exists():
            self.saved = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
        self.stats = {"Copied": 0, "Saved": 0, "Skipped": 0, "Not Found": 0, "Error": 0}

    def __enter__(self):
        self.file = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.file.close()

    def handle(self, session: requests.Session, site: str, query: str, prefix: str, code: str, auto: bool) -> None:
        """Busca, elige (o pregunta) y guarda. Se escribe al momento para no perder nada si cancelas."""
        try:
            with console.status(f"[dim]Buscando {query}...[/dim]", spinner="dots"):
                results = fetch_results(session, build_url(site, query))
        except requests.RequestException as exc:
            console.print(episode_line(prefix, f"{query} ({exc.__class__.__name__})", "Error", "red"))
            self.stats["Error"] += 1
            return

        already = next((r for r in results if r.magnet in self.saved), None)
        if not results:
            console.print(episode_line(prefix, query, "Not Found", "red"))
            self.stats["Not Found"] += 1
        elif already:
            # Ya elegiste uno para esta busqueda en una ejecucion anterior
            console.print(episode_line(prefix, already.title, "Saved", "blue", already.seeders))
            self.stats["Saved"] += 1
        else:
            chosen = results[0] if auto or len(results) == 1 else ask_choice(results, code)
            if chosen is None:
                console.print(episode_line(prefix, query, "Skipped", "yellow"))
                self.stats["Skipped"] += 1
            else:
                self.file.write(f"{chosen.magnet}\n")
                self.file.flush()
                self.saved.add(chosen.magnet)
                console.print(episode_line(prefix, chosen.title, "Copied", "green", chosen.seeders))
                self.stats["Copied"] += 1

    def summary(self) -> int:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[green]Copied[/green]", str(self.stats["Copied"]))
        table.add_row("[blue]Saved[/blue]", str(self.stats["Saved"]))
        table.add_row("[yellow]Skipped[/yellow]", str(self.stats["Skipped"]))
        table.add_row("[red]Not Found[/red]", str(self.stats["Not Found"]))
        if self.stats["Error"]:
            table.add_row("[bold red]Error[/bold red]", str(self.stats["Error"]))
        console.print()
        console.print(Panel(table, title="[bold]Resumen[/bold]", border_style="cyan", expand=False))
        console.print(f"[cyan]Archivo:[/cyan] {self.path}", soft_wrap=True)
        return 0 if self.stats["Error"] == 0 else 1


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def run(config: dict, delay: float, auto: bool) -> int:
    serie = config["SERIE"]
    console.print(Panel(Text(serie, style="bold magenta", justify="center"),
                        subtitle=f"[dim]{config['SITE']}[/dim]", border_style="magenta"))

    session = new_session()
    # Si el archivo ya existe (mismo SERIE, otro QUERY) se anexan solo los magnets nuevos
    with Output(OUTPUT_DIR / camel_case_filename(serie)) as output:
        for season in config["SEASON"]:
            index, start, end = int(season["INDEX"]), int(season["START"]), int(season["END"])
            console.print(Rule(f"[bold yellow]Season {index}[/bold yellow]  [dim]E{start:02d}-E{end:02d}[/dim]",
                               style="yellow", align="left"))
            for episode in range(start, end + 1):
                code = f"S{index:02d}E{episode:02d}"
                output.handle(session, config["SITE"], config["QUERY"].replace(PLACEHOLDER, code),
                              f"Episode {episode}", code, auto)
                time.sleep(delay)
    return output.summary()


def run_query(site: str, query: str, auto: bool) -> int:
    console.print(Panel(Text(query, style="bold magenta", justify="center"),
                        subtitle=f"[dim]{site}[/dim]", border_style="magenta"))
    with Output(GENERAL_FILE) as output:
        output.handle(new_session(), site, query, "Query", query, auto)
    return output.summary()


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

ejemplos:
  {CMD} -a
  {CMD} -w --auto
  {CMD} -q "{EXAMPLE_QUERY}" -a
  {CMD} -c config\\otra.json

al elegir: número de la fila, Enter = 1, 0 = omitir.
"""


def main() -> int:
    parser = argparse.ArgumentParser(prog=CMD, description=DESCRIPTION, epilog=HELP_EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-w", "--wizard", action="store_true", help="configurar settings.json paso a paso y buscar")
    mode.add_argument("-q", "--query", metavar="TEXTO", help="una sola búsqueda; se agrega a output\\general.txt")
    parser.add_argument("-a", "--auto", action="store_true", help="no preguntar: tomar siempre el primer resultado")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="archivo JSON de configuración")
    parser.add_argument("--delay", type=float, default=1.0, help="segundos entre búsquedas (default 1)")
    args = parser.parse_args()

    interactive = sys.stdin.isatty()
    if args.wizard and not interactive:
        console.print("[bold red]El wizard necesita una consola interactiva.[/bold red]")
        return 1
    auto = args.auto or not interactive
    if auto and not args.auto:
        console.print("[yellow]Sin consola interactiva: se toma el primer resultado de cada búsqueda.[/yellow]")

    try:
        if args.query:
            try:
                site = load_config(args.config)["SITE"]
            except (OSError, ValueError):
                site = DEFAULT_SITE
            return run_query(site, args.query, auto)

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
        return run(config, args.delay, auto)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado. Lo elegido hasta ahora ya está guardado.[/yellow]")
        return 130
    except EOFError:
        console.print("\n[red]No hay entrada interactiva disponible.[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
