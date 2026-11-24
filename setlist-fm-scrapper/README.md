# SetList FM Scrapper

Busca el setlist de un concierto en [setlist.fm](https://www.setlist.fm) por banda y fecha, o lista los conciertos
de una banda en un año. Usa la [API oficial de setlist.fm](https://api.setlist.fm/docs/1.0/index.html) y completa
el álbum de cada canción con la [iTunes Search API](https://performance-partners.apple.com/search-api) (gratis, sin
key), porque setlist.fm no lo guarda.

Con `--json` (o `-o`) el setlist sale en el formato de playlist de [`yt-music-playlist`](../yt-music-playlist/README.md),
listo para copiarlo a su carpeta `Inputs`.

## Instalación

```powershell
conda env create -f environment.yml      # crea el entorno "WebScrapper" (compartido con nyaa/pbay)
copy config\settings.example.json config\settings.json
```

Pide tu API key (gratis, uso no comercial) en <https://www.setlist.fm/settings/api> con tu cuenta de setlist.fm y
ponla en `API_KEY`. También puedes definir la variable de entorno `SETLISTFM_API_KEY`, que tiene prioridad.

`SETLISTFM.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Configuración

```json
{
  "API_KEY": "TU_API_KEY",
  "API_URL": "https://api.setlist.fm/rest/1.0",
  "LANGUAGE": "en",
  "PRIVACY": "PUBLIC",
  "ITUNES_COUNTRY": "US",
  "OUTPUT_DIR": "output"
}
```

| Clave | Descripción |
|---|---|
| `API_KEY` | API key de setlist.fm (obligatoria) |
| `API_URL` | URL base de la API |
| `LANGUAGE` | Idioma de los nombres de ciudades y países (`en`, `es`, `de`, `fr`, `it`, `pl`, `pt`, `tr`) |
| `PRIVACY` | `privacy` del JSON de playlist: `PRIVATE`, `UNLISTED` o `PUBLIC` |
| `ITUNES_COUNTRY` | Tienda de iTunes donde se buscan los álbumes (`US`, `MX`, ...) |
| `OUTPUT_DIR` | Carpeta de `-o` sin ruta; relativa al proyecto o absoluta (p. ej. `Z:\\dev\\py\\python-labs\\yt-music-playlist\\Inputs`) |

## Comandos

| Comando | Qué hace |
|---|---|
| `SETLISTFM -b "Gorillaz" -d "11/20/2026"` | Setlist del concierto en esa fecha (`MM/DD/YYYY`): `Canción / Álbum` |
| `SETLISTFM -b "Gorillaz" -d "11/20/2026" --json` | El setlist como playlist JSON (ver abajo) |
| `SETLISTFM -b "Gorillaz" -d "11/20/2026" -o` | Además guarda el JSON en `OUTPUT_DIR\<name>.json` |
| `SETLISTFM -b "Gorillaz" -d "11/20/2026" -o "ruta"` | Guarda el JSON en `ruta` (un `.json` o una carpeta) |
| `SETLISTFM -b "Gorillaz" -d "11/20/2026" --no-album` | No busca álbumes (más rápido) |
| `SETLISTFM -b "Gorillaz" -y 2026` | Conciertos de la banda en ese año, del más reciente al más antiguo |
| `SETLISTFM -b "Gorillaz" -y 2024-2026` | Conciertos en un rango de años |
| `SETLISTFM -b "Gorillaz" -y 2026 --json` | La lista de conciertos como JSON (también acepta `-o`) |
| `SETLISTFM -b "Gorillaz" -s "eastwood" -y 2020-2026` | Conciertos donde se tocó una canción que **contiene** el texto, con el link a cada setlist y un resumen (ver [Buscar una canción](#buscar-una-canción-s)) |
| `SETLISTFM -b "Gorillaz" -s "eastwood" -y 2026 --json` | Lo mismo como JSON (también acepta `-o`) |
| `SETLISTFM -b "Gorillaz" -s "eastwood" -y 2026 --refresh` | Ignora la caché de setlists y vuelve a pedir todos los años |
| `SETLISTFM -b "Gorillaz" -y 2026 -c ruta\otra.json` | Usa otro archivo de configuración |
| `SETLISTFM -h` | Ayuda con todos los comandos |

Notas:

- `artistName` de la API busca por aproximación; si alguno de los resultados coincide exactamente con la banda, se
  descartan los demás (bandas tributo, etc.).
- Si hay varios setlists el mismo día, se pregunta cuál (con `--json` o sin consola se toma el primero).
- Se omiten las canciones de cinta (`tape`: intros y outros que no se tocan en vivo) y las que no tienen nombre.
- La API no tiene el nombre del festival (p. ej. *Corona Capital 2026*): el título siempre es
  `Banda at Lugar, Ciudad, País`.

### Salida de consola

```
Gorillaz Setlist
Autódromo Hermanos Rodríguez, Mexico City, Mexico
Tour: The Mountain Tour

Songs list ──────────────────────────────

Tomorrow Comes Today / Gorillaz
Feel Good Inc. / Demon Days
```

```
Gorillaz · 2026 (2 conciertos) ──────────
[11/26/2026] Gorillaz at Estadio Mario Alberto Kempes, Córdoba, Argentina
[11/20/2026] Gorillaz at Autódromo Hermanos Rodríguez, Mexico City, Mexico
```

## Buscar una canción (`-s`)

La API de setlist.fm no permite buscar por canción, así que se descargan los setlists de la banda año por año (20 por
petición, a no más de 2 peticiones por segundo) y se filtran aquí. Por eso `-y` es obligatorio con `-s`: un año
(`2026`) o un rango (`2020-2026`, máximo 30 años). La API permite 1440 peticiones al día por key.

- La coincidencia es por **texto contenido**, sin distinguir mayúsculas, acentos ni puntuación: `eastwood` encuentra
  `Clint Eastwood` y `Clint Eastwood (Reprise)`. Si coinciden varias canciones, el resumen dice cuántas veces se tocó
  cada una.
- Los setlists sin canciones registradas se cuentan aparte: no se puede saber si se tocó.
- "Primera vez" es la primera **dentro del rango** revisado.

```
Gorillaz · "eastwood" · 2024-2026 ───────────────────────
[11/20/2026] Gorillaz at Autódromo Hermanos Rodríguez, Mexico City, Mexico
             Clint Eastwood  https://www.setlist.fm/setlist/gorillaz/2026/...html
[07/01/2025] Gorillaz at The O2, London, UK
             Clint Eastwood  https://www.setlist.fm/setlist/gorillaz/2025/...html

┌──────────────── Resumen ────────────────┐
│   Conciertos       2                    │
│   Veces tocada     2                    │
│   Última vez       11/20/2026 · ...     │
│   Primera vez      07/01/2025 · ...     │
│   Revisados        4 setlists           │
│   Sin canciones    1 (no se sabe ...)   │
└─────────────────────────────────────────┘
```

### Caché de setlists

Cada año descargado se guarda en `cache/setlists/<banda>/<año>.json` (la respuesta tal cual de la API), así que buscar
otra canción de la misma banda no repite peticiones. Como setlist.fm se sigue editando después de cada concierto:

| Año | Se vuelve a pedir |
|---|---|
| Actual | Cada 6 horas |
| Anterior | Cada 7 días |
| Más viejos | Nunca (usa `--refresh` para forzarlo) |

El listado `-y` siempre pide los datos a la API y de paso actualiza esta caché.

## Álbumes (iTunes)

1. Se baja el catálogo del artista en iTunes (hasta 200 canciones, una sola petición).
2. Si la canción no está ahí, o solo aparece como remix u otra versión, se busca `artista + canción`.
3. Se descartan versiones en vivo, karaoke y tributos. Se prefiere la canción sin agregados (`(feat. ...)` y
   `Remastered` no cuentan), luego el álbum de estudio sobre la edición deluxe y sobre singles, EPs y recopilaciones,
   y al final el lanzamiento más antiguo.
4. Se limpia el nombre: `Plastic Beach (Deluxe Version)` → `Plastic Beach`, `Song - Single` → `Song`.
5. En un cover, si la banda no tiene la canción, se busca con el artista original.

iTunes permite unas 20 peticiones por minuto, así que las búsquedas por canción esperan 3 s entre sí. Todo se guarda
en `cache/albums.json`, incluso las no encontradas (`null`); borra ese archivo (o una entrada) para volver a buscar.
Si iTunes no responde, el setlist se muestra sin álbumes.

## Salida en JSON

Con `--json` stdout solo lleva el JSON; el progreso, los avisos y los errores van a stderr. Si no hay resultados o
falla la configuración, sale con código 1 y no imprime JSON.

### `-d`: playlist (formato de `yt-music-playlist`)

```json
{
  "name": "Gorillaz Autódromo Hermanos Rodríguez 2026",
  "description": "Gorillaz The Mountain Tour at Autódromo Hermanos Rodríguez, Mexico City, Mexico",
  "privacy": "PUBLIC",
  "songs": [
    { "title": "Tomorrow Comes Today", "artist": "Gorillaz", "album": "Gorillaz" },
    { "title": "Feel Good Inc.", "artist": "Gorillaz", "album": "Demon Days" }
  ]
}
```

| Campo | Descripción |
|---|---|
| `name` | `Banda Lugar Año` |
| `description` | `Banda Tour at Lugar, Ciudad, País` (sin tour: `Banda at ...`) |
| `privacy` | `PRIVACY` de la configuración |
| `songs[].album` | Se omite si no se encontró (en `yt-music-playlist` es opcional) |

### `-y`: conciertos del año (o rango)

```json
{
  "band": "Gorillaz",
  "year": "2026",
  "Tour": [
    {
      "title": "Gorillaz at Autódromo Hermanos Rodríguez, Mexico City, Mexico",
      "venue": "Autódromo Hermanos Rodríguez, Mexico City, Mexico",
      "url": "https://www.setlist.fm/setlist/gorillaz/2026/autodromo-hermanos-rodriguez-corona-stage-mexico-city-mexico-6b741226.html",
      "date": "2026-11-20",
      "tour": "The Mountain Tour",
      "songCount": 24
    }
  ]
}
```

| Campo | Descripción |
|---|---|
| `title`, `venue`, `url` | Título, lugar y página del setlist en setlist.fm |
| `date` | Fecha ISO del concierto |
| `tour` | Nombre del tour o `null` |
| `songCount` | Canciones registradas (0 si el setlist aún está vacío) |

Con un rango, `year` es `"2024-2026"`.

### `-s`: conciertos donde se tocó una canción

```json
{
  "band": "Gorillaz",
  "song": "eastwood",
  "year": "2024-2026",
  "checked": 4,
  "emptySetlists": 1,
  "concerts": 2,
  "plays": 2,
  "songs": [{ "title": "Clint Eastwood", "plays": 2 }],
  "last": { "title": "Gorillaz at Autódromo Hermanos Rodríguez, Mexico City, Mexico", "date": "2026-11-20", "...": "..." },
  "first": { "title": "Gorillaz at The O2, London, UK", "date": "2025-07-01", "...": "..." },
  "Tour": [
    {
      "title": "Gorillaz at Autódromo Hermanos Rodríguez, Mexico City, Mexico",
      "venue": "Autódromo Hermanos Rodríguez, Mexico City, Mexico",
      "url": "https://www.setlist.fm/setlist/gorillaz/2026/...html",
      "date": "2026-11-20",
      "tour": "The Mountain Tour",
      "songCount": 24,
      "songs": ["Clint Eastwood"]
    }
  ]
}
```

| Campo | Descripción |
|---|---|
| `song` | El texto buscado |
| `checked` | Setlists revisados en el rango |
| `emptySetlists` | De esos, cuántos no tienen canciones registradas |
| `concerts`, `plays` | Conciertos donde se tocó y total de veces (una canción puede tocarse dos veces en un concierto) |
| `songs` | Cada canción que contiene el texto y cuántas veces se tocó |
| `last`, `first` | Concierto más reciente y más antiguo del rango donde se tocó (`null` si ninguno) |
| `Tour` | Los conciertos, del más reciente al más antiguo; `songs` = las canciones que coincidieron en ese setlist |

Si no se encuentra la canción, `concerts` es 0 y `Tour` queda vacío (código de salida 0). Si la banda no tiene
conciertos en el rango, sale con código 1 sin JSON.

## Estructura

```
setlist-fm-scrapper/
    SETLISTFM.bat          wrapper: activa el entorno WebScrapper y corre setlistfm.py
    setlistfm.py           entrada, solo llama a setlistfm_app.cli.main
    setlistfm_app/
        cli.py             opciones, comandos (cmd_setlist, cmd_year, cmd_song) y main
        api.py             cliente de la API de setlist.fm
        cache.py           caché de setlists por banda y año
        songs.py           búsqueda de una canción en los setlists
        albums.py          álbum de cada canción con iTunes (y caché)
        report.py          salida de consola (rich)
        export.py          los mismos datos como JSON
        config.py          rutas, constantes y settings.json
    config/settings.example.json
    cache/                 albums.json y setlists/ (ignorado en git)
    output/                JSON guardados con -o (ignorado en git)
```
