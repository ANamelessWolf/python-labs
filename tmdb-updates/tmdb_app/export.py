"""Salida en JSON (opción --json): los mismos datos que los reportes de report.py,
sin formato de consola. Fechas en ISO (YYYY-MM-DD), tamaños en bytes y como texto."""
from collections import Counter
from datetime import date
from pathlib import Path

from . import report
from .scanner import EP_MISSING, ERROR, EXTRA, INCOMPLETE, NAMING_ERROR, NOT_FOUND, OK, UPCOMING

TAG_ORDER = [OK, INCOMPLETE, NAMING_ERROR, UPCOMING, NOT_FOUND, ERROR]


def library_info(library) -> dict:
    return {"lastScan": library.last_scan, "totalSeries": len(library.series)}


def size(value: int | None) -> dict:
    return {"sizeBytes": value, "size": report.fmt_size(value) if value is not None else None}


def tag_counts(tags: list[str]) -> dict[str, int]:
    counts = Counter(tags)
    ordered = {t: counts[t] for t in TAG_ORDER if counts.get(t)}
    ordered.update({t: n for t, n in counts.items() if t not in ordered})
    return ordered


def library_name(path: str) -> str:
    return Path(path).name or path


def episode_json(ep: dict, today: date) -> dict:
    air = report.parse_date(ep.get("airDate"))
    return {
        "code": ep["code"],
        "number": ep["number"],
        "name": ep.get("name") or "",
        "airDate": ep.get("airDate"),
        "daysFromToday": (air - today).days if air else None,
        "state": report.live_state(ep, today),
    }


def season_json(season: dict, today: date, episodes: bool) -> dict:
    data = {
        "number": season["number"],
        "folder": season.get("folder"),
        "tag": season["tag"],
        "localEpisodes": season.get("localEpisodes"),
        "tmdbEpisodes": None if season["tag"] == EXTRA else season.get("tmdbEpisodes"),
        "airDate": season.get("airDate"),
        **size(season.get("sizeBytes")),
        "namingErrors": season.get("namingErrors", []),
    }
    if episodes:
        data["episodes"] = [episode_json(ep, today) for ep in season.get("episodes", [])]
    return data


def series_json(series: dict, today: date, episodes: bool = False) -> dict:
    """Resumen de una serie; con episodes=True incluye los episodios de cada temporada."""
    return {
        "name": series["folder"],
        "path": series["path"],
        "library": library_name(series["library"]),
        "libraryPath": series["library"],
        "status": series.get("status"),
        "tag": series["tag"],
        "finished": bool(series.get("finished")),
        "tmdbId": series.get("tmdbId"),
        "tmdbName": series.get("tmdbName"),
        "firstAirDate": series.get("firstAirDate"),
        "maxSeason": series.get("maxSeason"),
        "lastScan": series.get("lastScan"),
        "error": series.get("error"),
        **size(series.get("sizeBytes")),
        "looseFiles": series.get("looseFiles", []),
        "seasons": [season_json(s, today, episodes) for s in series.get("seasons", [])],
    }


def group_by_library(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for item in items:
        group = groups.setdefault(item["libraryPath"], {"name": item["library"], "path": item["libraryPath"],
                                                         "series": []})
        group["series"].append(item)
    return list(groups.values())


# ---------------------------------------------------------------- comandos

def status_tv(library, today: date) -> dict:
    all_series = library.sorted_series()
    return {
        "command": "status",
        **library_info(library),
        "tags": tag_counts([s["tag"] for s in all_series]),
        "libraries": group_by_library([series_json(s, today) for s in all_series]),
    }


def status_series(library, series: dict, today: date) -> dict:
    return {"command": "status", **library_info(library), "series": series_json(series, today, episodes=True)}


def updates(library, today: date, start: date, end: date) -> dict:
    items = []
    for air, series, ep, state in report.collect_updates(library, today, start, end):
        items.append({
            "date": air.isoformat(),
            "daysFromToday": (air - today).days,
            "series": series["folder"],
            "library": library_name(series["library"]),
            "code": ep["code"],
            "title": ep.get("name") or "",
            "state": state,
        })
    missing = sum(1 for i in items if i["state"] == EP_MISSING)
    return {
        "command": "updates",
        **library_info(library),
        "today": today.isoformat(),
        "from": start.isoformat(),
        "to": end.isoformat(),
        "missing": missing,
        "upcoming": len(items) - missing,
        "items": items,
    }


def missing(library, series_list: list[dict], today: date) -> dict:
    result, total_eps, whole = [], 0, 0
    for series in series_list:
        seasons = report.missing_seasons(series, today)
        if not seasons:
            continue
        entry = series_json(series, today)
        entry["seasons"] = []
        for season, episodes in seasons:
            data = season_json(season, today, episodes=False)
            data["wholeSeason"] = not episodes
            data["missingEpisodes"] = [episode_json(ep, today) for ep in episodes]
            data["missingCount"] = len(episodes) if episodes else season["tmdbEpisodes"]
            total_eps += data["missingCount"]
            whole += 0 if episodes else 1
            entry["seasons"].append(data)
        result.append(entry)
    return {
        "command": "missing",
        **library_info(library),
        "totalEpisodes": total_eps,
        "seriesWithMissing": len(result),
        "wholeSeasons": whole,
        "series": result,
    }


def series_list(library) -> dict:
    items = [{
        "name": s["folder"],
        "library": library_name(s["library"]),
        "libraryPath": s["library"],
        "status": s.get("status"),
        "tag": s["tag"],
        "tmdbId": s.get("tmdbId"),
        "tmdbName": s.get("tmdbName"),
        "nameDiffers": report.name_differs(s),
    } for s in library.sorted_series()]
    return {"command": "list", **library_info(library), "series": items}


def scan_result(library, scanned: list[dict], skipped: int, removed: list[str], unavailable: list,
                today: date, detail: bool) -> dict:
    problems = [{"name": s["folder"], "path": s["path"], "tag": s["tag"], "error": s.get("error")}
                for s in scanned if s["tag"] in (NOT_FOUND, ERROR) or s.get("error")]
    data = {
        "command": "scan",
        **library_info(library),
        "scanned": len(scanned),
        "skipped": skipped,
        "tags": tag_counts([s["tag"] for s in scanned]),
        "removed": removed,
        "unavailable": [str(p) for p in unavailable],
        "problems": problems,
    }
    if detail and scanned:
        data["series"] = series_json(scanned[0], today, episodes=True)
    return data


def series_change(command: str, library, series: dict, message: str, today: date) -> dict:
    """fix y unfollow: qué se hizo y cómo quedó la serie."""
    return {"command": command, **library_info(library), "message": message,
            "series": series_json(series, today, episodes=True)}
