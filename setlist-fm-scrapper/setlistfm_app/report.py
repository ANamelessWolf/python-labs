"""Reporte de consola (rich): setlist de un concierto, lista de conciertos del año y selector."""
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .api import Setlist
from .config import DATE_FORMAT
from .songs import Match, SongSearch


def render_setlist(console: Console, setlist: Setlist, albums: list[str | None]) -> None:
    console.print()
    console.print(Text(f"{setlist.artist} Setlist", style="bold magenta"))
    console.print(Text(setlist.place, style="cyan"))
    if setlist.tour:
        line = Text("Tour: ", style="bold cyan")
        line.append(setlist.tour, style="white")
        console.print(line)
    console.print()
    console.print(Rule("[bold yellow]Songs list[/bold yellow]", style="yellow", align="left"))
    console.print()
    if not setlist.songs:
        console.print("[yellow]El setlist todavía no tiene canciones registradas.[/yellow]")
    for song, album in zip(setlist.songs, albums):
        line = Text(song.title, style="white")
        if album:
            line.append(" / ", style="dim")
            line.append(album, style="magenta")
        console.print(line)


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count != 1 else ''}"


def concert_line(setlist: Setlist) -> Text:
    """'[11/20/2026] Gorillaz at Lugar, Ciudad, País'"""
    line = Text(f"[{setlist.date.strftime(DATE_FORMAT)}] ", style="bold yellow")
    line.append(setlist.artist, style="bold magenta")
    line.append(" at ", style="dim")
    line.append(setlist.place, style="white")
    return line


def render_year(console: Console, band: str, years: str, setlists: list[Setlist]) -> None:
    console.print()
    console.print(Rule(f"[bold magenta]{band}[/bold magenta] [dim]·[/dim] [bold yellow]{years}[/bold yellow] "
                       f"[dim]({len(setlists)} concierto{'s' if len(setlists) != 1 else ''})[/dim]",
                       style="magenta", align="left"))
    for setlist in setlists:
        line = concert_line(setlist)
        if not setlist.songs:
            line.append("  (sin canciones)", style="dim")
        console.print(line)


def render_song(console: Console, band: str, years: str, search: SongSearch) -> None:
    """Conciertos donde se toco la cancion (con su link) y el resumen."""
    console.print()
    console.print(Rule(f"[bold magenta]{band}[/bold magenta] [dim]·[/dim] [bold cyan]\"{search.query}\"[/bold cyan] "
                       f"[dim]·[/dim] [bold yellow]{years}[/bold yellow]", style="magenta", align="left"))
    if not search.matches:
        console.print(f"[yellow]No se encontró \"{search.query}\" en {plural(search.checked, 'setlist')}.[/yellow]")
    for match in search.matches:
        console.print(concert_line(match.setlist))
        detail = Text(" " * 13)
        detail.append(" / ".join(match.titles), style="cyan")
        detail.append(f"  {match.setlist.url}", style="dim")
        console.print(detail, soft_wrap=True)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[green]Conciertos[/green]", str(len(search.matches)))
    table.add_row("[green]Veces tocada[/green]", str(search.plays))
    if len(search.titles) > 1:
        for title, count in search.titles.most_common():
            table.add_row("", f"[cyan]{title}[/cyan] [dim]×{count}[/dim]")
    if search.matches:
        table.add_row("[cyan]Última vez[/cyan]", when(search.last))
        table.add_row("[cyan]Primera vez[/cyan]", when(search.first) + " [dim](en el rango)[/dim]")
    table.add_row("[blue]Revisados[/blue]", plural(search.checked, "setlist"))
    if search.empty:
        table.add_row("[yellow]Sin canciones[/yellow]", f"{search.empty} [dim](no se sabe si se tocó)[/dim]")
    console.print()
    console.print(Panel(table, title="[bold]Resumen[/bold]", border_style="cyan", expand=False))


def when(match: Match) -> str:
    return f"{match.setlist.date.strftime(DATE_FORMAT)} · {match.setlist.place}"


def ask_setlist(console: Console, setlists: list[Setlist]) -> Setlist:
    """Varios conciertos el mismo dia (dos funciones, otro artista con nombre parecido...): pregunta cual."""
    table = Table(title=f"[bold]{len(setlists)} setlists en la misma fecha[/bold]", title_justify="left",
                  header_style="bold cyan", border_style="grey37")
    table.add_column("#", style="bold yellow", justify="right")
    table.add_column("Artista", style="magenta")
    table.add_column("Lugar", overflow="fold")
    table.add_column("Canciones", justify="right", style="green")
    for i, s in enumerate(setlists, start=1):
        table.add_row(str(i), s.artist, s.place, str(len(s.songs)))
    console.print(table)
    index = IntPrompt.ask("[bold]¿Cuál?[/bold]", choices=[str(i) for i in range(1, len(setlists) + 1)],
                          show_choices=False, default=1, console=console)
    return setlists[index - 1]
