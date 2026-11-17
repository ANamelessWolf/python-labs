"""Reporte de consola: tabla para elegir, linea de cada episodio y resumen."""
from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.table import Table
from rich.text import Text

from .scraper import Result


def results_table(results: list[Result], episode_code: str, saved: set[str] | None = None) -> Table:
    """Tabla de resultados; con saved marca con ✔ los magnets que ya estan en el archivo."""
    table = Table(title=f"[bold]{episode_code}[/bold] · {len(results)} resultados", title_justify="left",
                  header_style="bold cyan", border_style="grey37", show_lines=False)
    table.add_column("#", style="bold yellow", justify="right")
    table.add_column("Nombre", overflow="fold")
    table.add_column("Tamaño", justify="right", style="magenta", no_wrap=True)
    table.add_column("Seeds", justify="right", style="bold green", no_wrap=True)
    table.add_column("Leechers", justify="right", style="red", no_wrap=True)
    for i, r in enumerate(results, start=1):
        title = f"[blue]✔[/blue] {r.title}" if saved and r.magnet in saved else r.title
        table.add_row(str(i), title, r.size, f"▲ {r.seeders}", f"▼ {r.leechers}")
    return table


def ask_choice(console: Console, results: list[Result], episode_code: str) -> Result | None:
    console.print(results_table(results, episode_code))
    index = IntPrompt.ask("    [bold]¿Cuál agrego?[/bold] [dim](0 = omitir)[/dim]",
                          choices=[str(i) for i in range(len(results) + 1)], show_choices=False, default=1,
                          console=console)
    return results[index - 1] if index else None


def episode_line(prefix: str, label: str, status: str, style: str, seeders: str | None = None) -> Text:
    line = Text("    ")
    line.append(f"{prefix}: ", style="bold cyan")
    line.append(label, style="white" if style == "green" else "dim")
    if seeders is not None:
        line.append(f" (▲ {seeders} seeds)", style="green")
    line.append(f" [{status}]", style=f"bold {style}")
    return line


def render_results(console: Console, output) -> int:
    """--list sin --json: la tabla de resultados de cada busqueda (✔ = ya esta en el archivo)."""
    for search in output.searches:
        if search.results:
            console.print()
            console.print(results_table(search.results, search.code or search.query, output.saved))
    return render_summary(console, output)


def render_summary(console: Console, output) -> int:
    """Dibuja el resumen de un Output (search.py). Regresa 1 si alguna busqueda fallo."""
    stats = output.stats
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[green]Copied[/green]", str(stats["Copied"]))
    table.add_row("[blue]Saved[/blue]", str(stats["Saved"]))
    table.add_row("[yellow]Skipped[/yellow]", str(stats["Skipped"]))
    table.add_row("[red]Not Found[/red]", str(stats["Not Found"]))
    if stats["Found"]:
        table.add_row("[cyan]Found[/cyan]", str(stats["Found"]))
    if stats["Error"]:
        table.add_row("[bold red]Error[/bold red]", str(stats["Error"]))
    console.print()
    console.print(Panel(table, title="[bold]Resumen[/bold]", border_style="cyan", expand=False))
    console.print(f"[cyan]Archivo:[/cyan] {output.path}", soft_wrap=True)
    return 0 if stats["Error"] == 0 else 1
