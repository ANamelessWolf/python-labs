"""Rutas, constantes y lectura de config/settings.json."""
import json
import os
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = APP_DIR / "config" / "settings.json"
CACHE_FILE = APP_DIR / "cache" / "albums.json"
SETLIST_CACHE_DIR = APP_DIR / "cache" / "setlists"
CMD = "SETLISTFM"
DESCRIPTION = "Busca setlists de conciertos en setlist.fm (API oficial) y los imprime o exporta como playlist."
DATE_FORMAT = "%m/%d/%Y"          # formato de -d y de las fechas que se imprimen
API_KEY_ENV = "SETLISTFM_API_KEY"  # si existe, tiene prioridad sobre API_KEY del settings.json
PRIVACY_VALUES = ("PRIVATE", "UNLISTED", "PUBLIC")

DEFAULTS = {
    "API_KEY": "",
    "API_URL": "https://api.setlist.fm/rest/1.0",
    "LANGUAGE": "en",
    "PRIVACY": "PUBLIC",
    "ITUNES_COUNTRY": "US",
    "OUTPUT_DIR": "output",
}


def load_config(path: Path) -> dict:
    """Lee settings.json (tolera comas finales) y completa las claves que falten con DEFAULTS."""
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    config = {**DEFAULTS, **json.loads(raw)}
    config["API_KEY"] = os.environ.get(API_KEY_ENV) or config["API_KEY"]
    if not config["API_KEY"] or config["API_KEY"].startswith("TU_"):
        raise ValueError(f"Falta API_KEY en {path} (o la variable de entorno {API_KEY_ENV})")
    config["PRIVACY"] = str(config["PRIVACY"]).upper()
    if config["PRIVACY"] not in PRIVACY_VALUES:
        raise ValueError(f"PRIVACY debe ser uno de {', '.join(PRIVACY_VALUES)}")
    return config


def output_dir(config: dict) -> Path:
    """OUTPUT_DIR relativo se toma desde la carpeta del proyecto."""
    path = Path(config["OUTPUT_DIR"])
    return path if path.is_absolute() else APP_DIR / path


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name).strip() or "setlist"
