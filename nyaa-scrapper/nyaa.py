"""Nyaa Scrapper: busca episodios en nyaa.si y guarda el magnet link del primer resultado.

Uso:
    python nyaa.py                          usa config/settings.json
    python nyaa.py -c config/otra.json      usa otro archivo de configuracion
    python nyaa.py --delay 2                segundos de espera entre busquedas (default 1)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = APP_DIR / "config" / "settings.json"
OUTPUT_DIR = APP_DIR / "output"
PLACEHOLDER = "SXXEXX"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) nyaa-scrapper"}

console = Console()


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
    """'Thousand-Year Blood War' -> 'thousand-YearBloodWar.txt'"""
    words = serie.split()
    parts = [words[0][:1].lower() + words[0][1:]] + [w[:1].upper() + w[1:] for w in words[1:]]
    name = re.sub(r'[<>:"/\\|?*]', "", "".join(parts))
    return f"{name}.txt"


def build_url(site: str, query: str) -> str:
    params = {"f": 0, "c": "0_0", "q": " ".join(query.split())}
    return f"{site.rstrip('/')}/?{urlencode(params)}"


def fetch_first_result(session: requests.Session, url: str, retries: int = 3) -> tuple[str, str] | None:
    """Regresa (titulo, magnet) del primer resultado, o None si no hay resultados."""
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
    row = soup.select_one("table.torrent-list tbody tr")
    if row is None:
        return None
    magnet = row.select_one('a[href^="magnet:"]')
    if magnet is None:
        return None
    title_link = row.select_one('td[colspan="2"] a[href^="/view/"]:not(.comments)')
    title = (title_link.get("title") or title_link.get_text(strip=True)) if title_link else "?"
    return title, magnet["href"]


def episode_line(episode: int, label: str, status: str, style: str) -> Text:
    line = Text("    ")
    line.append(f"Episode {episode}: ", style="bold cyan")
    line.append(label, style="white" if style == "green" else "dim")
    line.append(f" [{status}]", style=f"bold {style}")
    return line


def run(config: dict, delay: float) -> int:
    serie = config["SERIE"]
    output_file = OUTPUT_DIR / camel_case_filename(serie)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    console.print(Panel(Text(serie, style="bold magenta", justify="center"),
                        subtitle=f"[dim]{config['SITE']}[/dim]", border_style="magenta"))

    session = requests.Session()
    session.headers.update(HEADERS)
    # Si el archivo ya existe (mismo SERIE, otro QUERY) se anexan solo los magnets nuevos
    saved: set[str] = set()
    if output_file.exists():
        saved = {line.strip() for line in output_file.read_text(encoding="utf-8").splitlines() if line.strip()}
    magnets: list[str] = []
    seen: set[str] = set()
    stats = {"Copied": 0, "Saved": 0, "Duplicate": 0, "Not Found": 0, "Error": 0}

    for season in config["SEASON"]:
        index, start, end = int(season["INDEX"]), int(season["START"]), int(season["END"])
        console.print(Rule(f"[bold yellow]Season {index}[/bold yellow]  [dim]E{start:02d}-E{end:02d}[/dim]",
                           style="yellow", align="left"))
        for episode in range(start, end + 1):
            query = config["QUERY"].replace(PLACEHOLDER, f"S{index:02d}E{episode:02d}")
            url = build_url(config["SITE"], query)
            try:
                with console.status(f"[dim]Buscando {query}...[/dim]", spinner="dots"):
                    result = fetch_first_result(session, url)
            except requests.RequestException as exc:
                console.print(episode_line(episode, f"{query} ({exc.__class__.__name__})", "Error", "red"))
                stats["Error"] += 1
                result = False

            if result is None:
                console.print(episode_line(episode, query, "Not Found", "red"))
                stats["Not Found"] += 1
            elif result:
                title, magnet = result
                if magnet in saved:
                    console.print(episode_line(episode, title, "Saved", "blue"))
                    stats["Saved"] += 1
                elif magnet in seen:
                    # Un batch puede salir como primer resultado de varios episodios
                    console.print(episode_line(episode, title, "Duplicate", "yellow"))
                    stats["Duplicate"] += 1
                else:
                    seen.add(magnet)
                    magnets.append(magnet)
                    console.print(episode_line(episode, title, "Copied", "green"))
                    stats["Copied"] += 1
            time.sleep(delay)

    with output_file.open("a", encoding="utf-8") as fh:
        fh.writelines(f"{m}\n" for m in magnets)

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_row("[green]Copied[/green]", str(stats["Copied"]))
    summary.add_row("[blue]Saved[/blue]", str(stats["Saved"]))
    summary.add_row("[yellow]Duplicate[/yellow]", str(stats["Duplicate"]))
    summary.add_row("[red]Not Found[/red]", str(stats["Not Found"]))
    if stats["Error"]:
        summary.add_row("[bold red]Error[/bold red]", str(stats["Error"]))
    console.print()
    console.print(Panel(summary, title="[bold]Resumen[/bold]", border_style="cyan", expand=False))
    console.print(f"[cyan]Archivo:[/cyan] {output_file}", soft_wrap=True)
    return 0 if stats["Error"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca episodios en nyaa.si y guarda sus magnet links.")
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="archivo JSON de configuracion")
    parser.add_argument("--delay", type=float, default=1.0, help="segundos entre busquedas (default 1)")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        console.print(f"[bold red]Error de configuracion:[/bold red] {exc}")
        return 1

    try:
        return run(config, args.delay)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado.[/yellow]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
