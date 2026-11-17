"""Salida en JSON (opción --json): los mismos datos que el reporte de report.py, sin formato de consola.
Estados como constante (NOT_FOUND), seeds/leechers como números y tamaños en bytes y como texto."""
import re

from .scraper import Result
from .search import Output, Search

SIZE_UNITS = {"B": 1, "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3, "TIB": 1024 ** 4,
              "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4}


def parse_size(text: str) -> int | None:
    """'1.4 GiB' -> 1503238554. None si no se reconoce."""
    match = re.search(r"([\d.,]+)\s*([KMGT]?i?B)\b", text.replace("\xa0", " "), re.IGNORECASE)
    if not match:
        return None
    return round(float(match.group(1).replace(",", "")) * SIZE_UNITS[match.group(2).upper()])


def parse_int(text: str) -> int | None:
    digits = text.replace(",", "").strip()
    return int(digits) if digits.isdigit() else None


def state_key(state: str) -> str:
    """'Not Found' -> 'NOT_FOUND'."""
    return state.upper().replace(" ", "_")


def result_json(result: Result, saved: set[str] | None = None) -> dict:
    """Un torrent. Con saved (modo --list) agrega "saved": si el magnet ya esta en el archivo."""
    data = {
        "title": result.title,
        "magnet": result.magnet,
        "size": result.size.replace("\xa0", " "),
        "sizeBytes": parse_size(result.size),
        "seeders": parse_int(result.seeders),
        "leechers": parse_int(result.leechers),
        "url": result.view or None,
    }
    if saved is not None:
        data["saved"] = result.magnet in saved
    return data


def search_json(search: Search, saved: set[str] | None = None) -> dict:
    return {
        "season": search.season,
        "episode": search.episode,
        "code": search.code,
        "query": search.query,
        "state": state_key(search.state),
        "resultCount": search.result_count,
        "error": search.error,
        "result": result_json(search.result) if search.result else None,
        # Con --list: todos los resultados en el orden del sitio; sin --list, null
        "results": [result_json(r, saved) for r in search.results] if saved is not None else None,
    }


def search_result(command: str, output: Output, **context) -> dict:
    """Resultado de 'series' o 'query': el contexto de la busqueda, el resumen y cada busqueda."""
    return {
        "command": command,
        **context,
        "list": output.list_only,
        "file": str(output.path),
        "total": len(output.searches),
        "stats": {state_key(state): count for state, count in output.stats.items()},
        "items": [search_json(s, output.saved if output.list_only else None) for s in output.searches],
    }
