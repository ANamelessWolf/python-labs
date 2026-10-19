import json
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = APP_DIR / "config" / "settings.json"
DATA_DIR = APP_DIR / "data"
LIBRARY_FILE = DATA_DIR / "library.json"

DEFAULT_BASE_URL = "https://api.themoviedb.org/3"


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    tv_paths: list[Path]
    movie_paths: list[Path]
    api_key: str
    base_url: str
    language: str


def load_settings(path: Path = CONFIG_FILE) -> Settings:
    if not path.exists():
        raise ConfigError(
            f"No existe {path}. Copia config/settings.example.json a config/settings.json y llena tu API key."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} no es un JSON valido: {exc}") from exc

    media = data.get("MEDIA", {})
    tmdb = data.get("TMDB", {})
    api_key = (tmdb.get("API_KEY") or "").strip()
    if not api_key:
        raise ConfigError(f"TMDB.API_KEY esta vacio en {path}")

    tv_paths = [Path(p) for p in media.get("TV_PATHS", [])]
    if not tv_paths:
        raise ConfigError(f"MEDIA.TV_PATHS esta vacio en {path}")

    return Settings(
        tv_paths=tv_paths,
        movie_paths=[Path(p) for p in media.get("MOVIE_PATHS", [])],
        api_key=api_key,
        base_url=(tmdb.get("TMDB_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
        language=tmdb.get("LANGUAGE") or "en-US",
    )
