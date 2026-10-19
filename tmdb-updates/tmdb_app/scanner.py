"""Escaneo de carpetas locales y comparacion contra los datos de TMDB."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts", ".m2ts",
    ".webm", ".mpg", ".mpeg", ".flv", ".divx", ".ogm",
}
SEASON_DIR_RE = re.compile(r"^season\s*0*(\d+)$", re.IGNORECASE)
SPECIALS_DIR_RE = re.compile(r"^(specials?|season\s*0+)$", re.IGNORECASE)
EPISODE_RE = re.compile(r"(?<![a-z])s(\d{1,2})e(\d{1,3})((?:-?e\d{1,3})*)", re.IGNORECASE)
EXTRA_EP_RE = re.compile(r"e(\d{1,3})", re.IGNORECASE)
YEAR_SUFFIX_RE = re.compile(r"^(.*?)\s*\((\d{4})\)\s*$")
SKIP_DIRS = {"$recycle.bin", "system volume information"}

# Tags de temporada / serie
COMPLETE, INCOMPLETE, MISSING, NAMING_ERROR, UPCOMING, EXTRA = (
    "COMPLETE", "INCOMPLETE", "MISSING", "NAMING_ERROR", "UPCOMING", "EXTRA")
OK, NOT_FOUND, ERROR = "OK", "NOT_FOUND", "ERROR"
# Estados de episodio
EP_OK, EP_MISSING, EP_AVAILABLE, EP_TBA, EP_EXTRA = "OK", "MISSING", "AVAILABLE", "TBA", "EXTRA"
FINISHED_STATUSES = {"Ended", "Canceled"}


@dataclass
class LocalSeason:
    number: int
    folder: str
    episodes: set[int] = field(default_factory=set)
    naming_errors: list[str] = field(default_factory=list)


@dataclass
class LocalSeries:
    folder: str
    path: Path
    library: Path
    seasons: dict[int, LocalSeason] = field(default_factory=dict)
    loose_files: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return strip_year(self.folder)

    @property
    def year(self) -> int | None:
        match = YEAR_SUFFIX_RE.match(self.folder)
        return int(match.group(2)) if match else None


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def parse_episodes(filename: str) -> tuple[int, list[int]] | None:
    """'Show - S01E02E03 - x.mkv' -> (1, [2, 3]); 'S01E01-E03' -> (1, [1, 2, 3])."""
    match = EPISODE_RE.search(filename)
    if not match:
        return None
    season, first = int(match.group(1)), int(match.group(2))
    numbers = [first] + [int(n) for n in EXTRA_EP_RE.findall(match.group(3) or "")]
    if "-" in (match.group(3) or "") and len(numbers) == 2 and numbers[1] > numbers[0]:
        numbers = list(range(numbers[0], numbers[1] + 1))
    return season, numbers


def scan_season_folder(number: int, folder: Path) -> LocalSeason:
    season = LocalSeason(number=number, folder=folder.name)
    for file in sorted(folder.iterdir()):
        if not is_video(file):
            continue
        parsed = parse_episodes(file.name)
        if parsed is None:
            season.naming_errors.append(file.name)
        elif parsed[0] != number:
            season.naming_errors.append(f"{file.name}  (dice S{parsed[0]:02d}, esta en {folder.name})")
        else:
            season.episodes.update(parsed[1])
    return season


def scan_local_series(path: Path, library: Path) -> LocalSeries:
    series = LocalSeries(folder=path.name, path=path, library=library)
    for entry in sorted(path.iterdir()):
        if entry.is_dir():
            if SPECIALS_DIR_RE.match(entry.name):
                continue
            match = SEASON_DIR_RE.match(entry.name)
            if not match:
                continue
            number = int(match.group(1))
            scanned = scan_season_folder(number, entry)
            if number in series.seasons:  # "Season 1" y "Season 01" a la vez
                target = series.seasons[number]
                target.episodes |= scanned.episodes
                target.naming_errors += scanned.naming_errors
                target.folder += f" + {entry.name}"
            else:
                series.seasons[number] = scanned
        elif is_video(entry):
            series.loose_files.append(entry.name)
    return series


def discover_series(tv_paths: list[Path]) -> tuple[list[tuple[Path, Path]], list[Path]]:
    """Regresa ([(carpeta de serie, biblioteca)], bibliotecas no disponibles)."""
    found, unavailable = [], []
    for library in tv_paths:
        if not library.is_dir():
            unavailable.append(library)
            continue
        for entry in sorted(library.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and not entry.name.startswith(".") and entry.name.lower() not in SKIP_DIRS:
                found.append((entry, library))
    return found, unavailable


def strip_year(folder: str) -> str:
    """'Breaking Bad (2008)' -> 'Breaking Bad'."""
    match = YEAR_SUFFIX_RE.match(folder or "")
    return match.group(1) if match else (folder or "")


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", strip_year(text).lower())


def pick_match(results: list[dict], title: str, year: int | None) -> dict | None:
    norm = normalize(title)
    exact = [r for r in results
             if normalize(r.get("name", "")) == norm or normalize(r.get("original_name", "")) == norm]
    pool = exact or results
    if year:
        pool = [r for r in pool if (r.get("first_air_date") or "")[:4] == str(year)] or pool
    return pool[0] if pool else None


def parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def episode_state(have: bool, in_tmdb: bool, air_date: date | None, today: date) -> str:
    if not in_tmdb:
        return EP_EXTRA
    if have:
        return EP_OK
    if air_date is None:
        return EP_TBA
    return EP_MISSING if air_date <= today else EP_AVAILABLE


def evaluate(local: LocalSeries, tv: dict, today: date) -> dict:
    """Combina la carpeta local con los datos de TMDB y genera el registro de la serie."""
    tmdb_seasons = {n: data for n, data in tv.get("season_data", {}).items() if n > 0}
    season_air = {s["season_number"]: s.get("air_date") for s in tv.get("seasons", [])}
    local_seasons = {n: s for n, s in local.seasons.items() if n > 0}

    seasons = []
    for number in sorted(set(tmdb_seasons) | set(local_seasons)):
        loc = local_seasons.get(number)
        tdata = tmdb_seasons.get(number)
        tmdb_eps = {ep["episode_number"]: ep for ep in (tdata or {}).get("episodes", [])}
        have = loc.episodes if loc else set()

        episodes = []
        any_aired = False
        for ep_num in sorted(set(tmdb_eps) | have):
            ep = tmdb_eps.get(ep_num)
            air = parse_date(ep.get("air_date")) if ep else None
            any_aired |= bool(air and air <= today)
            episodes.append({
                "number": ep_num,
                "code": f"S{number:02d}E{ep_num:02d}",
                "name": ep.get("name") if ep else None,
                "airDate": air.isoformat() if air else None,
                "state": episode_state(ep_num in have, ep is not None, air, today),
            })

        if tdata is None:
            tag = EXTRA
        elif loc is None:
            tag = MISSING if any_aired else UPCOMING
        elif loc.naming_errors:
            tag = NAMING_ERROR
        elif all(e["state"] in (EP_OK, EP_EXTRA) for e in episodes):
            tag = COMPLETE
        elif not any_aired and not have:
            tag = UPCOMING
        else:
            tag = INCOMPLETE

        seasons.append({
            "number": number,
            "folder": loc.folder if loc else None,
            "tag": tag,
            "airDate": season_air.get(number),
            "tmdbEpisodes": len(tmdb_eps),
            "localEpisodes": len(have & set(tmdb_eps)),
            "namingErrors": loc.naming_errors if loc else [],
            "episodes": episodes,
        })

    tags = [s["tag"] for s in seasons if s["tag"] != EXTRA]
    if local.loose_files or NAMING_ERROR in tags:
        series_tag = NAMING_ERROR
    elif not tags or all(t == UPCOMING for t in tags):
        series_tag = UPCOMING
    elif all(t in (COMPLETE, UPCOMING) for t in tags):
        series_tag = OK
    else:
        series_tag = INCOMPLETE

    status = tv.get("status")
    return {
        **base_record(local),
        "tmdbId": tv["id"],
        "tmdbName": tv.get("name"),
        "status": status,
        "firstAirDate": tv.get("first_air_date"),
        "tag": series_tag,
        "finished": status in FINISHED_STATUSES and series_tag == OK,
        "seasons": seasons,
    }


def base_record(local: LocalSeries) -> dict:
    return {
        "folder": local.folder,
        "path": str(local.path),
        "library": str(local.library),
        "tmdbId": None,
        "tmdbName": None,
        "status": None,
        "firstAirDate": None,
        "tag": NOT_FOUND,
        "finished": False,
        "lastScan": datetime.now().isoformat(timespec="seconds"),
        "error": None,
        "looseFiles": local.loose_files,
        "seasons": [],
    }
