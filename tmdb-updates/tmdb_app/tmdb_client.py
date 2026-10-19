import threading
import time

import requests

MAX_ATTEMPTS = 5


class TmdbError(Exception):
    pass


class TmdbClient:
    """Cliente minimo de la API v3 de TMDB. Acepta API key v3 o token v4 (Bearer)."""

    APPEND_LIMIT = 20  # TMDB permite hasta 20 sub-recursos por append_to_response

    def __init__(self, api_key: str, base_url: str, language: str = "en-US", timeout: int = 20):
        self._api_key = api_key
        self._bearer = api_key.startswith("eyJ")
        self.base_url = base_url
        self.language = language
        self.timeout = timeout
        self._local = threading.local()

    @property
    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers["Accept"] = "application/json"
            if self._bearer:
                session.headers["Authorization"] = f"Bearer {self._api_key}"
            self._local.session = session
        return session

    def _redact(self, text: str) -> str:
        return text.replace(self._api_key, "***")

    def _get(self, path: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        params.setdefault("language", self.language)
        if not self._bearer:
            params["api_key"] = self._api_key

        for attempt in range(MAX_ATTEMPTS):
            last = attempt == MAX_ATTEMPTS - 1
            try:
                resp = self._session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                if last:
                    raise TmdbError(f"Error de red: {self._redact(str(exc))}") from None
                time.sleep(1 + attempt)
                continue

            if resp.status_code == 429 and not last:
                time.sleep(float(resp.headers.get("Retry-After", 1 + attempt)))
                continue
            if resp.status_code >= 500 and not last:
                time.sleep(1 + attempt)
                continue
            if resp.status_code == 401:
                raise TmdbError("API key invalida o sin permisos (401)")
            if resp.status_code == 404:
                raise TmdbError(f"No existe en TMDB: {path}")
            if not resp.ok:
                raise TmdbError(f"TMDB {resp.status_code}: {self._redact(resp.text[:200])}")
            return resp.json()

        raise TmdbError(f"TMDB no respondio tras {MAX_ATTEMPTS} intentos: {path}")

    def search_tv(self, query: str, year: int | None = None) -> list[dict]:
        results = self._get("/search/tv", query=query, first_air_date_year=year).get("results", [])
        if not results and year:
            results = self._get("/search/tv", query=query).get("results", [])
        return results

    def get_tv(self, tv_id: int) -> dict:
        """Detalles de la serie + episodios de cada temporada en `season_data` {numero: season}."""
        details = self._get(f"/tv/{tv_id}")
        numbers = [s["season_number"] for s in details.get("seasons", []) if s.get("season_number", 0) > 0]
        season_data: dict[int, dict] = {}
        for i in range(0, len(numbers), self.APPEND_LIMIT):
            chunk = numbers[i:i + self.APPEND_LIMIT]
            extra = self._get(f"/tv/{tv_id}", append_to_response=",".join(f"season/{n}" for n in chunk))
            for n in chunk:
                if f"season/{n}" in extra:
                    season_data[n] = extra[f"season/{n}"]
        details["season_data"] = season_data
        return details
