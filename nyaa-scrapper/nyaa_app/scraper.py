"""Peticiones a nyaa.si: busqueda, pagina de detalle y filtro de idioma."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) nyaa-scrapper"}
# Palabras que identifican cada idioma en la descripcion del torrent (Audio, Dub/Sub Tracks, MediaInfo...)
LANGUAGES = {
    "es": ["spanish", "español", "espanol", "castellano", "latino", "latin american", "spa", "esp"],
    "en": ["english", "inglés", "ingles", "eng"],
    "ja": ["japanese", "japonés", "japones", "日本語", "jpn"],
    "pt": ["portuguese", "português", "portugues"],
    "fr": ["french", "français", "francais", "fre", "fra"],
}
DETAIL_WORKERS = 4


@dataclass
class Result:
    title: str
    magnet: str
    size: str
    seeders: str
    leechers: str
    view: str = ""


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def build_url(site: str, query: str) -> str:
    params = {"f": 0, "c": "0_0", "q": " ".join(query.split())}
    return f"{site.rstrip('/')}/?{urlencode(params)}"


def get_page(session: requests.Session, url: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        response = session.get(url, timeout=30)
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 * attempt)
            continue
        response.raise_for_status()
        break
    else:
        response.raise_for_status()
    return response.text


def fetch_results(session: requests.Session, url: str) -> list[Result]:
    soup = BeautifulSoup(get_page(session, url), "html.parser")
    results = []
    for row in soup.select("table.torrent-list tbody tr"):
        magnet = row.select_one('a[href^="magnet:"]')
        title_link = row.select_one('td[colspan="2"] a[href^="/view/"]:not(.comments)')
        if magnet is None or title_link is None:
            continue
        cells = row.find_all("td", recursive=False)
        # Columnas: Category | Name | Link | Size | Date | Seeders | Leechers | Downloads
        size, seeders, leechers = (
            (cells[3].get_text(" ", strip=True), cells[5].get_text(strip=True), cells[6].get_text(strip=True))
            if len(cells) >= 7 else ("?", "?", "?")
        )
        title = title_link.get("title") or title_link.get_text(strip=True)
        results.append(Result(title, magnet["href"], size, seeders, leechers, urljoin(url, title_link["href"])))
    return results


def language_pattern(codes: list[str]) -> re.Pattern:
    """['es'] -> regex con 'spanish', 'español', ... como palabra completa. Un codigo desconocido se busca tal cual."""
    words = [w for code in codes for w in LANGUAGES.get(code.lower(), [code])]
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.IGNORECASE)


def fetch_description(session: requests.Session, url: str) -> str:
    soup = BeautifulSoup(get_page(session, url), "html.parser")
    node = soup.select_one("#torrent-description")
    return node.get_text("\n", strip=True) if node else ""


def filter_by_language(session: requests.Session, results: list[Result], pattern: re.Pattern) -> list[Result]:
    """Abre la pagina de detalle de cada resultado y deja solo los que mencionan el idioma (titulo o descripcion)."""
    def matches(result: Result) -> bool:
        if pattern.search(result.title):
            return True
        try:
            return bool(pattern.search(fetch_description(session, result.view)))
        except requests.RequestException:
            return False

    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        keep = list(pool.map(matches, results))
    return [r for r, ok in zip(results, keep) if ok]
