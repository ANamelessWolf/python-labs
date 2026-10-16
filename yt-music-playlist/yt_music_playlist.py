"""
yt_music_playlist.py
--------------------
Sincroniza playlists locales (JSON en Inputs/) con tu cuenta de YouTube Music.

- Si la playlist remota no existe (se busca por nombre) se crea con las canciones del JSON.
- Si ya existe, se reemplaza su contenido por el del JSON.

Uso:
    python yt_music_playlist.py                 # menu interactivo
    python yt_music_playlist.py --list          # lista playlists de Inputs
    python yt_music_playlist.py --sync Radiohead
    python yt_music_playlist.py --sync-all
    python yt_music_playlist.py --setup-auth    # genera browser.json / oauth.json
"""

import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from ytmusicapi import YTMusic, setup, setup_oauth
from ytmusicapi.auth.oauth import OAuthCredentials

APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.json"
CONFIG_EXAMPLE = APP_DIR / "config.example.json"
CACHE_FILE = APP_DIR / "cache" / "search_cache.json"
BATCH_SIZE = 50
PRIVACY_VALUES = ("PRIVATE", "UNLISTED", "PUBLIC")
# Headers copiados del navegador (sobre todo Firefox) que rompen las peticiones de ytmusicapi:
# content-encoding: gzip hace que YouTube espere un body comprimido y responda algo que no es JSON.
BAD_BROWSER_HEADERS = {"content-encoding", "content-length", "host", "connection", "te", "priority", "alt-used"}


# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(CONFIG_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Se creo {CONFIG_FILE.name} a partir de {CONFIG_EXAMPLE.name}.")
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def app_path(value: str) -> Path:
    """Rutas relativas en config.json se resuelven respecto a la carpeta de la app."""
    p = Path(value)
    return p if p.is_absolute() else APP_DIR / p


def setup_auth(config: dict) -> None:
    auth = config["auth"]
    method = auth.get("method", "browser")
    if method == "browser":
        target = app_path(auth["browser_file"])
        print("Autenticacion por headers del navegador:")
        print("  1. Abre https://music.youtube.com con tu sesion iniciada.")
        print("  2. DevTools (F12) > Network > filtra 'browse' > recarga o navega.")
        print("  3. Click en una peticion POST 'browse' > copia los Request Headers.")
        print("  4. Pegalos aqui y termina con una linea vacia + Ctrl+Z, Enter (Windows).\n")
        setup(filepath=str(target))
        headers = load_browser_headers(target)
        target.write_text(json.dumps(headers, indent=4, ensure_ascii=False), encoding="utf-8")
        print(f"\nOK: credenciales guardadas en {target}")
    elif method == "oauth":
        if not auth.get("client_id") or not auth.get("client_secret"):
            sys.exit("Error: define auth.client_id y auth.client_secret en config.json para usar OAuth.")
        target = app_path(auth["oauth_file"])
        setup_oauth(auth["client_id"], auth["client_secret"], filepath=str(target), open_browser=True)
        print(f"\nOK: token guardado en {target}")
    else:
        sys.exit(f"Error: auth.method desconocido '{method}' (usa 'browser' u 'oauth').")


def load_browser_headers(file: Path) -> dict:
    """Lee browser.json y quita headers problematicos y lineas de peticion ('POST /youtubei/...')."""
    headers = json.loads(file.read_text(encoding="utf-8"))
    return {k: v for k, v in headers.items() if k.lower() not in BAD_BROWSER_HEADERS and " " not in k}


def connect(config: dict) -> YTMusic:
    auth = config["auth"]
    method = auth.get("method", "browser")
    if method == "browser":
        file = app_path(auth["browser_file"])
        if not file.exists():
            sys.exit(f"Error: no existe {file}. Ejecuta primero con --setup-auth.")
        return YTMusic(load_browser_headers(file))
    if method == "oauth":
        file = app_path(auth["oauth_file"])
        if not file.exists():
            sys.exit(f"Error: no existe {file}. Ejecuta primero con --setup-auth.")
        creds = OAuthCredentials(client_id=auth["client_id"], client_secret=auth["client_secret"])
        return YTMusic(str(file), oauth_credentials=creds)
    sys.exit(f"Error: auth.method desconocido '{method}' (usa 'browser' u 'oauth').")


# ---------------------------------------------------------------------------
# Playlists locales
# ---------------------------------------------------------------------------

def load_local_playlists(config: dict) -> list[dict]:
    inputs = app_path(config.get("inputs_dir", "Inputs"))
    inputs.mkdir(exist_ok=True)
    playlists = []
    for file in sorted(inputs.glob("*.json")):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] {file.name}: JSON invalido ({e}), se omite.")
            continue
        errors = validate_playlist(data)
        if errors:
            print(f"[!] {file.name}: " + "; ".join(errors) + " -> se omite.")
            continue
        data["_file"] = file.name
        playlists.append(data)
    return playlists


def validate_playlist(data: dict) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["la raiz debe ser un objeto"]
    if not str(data.get("name", "")).strip():
        errors.append("falta 'name'")
    if data.get("privacy") and data["privacy"] not in PRIVACY_VALUES:
        errors.append(f"'privacy' debe ser uno de {PRIVACY_VALUES}")
    songs = data.get("songs")
    if not isinstance(songs, list):
        errors.append("'songs' debe ser una lista")
        return errors
    for i, s in enumerate(songs, 1):
        if not str(s.get("title", "")).strip() or not str(s.get("artist", "")).strip():
            errors.append(f"cancion #{i} requiere 'title' y 'artist'")
    return errors


def list_local_playlists(playlists: list[dict]) -> None:
    if not playlists:
        print("No hay playlists en Inputs/. Usa Assets/playlist.example.json como plantilla.")
        return
    print()
    for i, p in enumerate(playlists, 1):
        print(f"  {i:>2}. {p['name']:<35} {len(p['songs']):>4} canciones   ({p['_file']})")
    print()


# ---------------------------------------------------------------------------
# Busqueda de canciones
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)  # (Remastered), [Official Video]...
    text = re.sub(r"\b(official|video|audio|lyrics?|remaster(ed)?|hd|hq|4k)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def similarity(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()


def parse_views(views) -> int:
    """'1.2M' -> 1200000, '345K' -> 345000, '1,234' -> 1234."""
    if not views:
        return 0
    m = re.search(r"([\d.,]+)\s*([KMB])?", str(views).upper())
    if not m:
        return 0
    num = float(m.group(1).replace(",", "")) if m.group(2) else float(re.sub(r"[.,]", "", m.group(1)))
    return int(num * {"K": 1e3, "M": 1e6, "B": 1e9}.get(m.group(2), 1))


def artist_matches(result: dict, artist: str) -> bool:
    names = " ".join(a.get("name", "") for a in result.get("artists") or [])
    target = normalize(artist)
    return bool(target) and (target in normalize(names) or similarity(names, artist) >= 0.7
                             or target in normalize(result.get("title", "")))


class SongFinder:
    def __init__(self, yt: YTMusic, config: dict):
        self.yt = yt
        self.min_sim = float(config.get("min_title_similarity", 0.6))
        self.use_cache = bool(config.get("use_search_cache", True))
        self.cache = {}
        if self.use_cache and CACHE_FILE.exists():
            try:
                self.cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.cache = {}

    def save_cache(self) -> None:
        if self.use_cache:
            CACHE_FILE.parent.mkdir(exist_ok=True)
            CACHE_FILE.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False), encoding="utf-8")

    def find(self, song: dict) -> tuple[str | None, str]:
        """Devuelve (videoId, descripcion del resultado)."""
        if song.get("videoId"):
            return song["videoId"], "videoId definido en el JSON"

        title, artist, album = song["title"].strip(), song["artist"].strip(), (song.get("album") or "").strip()
        key = f"{normalize(title)}|{normalize(artist)}|{normalize(album)}"
        if key in self.cache:
            hit = self.cache[key]
            return hit["videoId"], hit["label"] + " (cache)"

        video_id, label = self._search(title, artist, album)
        if video_id:
            self.cache[key] = {"videoId": video_id, "label": label}
        return video_id, label

    def _search(self, title: str, artist: str, album: str) -> tuple[str | None, str]:
        # 1) Canciones oficiales del catalogo de YT Music (nombre + artista + album)
        queries = [f"{title} {artist} {album}", f"{title} {artist}"] if album else [f"{title} {artist}"]
        for query in queries:
            best = self._best_song(self.yt.search(query, filter="songs", limit=20), title, artist, album)
            if best:
                return best["videoId"], f"[oficial] {describe(best)}"

        # 2) Videos (en vivo, covers, unreleased): el mas reproducido que coincida
        videos = [v for v in self.yt.search(f"{title} {artist}", filter="videos", limit=20) if v.get("videoId")]
        matches = [v for v in videos if similarity(v.get("title", ""), title) >= self.min_sim
                   and artist_matches(v, artist)]
        if not matches:  # el titulo de los videos suele incluir al artista: relaja la coincidencia
            matches = [v for v in videos if normalize(title) in normalize(v.get("title", ""))]
        if matches:
            best = max(matches, key=lambda v: parse_views(v.get("views")))
            return best["videoId"], f"[video {best.get('views', '?')} vistas] {describe(best)}"
        return None, "no encontrada"

    def _best_song(self, results: list[dict], title: str, artist: str, album: str) -> dict | None:
        best, best_score = None, 0.0
        for r in results:
            if not r.get("videoId") or not artist_matches(r, artist):
                continue
            title_sim = similarity(r.get("title", ""), title)
            if title_sim < self.min_sim:
                continue
            score = title_sim
            # Desempate: titulo literal igual (evita "Creep (Acoustic)" si se pidio "Creep")
            if r.get("title", "").strip().lower() == title.lower():
                score += 0.1
            if album:
                result_album = (r.get("album") or {}).get("name", "")
                if normalize(result_album) == normalize(album):
                    score += 0.5
                elif similarity(result_album, album) >= 0.8:
                    score += 0.3
            if score > best_score:
                best, best_score = r, score
        return best


def describe(r: dict) -> str:
    artists = ", ".join(a.get("name", "") for a in r.get("artists") or [])
    album = (r.get("album") or {}).get("name")
    return f"{r.get('title')} - {artists}" + (f" ({album})" if album else "")


# ---------------------------------------------------------------------------
# Sincronizacion
# ---------------------------------------------------------------------------

def find_remote_playlist(yt: YTMusic, name: str) -> dict | None:
    target = name.strip().lower()
    for p in yt.get_library_playlists(limit=None):
        if p.get("title", "").strip().lower() == target:
            return p
    return None


def add_in_batches(yt: YTMusic, playlist_id: str, video_ids: list[str]) -> None:
    for i in range(0, len(video_ids), BATCH_SIZE):
        res = yt.add_playlist_items(playlist_id, video_ids[i:i + BATCH_SIZE], duplicates=True)
        if isinstance(res, dict) and "SUCCEEDED" not in str(res.get("status", "")):
            print(f"  [!] Respuesta inesperada al agregar canciones: {res.get('status')}")


def sync_playlist(yt: YTMusic, finder: SongFinder, playlist: dict, config: dict) -> None:
    name = playlist["name"].strip()
    print(f"\n=== {name} ({len(playlist['songs'])} canciones) ===")

    video_ids, missing = [], []
    for i, song in enumerate(playlist["songs"], 1):
        label = f"{song['title']} - {song['artist']}"
        try:
            vid, info = finder.find(song)
        except Exception as e:  # errores de red puntuales no deben abortar toda la playlist
            vid, info = None, f"error: {e}"
        if vid:
            video_ids.append(vid)
            print(f"  {i:>3}. OK   {label}  ->  {info}")
        else:
            missing.append(label)
            print(f"  {i:>3}. FALTA {label}  ({info})")
    finder.save_cache()

    description = playlist.get("description", "")
    privacy = playlist.get("privacy") or config.get("default_privacy", "PRIVATE")
    remote = find_remote_playlist(yt, name)

    if remote and config.get("replace_mode", "clear") == "recreate":
        print(f"  Borrando playlist remota existente ({remote['playlistId']})...")
        yt.delete_playlist(remote["playlistId"])
        remote = None

    if remote is None:
        print("  Creando playlist remota...")
        playlist_id = yt.create_playlist(name, description, privacy_status=privacy)
        if not isinstance(playlist_id, str):
            print(f"  [!] No se pudo crear la playlist: {playlist_id}")
            return
    else:
        playlist_id = remote["playlistId"]
        tracks = yt.get_playlist(playlist_id, limit=None).get("tracks", [])
        removable = [t for t in tracks if t.get("setVideoId")]
        print(f"  Playlist existente: eliminando {len(removable)} canciones...")
        if removable:
            yt.remove_playlist_items(playlist_id, removable)
        if description:
            yt.edit_playlist(playlist_id, description=description)

    if video_ids:
        add_in_batches(yt, playlist_id, video_ids)
    print(f"  Listo: {len(video_ids)} agregadas, {len(missing)} no encontradas.")
    print(f"  https://music.youtube.com/playlist?list={playlist_id}")


def sync_many(yt: YTMusic, playlists: list[dict], config: dict) -> None:
    finder = SongFinder(yt, config)
    for p in playlists:
        try:
            sync_playlist(yt, finder, p, config)
        except Exception as e:
            print(f"  [!] Error sincronizando '{p['name']}': {e}")


def pick_playlist(playlists: list[dict], query: str) -> dict | None:
    """Acepta el numero de la lista, el nombre de la playlist o el nombre del archivo."""
    q = query.strip().lower()
    if q.isdigit() and 1 <= int(q) <= len(playlists):
        return playlists[int(q) - 1]
    for p in playlists:
        if q in (p["name"].strip().lower(), p["_file"].lower(), Path(p["_file"]).stem.lower()):
            return p
    return None


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def menu(config: dict) -> None:
    yt = None
    while True:
        print("\n==== YouTube Music Playlist Sync ====")
        print("  1. Listar playlists de Inputs")
        print("  2. Seleccionar playlist a subir")
        print("  3. Sincronizar todas las playlists")
        print("  4. Salir")
        choice = input("Opcion: ").strip().lstrip("﻿")

        if choice == "4":
            return
        if choice not in ("1", "2", "3"):
            print("Opcion invalida.")
            continue

        playlists = load_local_playlists(config)
        if choice == "1":
            list_local_playlists(playlists)
            continue
        if not playlists:
            list_local_playlists(playlists)
            continue

        yt = yt or connect(config)
        if choice == "2":
            list_local_playlists(playlists)
            selected = pick_playlist(playlists, input("Numero o nombre de la playlist: "))
            if selected:
                sync_many(yt, [selected], config)
            else:
                print("No se encontro esa playlist.")
        else:
            sync_many(yt, playlists, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza playlists JSON con YouTube Music.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="Lista las playlists de Inputs")
    group.add_argument("--sync", metavar="NOMBRE", help="Sincroniza una playlist (nombre, archivo o numero)")
    group.add_argument("--sync-all", action="store_true", help="Sincroniza todas las playlists de Inputs")
    group.add_argument("--setup-auth", action="store_true", help="Configura la autenticacion con YouTube Music")
    args = parser.parse_args()

    config = load_config()
    if args.setup_auth:
        setup_auth(config)
    elif args.list:
        list_local_playlists(load_local_playlists(config))
    elif args.sync:
        playlists = load_local_playlists(config)
        selected = pick_playlist(playlists, args.sync)
        if not selected:
            sys.exit(f"Error: no se encontro la playlist '{args.sync}' en Inputs/.")
        sync_many(connect(config), [selected], config)
    elif args.sync_all:
        sync_many(connect(config), load_local_playlists(config), config)
    else:
        try:
            menu(config)
        except (KeyboardInterrupt, EOFError):
            print()


if __name__ == "__main__":
    main()
