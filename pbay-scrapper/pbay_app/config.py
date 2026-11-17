"""Rutas, constantes y lectura de config/settings.json."""
import json
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = APP_DIR / "config" / "settings.json"
OUTPUT_DIR = APP_DIR / "output"
GENERAL_FILE = OUTPUT_DIR / "general.txt"
PLACEHOLDER = "SXXEXX"
DEFAULT_SITE = "https://thepiratebay.bond"
CMD = "PBAY"
DESCRIPTION = "Busca episodios en The Pirate Bay y guarda sus magnet links."
EXAMPLE_QUERY = "Helluva Boss S03E01"


def load_config(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    # Tolera comas finales: { "a": 1, } / [ 1, 2, ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    config = json.loads(raw)
    for key in ("SITE", "SERIE", "QUERY", "SEASON"):
        if key not in config:
            raise ValueError(f"Falta la clave '{key}' en {path}")
    if PLACEHOLDER not in config["QUERY"]:
        raise ValueError(f"QUERY debe contener '{PLACEHOLDER}'")
    return config


def camel_case_filename(serie: str) -> str:
    """'Helluva Boss' -> 'helluvaBoss.txt'"""
    words = serie.split()
    parts = [words[0][:1].lower() + words[0][1:]] + [w[:1].upper() + w[1:] for w in words[1:]]
    name = re.sub(r'[<>:"/\\|?*]', "", "".join(parts))
    return f"{name}.txt"
