"""Biblioteca de películas (`TMDB movie -ls`): recorre MOVIE_PATHS/<género>, detecta películas y colecciones
(hasta MAX_DEPTH niveles), valida los nombres contra TMDB con un cache en data/movies.json y baja el poster
(folder.jpg / folder.png) a las carpetas que no lo tienen."""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR
from .movie import POSTER_NAMES, Genre, safe_folder_name
from .scanner import VIDEO_EXTENSIONS
from .tmdb_client import TmdbClient, TmdbError

MOVIE_CACHE_FILE = DATA_DIR / "movies.json"
MAX_DEPTH = 3  # género/colección/subcolección/película
EXTRA_DIRS = {"subs", "subtitles", "sub", "extras", "extra", "featurettes", "sample", "samples", "bonus",
              "behind the scenes", "deleted scenes", "trailers", "other", "specials", "artwork", "covers"}

MOVIE, COLLECTION = "movie", "collection"
# Estados
OK, RENAME, REVIEW, NOT_FOUND = "OK", "RENAME", "REVIEW", "NOT_FOUND"

PAREN_YEAR_RE = re.compile(r"^(.*?)\s*\((\d{4})\)")
EXACT_FORMAT_RE = re.compile(r"^(.+?) \((\d{4})\)$")
BARE_YEAR_RE = re.compile(r"^(.*\S)[\s._]+(\d{4})$")
COLLECTION_WORDS_RE = re.compile(r"\b(collection|trilogy|triology|saga|series|quadrilogy|anthology)\b", re.I)


# ---------------------------------------------------------------- nombres

def norm(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower().replace("&", "and"))


def clean_query(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[._]+", " ", text)).strip(" -")


def folder_year(name: str) -> int | None:
    match = PAREN_YEAR_RE.match(name)
    return int(match.group(2)) if match and match.group(1).strip() else None


def search_candidates(name: str) -> list[tuple[str, int | None]]:
    """'Heretic (2024) (1080p)' -> [('Heretic', 2024)]; 'Obsession 2026' -> [('Obsession 2026', None), ('Obsession', 2026)]."""
    match = PAREN_YEAR_RE.match(name)
    if match and match.group(1).strip():
        return [(clean_query(match.group(1)), int(match.group(2)))]
    match = BARE_YEAR_RE.match(name)
    if match and 1900 <= int(match.group(2)) <= 2100:
        return [(clean_query(name), None), (clean_query(match.group(1)), int(match.group(2)))]
    return [(clean_query(name), None)]


def release_year(movie: dict) -> int | None:
    value = (movie.get("release_date") or "")[:4]
    return int(value) if value.isdigit() else None


# ---------------------------------------------------------------- árbol local

@dataclass
class Node:
    kind: str
    name: str
    path: Path
    poster: str | None = None
    children: list["Node"] = field(default_factory=list)
    status: str | None = None
    suggested: str | None = None
    entry: dict | None = None
    poster_created: bool = False
    error: str | None = None

    @property
    def movie_count(self) -> int:
        return 1 if self.kind == MOVIE else sum(c.movie_count for c in self.children)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def to_json(self) -> dict:
        e = self.entry or {}
        data = {"type": self.kind, "name": self.name, "path": str(self.path), "status": self.status}
        if self.kind == MOVIE:
            data.update({
                "year": folder_year(self.name),
                "suggestedName": self.suggested,
                "tmdbId": e.get("tmdbId"),
                "tmdbTitle": e.get("title"),
                "tmdbOriginalTitle": e.get("originalTitle"),
                "tmdbYear": e.get("year"),
            })
        else:
            data.update({"tmdbId": e.get("tmdbId"), "tmdbName": e.get("title"), "count": self.movie_count})
        data.update({"poster": self.poster, "posterCreated": self.poster_created, "error": self.error})
        if self.kind == COLLECTION:
            data["items"] = [c.to_json() for c in self.children]
        return data


def find_poster(path: Path) -> str | None:
    return next((name for name in POSTER_NAMES if (path / name).is_file()), None)


def scan_folder(path: Path, depth: int = 1) -> Node | None:
    """Película si tiene videos directos; colección si tiene subcarpetas con películas.
    En el primer nivel una carpeta sin videos cuenta como película (vacía, .iso, etc.)."""
    try:
        entries = list(path.iterdir())
    except OSError:
        return Node(MOVIE, path.name, path, error="No se pudo leer la carpeta")
    if any(e.suffix.lower() in VIDEO_EXTENSIONS and e.is_file() for e in entries):
        return Node(MOVIE, path.name, path, find_poster(path))
    subdirs = sorted((e for e in entries if e.is_dir() and not e.name.startswith((".", "$"))
                      and e.name.lower() not in EXTRA_DIRS), key=lambda e: e.name.lower())
    children = []
    if depth < MAX_DEPTH:
        children = [n for n in (scan_folder(d, depth + 1) for d in subdirs) if n]
    if children:
        return Node(COLLECTION, path.name, path, find_poster(path), children)
    if depth == 1 or not subdirs:
        return Node(MOVIE, path.name, path, find_poster(path))
    return None


def scan_genre(genre: Genre) -> list[Node]:
    nodes = []
    for entry in sorted(genre.path.iterdir(), key=lambda e: e.name.lower()):
        if entry.is_dir() and not entry.name.startswith((".", "$")):
            node = scan_folder(entry)
            if node:
                nodes.append(node)
    return nodes


# ---------------------------------------------------------------- cache

class MovieCache:
    """data/movies.json: el match de TMDB por nombre de carpeta (sin importar el género donde esté).
    Para corregir un match: pon "tmdbId": N y "manual": true en la entrada y borra "title"."""

    def __init__(self, path: Path = MOVIE_CACHE_FILE):
        self.path = path
        self.movies: dict[str, dict] = {}
        self.collections: dict[str, dict] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.movies = data.get("movies", {})
            self.collections = data.get("collections", {})

    def table(self, kind: str) -> dict[str, dict]:
        return self.movies if kind == MOVIE else self.collections

    @staticmethod
    def key(name: str) -> str:
        return name.casefold()

    def get(self, node: Node) -> dict | None:
        return self.table(node.kind).get(self.key(node.name))

    def put(self, node: Node, entry: dict) -> None:
        self.table(node.kind)[self.key(node.name)] = entry

    def prune(self, nodes: list[Node], roots: list[Path], full: bool = True) -> list[str]:
        """Quita las entradas de carpetas que ya no existen. Solo toca entradas cuya ruta está bajo una
        carpeta de MOVIE_PATHS disponible (si M: no está conectado no se borra nada de M:)."""
        seen = {(n.kind, self.key(n.name)) for n in nodes}
        available = [os.path.normcase(str(r)) + os.sep for r in roots]
        removed = []
        for kind in (MOVIE, COLLECTION):
            table = self.table(kind)
            for key, entry in list(table.items()):
                if (kind, key) in seen:
                    continue
                path = os.path.normcase(entry.get("path") or "")
                if (not path and full) or (path and any(path.startswith(root) for root in available)):
                    removed.append(entry.get("folder") or key)
                    del table[key]
        return sorted(removed, key=str.lower)

    def locate(self, genre: Genre, nodes: list[Node]) -> None:
        """Guarda dónde está cada carpeta (género, colección y ruta); se actualiza en cada corrida."""
        def visit(node: Node, collection: str | None) -> None:
            entry = self.get(node)
            if entry is not None:
                location = {"folder": node.name, "genre": genre.name, "collection": collection, "path": str(node.path)}
                rest = {k: v for k, v in entry.items() if k not in location}
                self.put(node, {**location, **rest})
            for child in node.children:
                visit(child, node.name)
        for node in nodes:
            visit(node, None)

    def needs_lookup(self, node: Node, refresh: bool) -> bool:
        entry = self.get(node)
        if entry is None:
            return True
        if entry.get("manual"):
            return bool(entry.get("tmdbId")) and not entry.get("title")
        return refresh

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sort = lambda d: dict(sorted(d.items()))
        payload = {"updated": datetime.now().isoformat(timespec="seconds"),
                   "movies": sort(self.movies), "collections": sort(self.collections)}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)


# ---------------------------------------------------------------- TMDB

def pick_movie(results: list[dict], query: str, year: int | None) -> tuple[dict | None, bool, str | None]:
    """(película, seguro, título que coincidió). Seguro = título exacto y año que cuadra, o un único
    título exacto claramente más conocido que los demás."""
    target = norm(query)

    def matched_title(r):
        if norm(r.get("title")) == target:
            return r.get("title")
        if norm(r.get("original_title")) == target:
            return r.get("original_title")
        return None

    exact = [r for r in results if matched_title(r)]
    if year:
        for tolerance in (0, 1):
            hits = [r for r in exact if release_year(r) and abs(release_year(r) - year) <= tolerance]
            if hits:
                return hits[0], True, matched_title(hits[0])
        if exact:
            return exact[0], False, matched_title(exact[0])
    elif exact:
        ranked = sorted(exact, key=lambda r: r.get("vote_count") or 0, reverse=True)
        top = ranked[0].get("vote_count") or 0
        second = ranked[1].get("vote_count") or 0 if len(ranked) > 1 else 0
        sure = len(ranked) == 1 or (top >= 50 and top >= 5 * second)
        return ranked[0], sure, matched_title(ranked[0])
    return (results[0], False, results[0].get("title")) if results else (None, False, None)


def movie_entry(movie: dict | None, confident: bool, matched: str | None, query: str, manual: bool = False) -> dict:
    entry = {"query": query, "tmdbId": None, "checked": datetime.now().isoformat(timespec="seconds")}
    if movie:
        entry.update({
            "tmdbId": movie["id"],
            "title": movie.get("title"),
            "originalTitle": movie.get("original_title"),
            "matchedTitle": matched or movie.get("title"),
            "year": release_year(movie),
            "posterPath": movie.get("poster_path"),
            "confident": confident,
        })
    if manual:
        entry["manual"] = True
    return entry


def lookup_movie(client: TmdbClient, node: Node, cached: dict | None) -> dict:
    if cached and cached.get("manual") and cached.get("tmdbId"):
        movie = client._get(f"/movie/{cached['tmdbId']}")
        return movie_entry(movie, True, movie.get("title"), node.name, manual=True)
    best = None
    for query, year in search_candidates(node.name):
        movie, confident, matched = pick_movie(client.search_movie(query, year), query, year)
        if movie and confident:
            return movie_entry(movie, True, matched, query)
        if movie and best is None:
            best = movie_entry(movie, False, matched, query)
    return best or movie_entry(None, False, None, search_candidates(node.name)[0][0])


def collection_entry(data: dict, query: str, confident: bool, overlap: int, manual: bool = False) -> dict:
    entry = {"query": query, "tmdbId": data["id"], "title": data.get("name"), "posterPath": data.get("poster_path"),
             "confident": confident, "matchedMovies": overlap,
             "checked": datetime.now().isoformat(timespec="seconds")}
    if manual:
        entry["manual"] = True
    return entry


def lookup_collection(client: TmdbClient, node: Node, cached: dict | None, child_ids: set[int]) -> dict:
    """Una colección solo es segura si TMDB incluye películas que tienes dentro de la carpeta
    ('Batman' en DC Universe no es la Batman Collection de live action)."""
    if cached and cached.get("manual") and cached.get("tmdbId"):
        data = client._get(f"/collection/{cached['tmdbId']}")
        return collection_entry(data, node.name, True, 0, manual=True)

    query = clean_query(COLLECTION_WORDS_RE.sub(" ", node.name)) or node.name
    candidates: dict[int, dict] = {}
    for result in client._get("/search/collection", query=query).get("results", [])[:5]:
        candidates[result["id"]] = result
    # Las colecciones a las que pertenecen las películas de adentro
    for movie_id in list(child_ids)[:3]:
        belongs = client._get(f"/movie/{movie_id}").get("belongs_to_collection")
        if belongs:
            candidates.setdefault(belongs["id"], belongs)

    best, best_overlap = None, 0
    for collection_id in candidates:
        data = client._get(f"/collection/{collection_id}")
        overlap = len({part["id"] for part in data.get("parts", [])} & child_ids)
        if overlap > best_overlap:
            best, best_overlap = data, overlap
    if best is None:
        return {"query": query, "tmdbId": None, "checked": datetime.now().isoformat(timespec="seconds")}
    exact_name = norm(COLLECTION_WORDS_RE.sub(" ", best.get("name", ""))) == norm(query)
    # Seguro: la colección cubre al menos la mitad de tus películas de la carpeta (así 'Pixar' no se vuelve
    # la colección de Monsters, Inc.) y coinciden 2+, o el nombre es exacto, o es la única película
    covers_half = best_overlap * 2 >= len(child_ids)
    confident = covers_half and (best_overlap >= 2 or exact_name or len(child_ids) == 1)
    return collection_entry(best, query, confident, best_overlap)


def child_movie_ids(node: Node, cache: "MovieCache") -> set[int]:
    ids = set()
    for child in node.walk():
        if child.kind == MOVIE:
            entry = cache.get(child)
            if entry and entry.get("tmdbId"):
                ids.add(entry["tmdbId"])
    return ids


def apply_status(node: Node, entry: dict | None) -> None:
    node.entry = entry
    if not entry or not entry.get("tmdbId"):
        node.status = NOT_FOUND
        return
    if node.kind == COLLECTION:
        node.status = OK if entry.get("confident") else REVIEW
        return
    title = entry.get("matchedTitle") or entry.get("title") or ""
    try:
        node.suggested = safe_folder_name(title, entry.get("year"))
    except Exception:
        node.suggested = None
    if not entry.get("confident"):
        node.status = REVIEW
        return
    match = EXACT_FORMAT_RE.match(node.name)
    names = {norm(entry.get("title")), norm(entry.get("originalTitle")), norm(entry.get("matchedTitle"))}
    if match and int(match.group(2)) == entry.get("year") and norm(match.group(1)) in names:
        node.status, node.suggested = OK, None
    else:
        node.status = RENAME


def wants_poster(node: Node) -> bool:
    e = node.entry or {}
    return not node.poster and e.get("confident") and bool(e.get("posterPath"))


def download_poster(client: TmdbClient, node: Node) -> None:
    try:
        data, ext = client.download_image(node.entry["posterPath"])
        target = node.path / f"folder{ext}"
        target.write_bytes(data)
        node.poster, node.poster_created = target.name, True
    except (TmdbError, OSError) as exc:
        node.error = f"No se pudo guardar el poster: {exc}"
