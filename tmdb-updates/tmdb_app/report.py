"""Reportes de consola con rich."""
from collections import Counter
from datetime import date, datetime

from rich.box import ROUNDED, SIMPLE_HEAD
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .scanner import (
    COMPLETE, EP_AVAILABLE, EP_EXTRA, EP_MISSING, EP_OK, EP_TBA, ERROR, EXTRA, INCOMPLETE,
    MISSING, NAMING_ERROR, NOT_FOUND, OK, UPCOMING, episode_state, normalize, parse_date,
)

TAG_STYLES = {
    OK: "bold green",
    COMPLETE: "green",
    INCOMPLETE: "bold yellow",
    MISSING: "bold red",
    NAMING_ERROR: "bold magenta",
    UPCOMING: "bold cyan",
    EXTRA: "blue",
    NOT_FOUND: "bold white on red",
    ERROR: "bold white on red",
}
TAG_ICONS = {
    OK: "✔", COMPLETE: "✔", INCOMPLETE: "◐", MISSING: "✘", NAMING_ERROR: "⚠",
    UPCOMING: "◷", EXTRA: "＋", NOT_FOUND: "?", ERROR: "!",
}
STATUS_STYLES = {
    "Returning Series": "green",
    "In Production": "cyan",
    "Planned": "blue",
    "Pilot": "blue",
    "Ended": "grey62",
    "Released": "grey62",
    "Canceled": "red",
}
EP_STYLES = {EP_OK: "green", EP_MISSING: "bold red", EP_AVAILABLE: "cyan", EP_TBA: "grey50", EP_EXTRA: "blue"}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fmt_date(d: date | str | None) -> str:
    if isinstance(d, str):
        d = parse_date(d)
    if d is None:
        return "TBA"
    suffix = "th" if 11 <= d.day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    return f"{MONTHS[d.month - 1]} {d.day}{suffix} {d.year}"


def relative_day(d: date, today: date) -> str:
    delta = (d - today).days
    if delta == 0:
        return "hoy"
    if delta == 1:
        return "mañana"
    if delta == -1:
        return "ayer"
    return f"en {delta} días" if delta > 0 else f"hace {-delta} días"


def fmt_timestamp(value: str | None) -> str:
    if not value:
        return "nunca"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def tag_text(tag: str, icon: bool = True) -> Text:
    label = f"{TAG_ICONS.get(tag, '')} {tag}" if icon else tag
    return Text(label.strip(), style=TAG_STYLES.get(tag, "white"))


def status_text(status: str | None) -> Text:
    return Text(f"[{status or 'sin datos'}]", style=STATUS_STYLES.get(status, "grey50"))


def live_state(ep: dict, today: date) -> str:
    """El estado guardado puede estar viejo: un AVAILABLE ya pudo salir. Se recalcula con la fecha."""
    if ep["state"] in (EP_OK, EP_EXTRA):
        return ep["state"]
    return episode_state(False, True, parse_date(ep.get("airDate")), today)


def season_label(season: dict) -> str:
    return f"Season {season['number']:02d}"


def season_counts(season: dict) -> str:
    if season["tag"] == EXTRA:
        return "no existe en TMDB"
    return f"{season['localEpisodes']}/{season['tmdbEpisodes']}"


def name_differs(series: dict) -> bool:
    """True si el nombre en TMDB no es el de la carpeta: ayuda a detectar matches incorrectos."""
    return bool(series.get("tmdbName")) and normalize(series["tmdbName"]) != normalize(series["folder"])


def visible_tags(series: dict) -> set[str]:
    return {s["tag"] for s in series.get("seasons", []) if s["tag"] != EXTRA}


def series_header(series: dict, show_tag: bool) -> Text:
    line = Text()
    line.append(series["folder"], style="bold")
    line.append(" ")
    line.append_text(status_text(series.get("status")))
    if show_tag:
        line.append(" ")
        line.append_text(tag_text(series["tag"]))
    if series.get("error"):
        line.append(f"  {series['error']}", style="red")
    return line


def tag_summary(items: list[str], order: list[str]) -> Text:
    counts = Counter(items)
    text = Text()
    for tag in order:
        if counts.get(tag):
            text.append(f" {TAG_ICONS.get(tag, '')} {tag} {counts[tag]} ", style=TAG_STYLES.get(tag, ""))
            text.append("  ")
    return text


def print_banner(console: Console, title: str, library) -> None:
    subtitle = f"último scan: {fmt_timestamp(library.last_scan)} · {len(library.series)} series"
    console.print(Panel(Text(title, style="bold white", justify="center"), subtitle=subtitle,
                        border_style="bright_blue", box=ROUNDED))


# ---------------------------------------------------------------- status -tv

def render_tv_status(console: Console, library) -> None:
    print_banner(console, "📺  Estado de la biblioteca", library)
    all_series = library.sorted_series()
    console.print(tag_summary([s["tag"] for s in all_series],
                              [OK, INCOMPLETE, NAMING_ERROR, UPCOMING, NOT_FOUND, ERROR]))
    current_lib = None
    for series in all_series:
        if series["library"] != current_lib:
            current_lib = series["library"]
            console.print()
            console.rule(f"[bold bright_blue]{current_lib}", align="left", style="bright_blue")
        tags = visible_tags(series)
        collapsed = len(tags) <= 1 and not series.get("looseFiles")
        console.print(series_header(series, show_tag=collapsed))
        if collapsed:
            continue
        if series.get("looseFiles"):
            console.print(Text(f"    ⚠ {len(series['looseFiles'])} archivo(s) sueltos en la raíz", style="magenta"))
        for season in series["seasons"]:
            line = Text(f"    {season_label(season)} ")
            line.append_text(tag_text(season["tag"], icon=False))
            line.append(f"  {season_counts(season)}", style="grey50")
            console.print(line)


# ---------------------------------------------------------------- status -sn

def render_series_detail(console: Console, series: dict, today: date) -> None:
    root_label = series_header(series, show_tag=True)
    meta = Text()
    if series.get("tmdbId"):
        meta.append(f"TMDB {series['tmdbId']}", style="grey50")
        if name_differs(series):
            meta.append(f" · {series['tmdbName']}", style="grey50 italic")
        meta.append(" · ", style="grey50")
    meta.append(f"{series['path']} · scan {fmt_timestamp(series.get('lastScan'))}", style="grey50")
    tree = Tree(Group(root_label, meta), guide_style="bright_blue")

    if series.get("looseFiles"):
        loose = tree.add(Text("⚠ Archivos sueltos en la raíz (NAMING_ERROR) — muévelos a 'Season XX'",
                              style="bold magenta"))
        for name in series["looseFiles"]:
            loose.add(Text(name, style="magenta"))

    for season in series.get("seasons", []):
        label = Text(f"{season_label(season)} ")
        label.append_text(tag_text(season["tag"]))
        label.append(f"  {season_counts(season)}", style="grey50")
        if season["tag"] in (MISSING, UPCOMING) and season.get("airDate"):
            label.append(f"  · estreno {fmt_date(season['airDate'])}", style="grey50")
        node = tree.add(label)

        for name in season.get("namingErrors", []):
            node.add(Text(f"✎ {name}", style="magenta"))
        if season["tag"] in (INCOMPLETE, NAMING_ERROR, UPCOMING):
            for ep in season["episodes"]:
                node.add(episode_line(ep, today))
    console.print(tree)


def episode_line(ep: dict, today: date) -> Text:
    state = live_state(ep, today)
    line = Text(f"{ep['code']} ", style="bold")
    if state == EP_MISSING:
        line.append(f"MISSING (Released on {fmt_date(ep['airDate'])})", style=EP_STYLES[state])
    elif state == EP_AVAILABLE:
        line.append(f"AVAILABLE ON {fmt_date(ep['airDate'])}", style=EP_STYLES[state])
        line.append(f" ({relative_day(parse_date(ep['airDate']), today)})", style="grey50")
    elif state == EP_EXTRA:
        line.append("EXTRA (no existe en TMDB)", style=EP_STYLES[state])
    else:
        line.append(state, style=EP_STYLES[state])
    if ep.get("name"):
        line.append(f"  {ep['name']}", style="grey50 italic")
    return line


# ---------------------------------------------------------------- updates

def collect_updates(library, today: date, start: date, end: date) -> list[tuple[date, dict, dict, str]]:
    rows = []
    for series in library.sorted_series():
        if series.get("finished"):
            continue
        for season in series.get("seasons", []):
            if season["tag"] not in (INCOMPLETE, MISSING, UPCOMING):
                continue
            for ep in season["episodes"]:
                state = live_state(ep, today)
                air = parse_date(ep.get("airDate"))
                if state in (EP_MISSING, EP_AVAILABLE) and air and start <= air <= end:
                    rows.append((air, series, ep, state))
    rows.sort(key=lambda r: (r[0], r[1]["folder"].lower(), r[2]["code"]))
    return rows


def render_updates(console: Console, library, today: date, start: date, end: date) -> None:
    print_banner(console, f"🗓  Updates  {fmt_date(start)} → {fmt_date(end)}", library)
    rows = collect_updates(library, today, start, end)
    if not rows:
        console.print(Text("Nada nuevo en este rango. 🎉", style="green"))
        return

    table = Table(box=SIMPLE_HEAD, header_style="bold bright_blue", expand=False)
    table.add_column("Fecha", no_wrap=True)
    table.add_column("Cuándo", style="grey62", no_wrap=True)
    table.add_column("Serie", style="bold")
    table.add_column("Episodio", no_wrap=True)
    table.add_column("Título", style="italic")
    table.add_column("Estado", no_wrap=True)

    past_done = False
    for air, series, ep, state in rows:
        if not past_done and air > today:
            past_done = True
            table.add_section()
        badge = Text("MISSING", style=EP_STYLES[EP_MISSING]) if state == EP_MISSING \
            else Text("AVAILABLE ON", style=EP_STYLES[EP_AVAILABLE])
        table.add_row(fmt_date(air), relative_day(air, today), series["folder"], ep["code"],
                      ep.get("name") or "", badge)
    console.print(table)
    missing = sum(1 for r in rows if r[3] == EP_MISSING)
    console.print(Text(f"{missing} por descargar · {len(rows) - missing} próximos", style="grey62"))


# ---------------------------------------------------------------- list

def render_list(console: Console, library) -> None:
    print_banner(console, "📚  Mis series", library)
    table = Table(box=SIMPLE_HEAD, header_style="bold bright_blue")
    table.add_column("#", style="grey50", justify="right")
    table.add_column("Serie", style="bold")
    table.add_column("Status TMDB", no_wrap=True)
    table.add_column("Tag", no_wrap=True)
    table.add_column("TMDB id", style="grey62", justify="right")
    table.add_column("Nombre en TMDB", style="grey62 italic")

    current_lib = None
    for i, series in enumerate(library.sorted_series(), start=1):
        if series["library"] != current_lib:
            if current_lib is not None:
                table.add_section()
            current_lib = series["library"]
            table.add_row("", Text(current_lib, style="bright_blue"), "", "", "", "")
        table.add_row(
            str(i),
            series["folder"],
            status_text(series.get("status")),
            tag_text(series["tag"]),
            str(series.get("tmdbId") or "—"),
            series["tmdbName"] if name_differs(series) else "",
        )
    console.print(table)


# ---------------------------------------------------------------- scan

def render_scan_result(console: Console, scanned: list[dict], skipped: int, removed: list[str],
                       unavailable: list) -> None:
    for lib in unavailable:
        console.print(Text(f"⚠ Biblioteca no disponible (se conservan sus datos): {lib}", style="yellow"))
    for path in removed:
        console.print(Text(f"🗑 Ya no existe, se quitó del registro: {path}", style="grey50"))
    problems = [s for s in scanned if s["tag"] in (NOT_FOUND, ERROR) or s.get("error")]
    for s in problems:
        console.print(Text(f"✘ {s['folder']}: {s.get('error') or s['tag']}", style="red"))

    body = Text()
    body.append(f"Escaneadas: {len(scanned)}   ", style="bold")
    body.append(f"Omitidas (terminadas y completas): {skipped}\n", style="grey62")
    body.append_text(tag_summary([s["tag"] for s in scanned],
                                 [OK, INCOMPLETE, NAMING_ERROR, UPCOMING, NOT_FOUND, ERROR]))
    console.print(Panel(body, title="Scan terminado", border_style="green", box=ROUNDED))
