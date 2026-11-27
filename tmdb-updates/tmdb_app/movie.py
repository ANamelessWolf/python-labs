"""Comando `movie`: renombra la carpeta de una película a 'Nombre (Año)' y le pone el poster de TMDB
como folder.jpg / folder.png."""
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .scanner import normalize
from .tmdb_client import TmdbClient

INVALID_CHARS_RE = re.compile(r'[<>"/\\|?*\x00-\x1f]')
POSTER_NAMES = ("folder.jpg", "folder.jpeg", "folder.png", "folder.webp")


class MovieError(Exception):
    pass


@dataclass
class MovieResult:
    previous_path: Path
    path: Path
    renamed: bool
    poster: Path | None
    tmdb_id: int
    title: str
    year: int | None
    warnings: list[str]

    def to_json(self) -> dict:
        return {
            "command": "movie",
            "path": str(self.path),
            "folder": self.path.name,
            "previousPath": str(self.previous_path),
            "renamed": self.renamed,
            "poster": str(self.poster) if self.poster else None,
            "tmdbId": self.tmdb_id,
            "tmdbTitle": self.title,
            "year": self.year,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------- argumentos

def split_command_line(raw: str) -> list[str]:
    """Separa una linea de comandos de Windows tratando '\\' como caracter normal (no como escape)."""
    tokens, current, quoted, has_token = [], [], False, False
    for ch in raw:
        if ch == '"':
            quoted, has_token = not quoted, True
        elif ch in " \t" and not quoted:
            if has_token:
                tokens.append("".join(current))
            current, has_token = [], False
        else:
            current.append(ch)
            has_token = True
    if has_token:
        tokens.append("".join(current))
    return tokens


def repair_windows_argv(argv: list[str]) -> list[str]:
    """Con Tab, cmd/PowerShell completan carpetas como "Moonrise Kingdom (2012)\\". En Windows ese \\" final
    escapa la comilla y los argumentos siguientes se pegan a la ruta. Si se detecta, se vuelve a leer la
    linea de comandos original sin interpretar '\\' como escape."""
    if os.name != "nt" or not any('"' in a for a in argv):
        return argv
    try:
        import ctypes
        get_command_line = ctypes.windll.kernel32.GetCommandLineW
        get_command_line.restype = ctypes.c_wchar_p
        tokens = split_command_line(get_command_line())
    except Exception:
        return argv
    script = Path(sys.argv[0]).name.lower()
    for i, token in enumerate(tokens):
        if Path(token).name.lower() == script:
            return tokens[i + 1:]
    return argv


def clean_dir_arg(value: str) -> str:
    """Quita comillas y la diagonal final que deja el autocompletado ('.\\Pelicula\\' -> '.\\Pelicula')."""
    value = value.strip().strip('"').strip("'").strip()
    stripped = value.rstrip("\\/")
    return stripped if stripped and not stripped.endswith(":") else value


def resolve_folder(value: str, movie_paths: list[Path]) -> Path:
    raw = Path(clean_dir_arg(value))
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw, *(root / raw for root in movie_paths)]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    where = "" if raw.is_absolute() else f" (busqué en {Path.cwd()}" + \
        (f" y en MOVIE_PATHS" if movie_paths else "") + ")"
    raise MovieError(f"No existe la carpeta '{raw}'{where}.")


# ---------------------------------------------------------------- TMDB

def release_year(movie: dict) -> int | None:
    value = (movie.get("release_date") or "")[:4]
    return int(value) if value.isdigit() else None


def pick_movie(results: list[dict], title: str, year: int | None) -> dict | None:
    norm = normalize(title)
    exact = [r for r in results
             if normalize(r.get("title", "")) == norm or normalize(r.get("original_title", "")) == norm]
    pool = exact or results
    if year:
        pool = [r for r in pool if release_year(r) == year] or pool
    return pool[0] if pool else None


def safe_folder_name(name: str, year: int | None) -> str:
    name = name.replace(":", " -")
    name = INVALID_CHARS_RE.sub("", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if not name:
        raise MovieError("El nombre de la película queda vacío después de quitar caracteres inválidos.")
    return f"{name} ({year})" if year else name


# ---------------------------------------------------------------- proceso

def format_movie(client: TmdbClient, folder: Path, name: str, year: int | None, status=None) -> MovieResult:
    """Busca la película, descarga el poster, renombra la carpeta y guarda el poster como folder.<ext>.
    Si la búsqueda o la descarga fallan no se toca nada."""
    warnings: list[str] = []
    status = status or (lambda _msg: None)

    status(f"Buscando '{name}' en TMDB…")
    movie = pick_movie(client.search_movie(name, year), name, year)
    if movie is None:
        raise MovieError(f"Sin resultados en TMDB para '{name}'" + (f" ({year})" if year else "") + ".")

    tmdb_year = release_year(movie)
    if year and tmdb_year and tmdb_year != year:
        warnings.append(f"TMDB tiene '{movie.get('title')}' en {tmdb_year}, no en {year}; se usa {tmdb_year}.")
    final_year = tmdb_year or year
    if not final_year:
        warnings.append("No se conoce el año; la carpeta queda sin '(YYYY)'.")

    image = None
    if movie.get("poster_path"):
        status(f"Descargando poster de '{movie.get('title')}'…")
        image = client.download_image(movie["poster_path"])
    else:
        warnings.append(f"'{movie.get('title')}' no tiene poster en TMDB.")

    target = folder.parent / safe_folder_name(name, final_year)
    renamed = target.name != folder.name
    if renamed:
        same_folder = target.exists() and os.path.samefile(target, folder)  # solo cambia mayúsculas
        if target.exists() and not same_folder:
            raise MovieError(f"Ya existe la carpeta '{target}'.")
        try:
            folder.rename(target)
        except OSError as exc:
            raise MovieError(f"No se pudo renombrar '{folder.name}' (¿está abierta en otro programa?): {exc}") from None

    poster = None
    if image:
        data, ext = image
        poster = target / f"folder{ext}"
        for old in POSTER_NAMES:
            old_path = target / old
            if old_path.name != poster.name and old_path.exists():
                old_path.unlink()
        poster.write_bytes(data)

    return MovieResult(folder, target, renamed, poster, movie["id"], movie.get("title") or name,
                       final_year, warnings)


# ---------------------------------------------------------------- mover a un género

COPY_CHUNK = 8 * 1024 * 1024


@dataclass
class Genre:
    name: str
    path: Path


@dataclass
class MoveResult:
    previous_path: Path
    path: Path
    genre: Genre
    created_genre: bool
    moved: bool

    def to_json(self) -> dict:
        return {
            "command": "movie-move",
            "path": str(self.path),
            "folder": self.path.name,
            "previousPath": str(self.previous_path),
            "genre": self.genre.name,
            "genrePath": str(self.genre.path),
            "createdGenre": self.created_genre,
            "moved": self.moved,
        }


def list_genres(movie_paths: list[Path]) -> list[Genre]:
    """Subcarpetas de cada carpeta de MOVIE_PATHS, ordenadas por nombre."""
    genres = []
    for root in movie_paths:
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if entry.is_dir() and not entry.name.startswith((".", "$")):
                genres.append(Genre(entry.name, entry))
    return sorted(genres, key=lambda g: (g.name.lower(), str(g.path)))


def find_genre(genres: list[Genre], name: str) -> Genre | None:
    wanted = name.strip().lower()
    return next((g for g in genres if g.name.lower() == wanted), None)


def safe_genre_name(name: str) -> str:
    clean = re.sub(r"\s+", " ", INVALID_CHARS_RE.sub("", name.replace(":", " -"))).strip().rstrip(". ")
    if not clean:
        raise MovieError(f"Nombre de género inválido: '{name}'")
    return clean


def folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def same_drive(a: Path, b: Path) -> bool:
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except OSError:
        return False


def copy_tree(src: Path, dst: Path, advance) -> None:
    """Copia src -> dst en bloques, llamando advance(bytes) para la barra de progreso."""
    import shutil
    dst.mkdir(parents=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            copy_tree(item, target, advance)
            continue
        with item.open("rb") as fin, target.open("wb") as fout:
            while chunk := fin.read(COPY_CHUNK):
                fout.write(chunk)
                advance(len(chunk))
        shutil.copystat(item, target)
    shutil.copystat(src, dst)


def move_folder(src: Path, dst: Path, start=None, advance=None) -> None:
    """Mueve la carpeta. En la misma unidad es un rename; entre unidades copia con progreso y luego borra
    el original (si la copia falla, se borra la copia parcial y el original queda intacto)."""
    import shutil
    if same_drive(src, dst.parent):
        try:
            src.rename(dst)
            return
        except OSError as exc:
            raise MovieError(f"No se pudo mover '{src.name}' (¿está abierta en otro programa?): {exc}") from None
    (start or (lambda _total: None))(folder_size(src))
    try:
        copy_tree(src, dst, advance or (lambda _n: None))
    except BaseException as exc:
        shutil.rmtree(dst, ignore_errors=True)
        if isinstance(exc, OSError):
            raise MovieError(f"Falló la copia a '{dst}', el original queda intacto: {exc}") from None
        raise
    try:
        shutil.rmtree(src)
    except OSError as exc:
        raise MovieError(f"Se copió a '{dst}' pero no se pudo borrar el original '{src}': {exc}") from None

