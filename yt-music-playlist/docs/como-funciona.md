# Cómo funciona yt-music-playlist

Esta guía recorre la app paso a paso: desde que ejecutas `ytmusic-sync` hasta que la playlist queda en YouTube Music. Todo el código está en [yt_music_playlist.py](../yt_music_playlist.py).

## Vista general

```mermaid
flowchart TD
    A[ytmusic-sync.bat] --> B[Activa conda ytMusic]
    B --> C[yt_music_playlist.py]
    C --> D[load_config: lee config.json]
    D --> E{Argumentos}
    E -- sin argumentos --> F[Menu interactivo]
    E -- --list / --sync / --sync-all --> G[Accion directa]
    E -- --setup-auth --> H[Genera browser.json]
    F --> I[load_local_playlists: lee Inputs/*.json]
    G --> I
    I --> J[connect: sesion de YouTube Music]
    J --> K[sync_playlist por cada playlist]
    K --> L[SongFinder: busca cada cancion]
    L --> M{Existe la playlist remota?}
    M -- no --> N[create_playlist]
    M -- si --> O[Vacia la playlist]
    N --> P[add_in_batches: agrega canciones]
    O --> P
```

## Paso 1: el lanzador `.bat`

[ytmusic-sync.bat](../ytmusic-sync.bat) hace tres cosas:

1. Inicializa Anaconda (`activate.bat`).
2. Activa el ambiente `ytMusic`. Si no existe, muestra un error y termina.
3. Ejecuta `python yt_music_playlist.py` y le pasa todos los argumentos (`%*`).

Usa rutas absolutas (`Z:\dev\py\python-labs\yt-music-playlist`), por eso funciona igual si lo copias a `Z:\bin`.

## Paso 2: la configuración

`load_config()` lee `config.json`. Si no existe, lo crea copiando [config.example.json](../config.example.json).

Las rutas relativas del config (`browser.json`, `Inputs`, etc.) se resuelven con `app_path()` respecto a la carpeta de la app, no respecto a la carpeta desde donde ejecutas el comando. Por eso puedes llamarlo desde cualquier lugar.

| Clave | Para qué se usa |
|---|---|
| `auth.method` | `browser` u `oauth`: define cómo se conecta |
| `inputs_dir` | Carpeta donde están tus playlists JSON |
| `default_privacy` | Privacidad de las playlists nuevas si el JSON no la define |
| `replace_mode` | `clear` (vaciar y rellenar) o `recreate` (borrar y crear) |
| `min_title_similarity` | Qué tan parecido debe ser el título encontrado (0 a 1) |
| `use_search_cache` | Si guarda las búsquedas en `cache/search_cache.json` |

## Paso 3: la autenticación

YouTube Music no tiene una API pública oficial para cuentas personales. La app usa [ytmusicapi](https://ytmusicapi.readthedocs.io/), que se hace pasar por el navegador web de music.youtube.com.

### Modo `browser` (Current Mode)

1. `ytmusic-sync --setup-auth` llama a `setup()` de ytmusicapi, que te pide pegar los headers de una petición de music.youtube.com.
2. Los headers incluyen tu cookie de sesión. Con ellos, las peticiones de la app cuentan como si vinieran de tu navegador.
3. `load_browser_headers()` quita los headers que rompen las peticiones, como `content-encoding: gzip` (que Firefox incluye al copiar) y la línea `POST /youtubei/...`. Después guarda el resultado en `browser.json`.
4. En cada ejecución, `connect()` vuelve a leer y limpiar `browser.json` y crea el objeto `YTMusic`.

Si cierras sesión en el navegador o la cookie expira, las peticiones empiezan a fallar. En ese caso repite `--setup-auth`.

> `browser.json` equivale a tu sesión de Google: no lo compartas. Ya está en `.gitignore`.

### Modo `oauth`

Requiere crear credenciales en Google Cloud (tipo *TVs and Limited Input devices*), poner `client_id` y `client_secret` en el config y ejecutar `--setup-auth`. Se abre el navegador para autorizar y se guarda `oauth.json`. Es más estable a largo plazo, pero más laborioso de configurar.

## Paso 4: leer las playlists locales

`load_local_playlists()` recorre `Inputs/*.json` en orden alfabético y, por cada archivo:

1. Lo carga como JSON. Si está mal formado, avisa y lo omite.
2. Lo valida con `validate_playlist()`:
   - `name` es obligatorio.
   - `privacy`, si existe, debe ser `PRIVATE`, `UNLISTED` o `PUBLIC`.
   - `songs` debe ser una lista y cada canción debe tener `title` y `artist`.
3. Guarda el nombre del archivo en `_file` para mostrarlo en el listado.

El formato completo está en [Assets/playlist.schema.json](../Assets/playlist.schema.json).

## Paso 5: el menú

`menu()` muestra las cuatro opciones en un ciclo:

| Opción | Qué hace |
|---|---|
| 1. Listar | Lee `Inputs/` y muestra nombre, número de canciones y archivo. No se conecta a YouTube. |
| 2. Seleccionar | Muestra la lista y pide un número, el nombre de la playlist o el nombre del archivo (`pick_playlist()`). Sincroniza solo esa. |
| 3. Sincronizar todas | Sincroniza todas las playlists de `Inputs/`, una tras otra. |
| 4. Salir | Termina. `Ctrl+C` también sale limpio. |

Las playlists se vuelven a leer cada vez que eliges una opción, así que puedes editar los JSON sin reiniciar la app. La conexión a YouTube se crea solo la primera vez que se necesita.

Los argumentos `--list`, `--sync NOMBRE` y `--sync-all` hacen lo mismo que las opciones 1, 2 y 3, pero sin el menú.

## Paso 6: buscar cada canción

La clase `SongFinder` convierte cada `{title, artist, album}` en un `videoId` de YouTube.

### 6.1 Atajos

- Si la canción tiene `videoId` en el JSON, se usa directamente y no se busca.
- Si la búsqueda ya se hizo antes, se toma de la caché (`cache/search_cache.json`). La clave es título + artista + álbum normalizados. En la salida aparece como `(cache)`.

### 6.2 Normalización

Para comparar textos, `normalize()`:

- quita acentos (`Canción` → `cancion`)
- pasa todo a minúsculas
- elimina lo que está entre paréntesis o corchetes (`(Remastered)`, `[Official Video]`)
- elimina palabras de ruido: `official`, `video`, `audio`, `lyrics`, `remaster`, `hd`, `4k`...
- deja solo letras y números

`similarity()` devuelve un valor de 0 a 1: 1 si son iguales, 0.9 si uno contiene al otro, y si no, el parecido calculado con `difflib`.

### 6.3 Primero: canciones oficiales

Se busca en el catálogo de **canciones** de YT Music (`filter="songs"`), que contiene las pistas oficiales de los sellos:

1. Consulta `título artista álbum` (si hay álbum).
2. Si no hay resultado válido, consulta `título artista`.

Cada resultado se descarta si el artista no coincide (`artist_matches()`) o si el título tiene una similitud menor a `min_title_similarity`. Los que pasan reciben un puntaje:

| Criterio | Puntos |
|---|---|
| Similitud del título | 0 a 1 |
| Título literalmente igual (evita `Creep (Acoustic)` si pediste `Creep`) | +0.1 |
| Álbum igual al indicado | +0.5 |
| Álbum parecido (p. ej. `OK Computer` vs `OK Computer OKNOTOK`) | +0.3 |

Gana el puntaje más alto. En la salida aparece como `[oficial]`.

### 6.4 Después: videos

Si no hay canción oficial (versiones en vivo, covers, unreleased), se busca en **videos** (`filter="videos"`):

1. Se quedan los videos con título parecido y artista coincidente.
2. Si ninguno pasa, se relaja el criterio: basta con que el título del video contenga el título de la canción, porque en los videos el artista suele venir en el título (`Radiohead - Creep (Live)`).
3. Gana el de **más reproducciones**. `parse_views()` convierte textos como `1.2M` o `345K` en números.

En la salida aparece como `[video 1.2M vistas]`.

### 6.5 Si no se encuentra

La canción se marca como `FALTA`, se omite y la sincronización continúa con la siguiente. Un error de red en una canción tampoco detiene la playlist.

## Paso 7: sincronizar con YouTube Music

`sync_playlist()` hace lo siguiente:

1. **Busca todas las canciones** (paso 6) e imprime una línea por canción con `OK` o `FALTA`. Al final guarda la caché.
2. **Busca la playlist remota** con `find_remote_playlist()`: recorre toda tu biblioteca y compara el título sin distinguir mayúsculas.
3. **Decide qué hacer:**
   - **No existe:** la crea con `create_playlist()` usando el nombre, la descripción y la privacidad del JSON.
   - **Existe y `replace_mode` es `clear` (default):** obtiene sus canciones actuales y las elimina todas. Si el JSON tiene descripción, la actualiza. La playlist conserva su ID y su URL.
   - **Existe y `replace_mode` es `recreate`:** borra la playlist completa y crea una nueva. La URL cambia.
4. **Agrega las canciones** con `add_in_batches()` en grupos de 50, en el orden del JSON. Se permiten duplicados si los pusiste a propósito.
5. **Muestra el resumen:** cuántas se agregaron, cuántas faltaron y la URL de la playlist.

Si una playlist completa falla, `sync_many()` muestra el error y sigue con la siguiente.

## Ejemplo de salida

```
=== Radiohead (5 canciones) ===
    1. OK   Paranoid Android - Radiohead  ->  [oficial] Paranoid Android - Radiohead (OK Computer OKNOTOK 1997 2017)
    2. OK   Weird Fishes/Arpeggi - Radiohead  ->  [oficial] Weird Fishes / Arpeggi - Radiohead (In Rainbows)
    3. OK   Creep - Radiohead  ->  [oficial] Creep - Radiohead (Creep) (cache)
    4. OK   Lift - Radiohead  ->  [oficial] Lift - Radiohead (OK Computer OKNOTOK 1997 2017)
    5. OK   True Love Waits - Radiohead  ->  [oficial] True Love Waits - Radiohead (A Moon Shaped Pool)
  Playlist existente: eliminando 5 canciones...
  Listo: 5 agregadas, 0 no encontradas.
  https://music.youtube.com/playlist?list=PL...
```

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `no existe ...browser.json` | Aún no configuraste la autenticación | `ytmusic-sync --setup-auth` |
| Todas las canciones con `error: Expecting value...` | Headers inválidos o sesión expirada | Repite `--setup-auth` |
| Se eligió una versión que no querías | El catálogo de YT Music no tiene la versión pedida | Pon el `videoId` exacto en el JSON |
| Un resultado viejo se repite aunque cambiaste el JSON | Viene de la caché | Borra la entrada en `cache/search_cache.json` o pon `use_search_cache: false` |
| `no se pudo activar el entorno conda "ytMusic"` | El ambiente no existe | `conda env create -f environment.yml` |
