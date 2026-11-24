"""Archivo de salida: busca, elige (o pregunta), guarda el magnet y registra cada busqueda.

Lo que queda registrado (stats y searches) es lo que usan el resumen de report.py y el JSON de export.py.
"""
from dataclasses import dataclass, field
from pathlib import Path

import requests
from rich.console import Console

from . import report
from .scraper import Result, build_url, fetch_results

COPIED, SAVED, SKIPPED, NOT_FOUND, ERROR = "Copied", "Saved", "Skipped", "Not Found", "Error"
FOUND = "Found"   # solo con --list: hubo resultados y no se eligio ninguno
STATES = [COPIED, SAVED, SKIPPED, NOT_FOUND, ERROR, FOUND]


@dataclass
class Search:
    query: str
    state: str                    # uno de STATES
    season: int | None = None     # None en una busqueda suelta (-q)
    episode: int | None = None
    code: str | None = None       # "S01E05"
    result_count: int = 0
    result: Result | None = None  # el guardado (Copied) o el que ya estaba en el archivo (Saved)
    error: str | None = None
    results: list[Result] = field(default_factory=list)   # todos los resultados (solo con --list)


class Output:
    """Archivo de salida en modo anexar; recuerda los magnets ya guardados para no repetirlos."""

    def __init__(self, path: Path, console: Console, list_only: bool = False):
        self.path = path
        self.console = console
        self.list_only = list_only   # --list: registra todos los resultados y no escribe nada
        path.parent.mkdir(parents=True, exist_ok=True)
        self.saved: set[str] = set()
        if path.exists():
            self.saved = {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
        self.stats = {state: 0 for state in STATES}
        self.searches: list[Search] = []

    def __enter__(self):
        # Con --list no se abre el archivo: solo se lee para marcar los magnets ya guardados
        self.file = None if self.list_only else self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *exc):
        if self.file:
            self.file.close()

    def record(self, search: Search) -> None:
        self.stats[search.state] += 1
        self.searches.append(search)

    def handle(self, session: requests.Session, site: str, query: str, prefix: str, code: str, auto: bool,
               season: int | None = None, episode: int | None = None) -> None:
        """Busca, elige (o pregunta) y guarda. Se escribe al momento para no perder nada si cancelas."""
        console = self.console
        search = Search(query, ERROR, season, episode, code if season is not None else None)
        try:
            with console.status(f"[dim]Buscando {query}...[/dim]", spinner="dots"):
                results = fetch_results(session, build_url(site, query))
        except requests.RequestException as exc:
            console.print(report.episode_line(prefix, f"{query} ({exc.__class__.__name__})", ERROR, "red"))
            search.error = f"{exc.__class__.__name__}: {exc}"
            self.record(search)
            return

        search.result_count = len(results)
        if self.list_only:
            search.results = results
            if results:
                label = f"{query} ({len(results)} resultado{'s' if len(results) != 1 else ''})"
                console.print(report.episode_line(prefix, label, FOUND, "cyan"))
                search.state = FOUND
            else:
                console.print(report.episode_line(prefix, query, NOT_FOUND, "red"))
                search.state = NOT_FOUND
            self.record(search)
            return

        already = next((r for r in results if r.magnet in self.saved), None)
        if not results:
            console.print(report.episode_line(prefix, query, NOT_FOUND, "red"))
            search.state = NOT_FOUND
        elif already:
            # Ya elegiste uno para esta busqueda en una ejecucion anterior
            console.print(report.episode_line(prefix, already.title, SAVED, "blue", already.seeders))
            search.state, search.result = SAVED, already
        else:
            chosen = results[0] if auto or len(results) == 1 else report.ask_choice(console, results, code)
            if chosen is None:
                console.print(report.episode_line(prefix, query, SKIPPED, "yellow"))
                search.state = SKIPPED
            else:
                self.file.write(f"{chosen.magnet}\n")
                self.file.flush()
                self.saved.add(chosen.magnet)
                console.print(report.episode_line(prefix, chosen.title, COPIED, "green", chosen.seeders))
                search.state, search.result = COPIED, chosen
        self.record(search)
