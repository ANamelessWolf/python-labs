"""Peticiones al mirror de The Pirate Bay: busqueda y lectura de la tabla de resultados."""
import time
from dataclasses import dataclass
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) pbay-scrapper"}


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
    # /search/<query>/<pagina>/<orden 99 = default>/<categoria 0 = todas>
    return f"{site.rstrip('/')}/search/{quote(' '.join(query.split()))}/1/99/0"


def fetch_results(session: requests.Session, url: str, retries: int = 3) -> list[Result]:
    for attempt in range(1, retries + 1):
        response = session.get(url, timeout=30)
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 * attempt)
            continue
        response.raise_for_status()
        break
    else:
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for row in soup.select("table#searchResult tr"):
        magnet = row.select_one('a[href^="magnet:"]')
        title_link = row.select_one('a[href*="/torrent/"]')
        if magnet is None or title_link is None:
            continue
        cells = row.find_all("td", recursive=False)
        # Columnas: Type | Name | Uploaded | Magnet | Size | SE | LE | ULed by
        size, seeders, leechers = (
            (cells[4].get_text(" ", strip=True), cells[5].get_text(strip=True), cells[6].get_text(strip=True))
            if len(cells) >= 7 else ("?", "?", "?")
        )
        results.append(Result(title_link.get_text(strip=True), magnet["href"], size, seeders, leechers,
                              urljoin(url, title_link["href"])))
    return results
