# yt-music-playlist

App de consola que sincroniza playlists definidas en JSON (`Inputs/`) con tu cuenta de YouTube Music, usando [ytmusicapi](https://ytmusicapi.readthedocs.io/).

- **No existe** la playlist remota (se busca por nombre en tu biblioteca) → se crea con todas las canciones del JSON.
- **Ya existe** → se vacía y se llena con el contenido del JSON (mantiene la misma URL). Con `"replace_mode": "recreate"` se borra y se crea de nuevo.

Explicación detallada paso a paso: [docs/como-funciona.md](docs/como-funciona.md).

## Instalación

```bat
conda env create -f environment.yml
```

(o bien `conda create -n ytMusic python=3.12` + `pip install ytmusicapi`)

## Configuración

Al primer uso se genera `config.json` a partir de `config.example.json`:

| Clave | Descripción |
|---|---|
| `auth.method` | `browser` (recomendado) u `oauth` |
| `auth.browser_file` | Archivo con los headers del navegador (`browser.json`) |
| `auth.oauth_file`, `client_id`, `client_secret` | Solo para OAuth (requiere credenciales de Google Cloud tipo *TVs and Limited Input devices*) |
| `inputs_dir` | Carpeta de playlists (default `Inputs`) |
| `default_privacy` | `PRIVATE`, `UNLISTED` o `PUBLIC` para playlists nuevas |
| `replace_mode` | `clear` (vaciar y rellenar) o `recreate` (borrar y crear) |
| `min_title_similarity` | Umbral 0–1 para aceptar un resultado de búsqueda |
| `use_search_cache` | Guarda las búsquedas en `cache/search_cache.json` para no repetirlas |

### Autenticación (browser)

```bat
ytmusic-sync --setup-auth
```

1. Abre https://music.youtube.com con tu sesión iniciada.
2. F12 → Network → filtra `browse` → navega por la página.
3. Clic en una petición POST `browse` → copia los *Request Headers*.
4. Pégalos en la consola y termina con `Ctrl+Z` + `Enter`.

Esto crea `browser.json` (ignorado en git). Si en algún momento falla la autenticación, repite el proceso.

## Formato de playlist

El esquema está en [Assets/playlist.schema.json](Assets/playlist.schema.json) y hay una plantilla en [Assets/playlist.example.json](Assets/playlist.example.json). Copia la plantilla a `Inputs/<Nombre>.json`:

```json
{
  "name": "Radiohead",
  "description": "Lo mejor de Radiohead",
  "privacy": "PRIVATE",
  "songs": [
    { "title": "Paranoid Android", "artist": "Radiohead", "album": "OK Computer" },
    { "title": "True Love Waits", "artist": "Radiohead" }
  ]
}
```

`title` y `artist` son obligatorios; `album` es opcional. Puedes forzar un video con `"videoId"`.

## Búsqueda de canciones

1. Busca en el catálogo de **canciones oficiales** de YT Music por `nombre + artista + álbum` (y luego sin álbum). Se elige el resultado cuyo artista coincide y con mejor similitud de título, priorizando el álbum indicado.
2. Si no hay canción oficial (en vivo, covers, unreleased), busca en **videos** y toma el **más reproducido** que coincida.
3. Las canciones no encontradas se reportan en consola y se omiten.

## Uso

```bat
ytmusic-sync                  :: menú interactivo
ytmusic-sync --list
ytmusic-sync --sync Radiohead :: por nombre, archivo o número
ytmusic-sync --sync-all
```

Menú:

```
1. Listar playlists de Inputs
2. Seleccionar playlist a subir
3. Sincronizar todas las playlists
4. Salir
```

Para usarlo desde cualquier lugar copia `ytmusic-sync.bat` a `Z:\bin` (usa rutas absolutas).
