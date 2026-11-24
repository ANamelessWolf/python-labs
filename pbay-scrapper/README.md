# PirateBay Scrapper

Busca cada episodio de una serie en un mirror de The Pirate Bay (p. ej. `https://thepiratebay.bond`) y guarda el
magnet link en `output/<serie en camelCase>.txt`, uno por línea. Si hay varios resultados te pregunta cuál agregar.

## Instalación

Usa el mismo entorno conda que `nyaa-scrapper`:

```powershell
conda env create -f ..\nyaa-scrapper\environment.yml     # solo si aún no existe "WebScrapper"
copy config\settings.example.json config\settings.json
```

`PBAY.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Configuración

```json
{
  "SITE": "https://thepiratebay.bond",
  "SERIE": "Helluva Boss",
  "QUERY": "Helluva Boss SXXEXX",
  "SEASON": [
    { "INDEX": 3, "START": 1, "END": 8 }
  ]
}
```

| Clave | Descripción |
|---|---|
| `SITE` | URL del mirror; si se cae, cámbialo por otro |
| `SERIE` | Nombre de la serie; define el archivo de salida (`helluvaBoss.txt`) |
| `QUERY` | Texto de búsqueda; `SXXEXX` se reemplaza por `S03E01`, `S03E02`, ... |
| `SEASON` | Lista de temporadas: `INDEX` = número de temporada, `START`/`END` = rango de episodios |

La búsqueda queda como `https://thepiratebay.bond/search/Helluva%20Boss%20S03E01/1/99/0`.

## Comandos

| Comando | Qué hace |
|---|---|
| `PBAY` | Usa `config\settings.json`; si hay varios resultados muestra una tabla y pregunta cuál agregar |
| `PBAY -c ruta\otra.json` | Usa otro archivo de configuración |
| `PBAY -a` (o `--auto`) | No pregunta: toma siempre el primer resultado |
| `PBAY -w` (o `--wizard`) | Wizard: pregunta sitio, serie, query, temporada inicial y final (vacía = solo una) y el rango de episodios de cada temporada; guarda `settings.json` y busca. Acepta `-a` |
| `PBAY -q "Helluva Boss S03E01"` | Una sola búsqueda; el magnet elegido se agrega a `output\general.txt`. Acepta `-a` |
| `PBAY -h` | Ayuda con todos los modos, opciones y ejemplos |
| `PBAY --delay 2` | Espera 2 s entre búsquedas (default 1) |
| `PBAY -q "Helluva Boss S03E01" -l` (o `--list`) | Solo busca: muestra la tabla con **todos** los resultados (✔ = ya está en el `.txt`) sin preguntar ni escribir nada. Funciona con cualquier modo menos `-w` |
| `PBAY -s https://otro.sitio` (o `--site`) | Usa otro sitio en lugar del `SITE` de la configuración |
| `PBAY -q "Helluva Boss S03E01" --json` | Imprime el resultado como JSON en vez del reporte (ver [Salida en JSON](#salida-en-json)). Funciona con cualquier modo menos `-w` |

La tabla muestra nombre, tamaño, seeds (▲) y leechers (▼) de cada torrent. Al elegir: escribe el número de la fila, `Enter` toma la 1 y `0` omite el episodio.

## Estados en consola

| Estado | Significado |
|---|---|
| `[Copied]` | Se guardó el magnet elegido (o el único resultado) |
| `[Saved]` | Uno de los resultados ya estaba en el archivo de una ejecución anterior; no pregunta otra vez |
| `[Skipped]` | Elegiste `0` |
| `[Not Found]` | La búsqueda no tuvo resultados |
| `[Error]` | Falló la petición HTTP |
| `[Found]` | Solo con `--list`: hubo resultados y no se guardó ninguno |

El archivo nunca se borra: los magnets nuevos se anexan al final, y cada elección se guarda en cuanto la haces
(si cancelas con `Ctrl+C` no se pierde lo ya elegido). Para empezar de cero, borra el `.txt`.

## Código

`PBAY.bat` llama a `pbay.py`, que solo arranca `pbay_app.cli.main` (la misma estructura que `tmdb-updates` y
`nyaa-scrapper`).

| Archivo | Qué tiene |
|---|---|
| `pbay.py` | Punto de entrada (lo llama `PBAY.bat`) |
| `pbay_app/cli.py` | Opciones, comandos (`cmd_series`, `cmd_query`), wizard y `main` |
| `pbay_app/config.py` | Rutas, constantes y lectura de `settings.json` |
| `pbay_app/scraper.py` | Peticiones al sitio y lectura de resultados |
| `pbay_app/search.py` | Archivo de salida: elige, guarda el magnet y registra cada búsqueda |
| `pbay_app/report.py` | Reporte de consola (tabla para elegir, líneas y resumen) |
| `pbay_app/export.py` | Salida en JSON (`--json`): los mismos datos que el reporte |

## Salida en JSON

Con `--json`, en vez del reporte imprime en stdout un único objeto JSON; el panel, el progreso y los avisos van a
stderr. Funciona con el modo de `settings.json` (`PBAY --json`, `PBAY -c otra.json --json`) y con
`PBAY -q "texto" --json`.

- **Implica `--auto`**: nadie puede elegir, así que toma el primer resultado (y lo guarda en el `.txt` como siempre).
- **Con `--list`** (`PBAY -q "texto" --list --json`) no elige ni guarda nada: cada item trae `results` con todos los
  resultados y su `state` es `FOUND` (o `NOT_FOUND` / `ERROR`). Lo usan los nodos Torrents de Node Board.
- `-w --json` falla: el wizard es interactivo.
- Un error de configuración termina con código 1, el mensaje va a stderr y no se imprime JSON.
- Si falla la petición de algún episodio, el JSON se imprime igual (con código 0) y ese episodio queda con
  `state: "ERROR"` y el mensaje en `error`. Así no se pierden los que sí se guardaron.

| Campo | Descripción |
|---|---|
| `command` | `"series"` (búsqueda con `settings.json`) o `"query"` (`-q`) |
| `site`, `serie`, `query` | Sitio, serie (`null` con `-q`) y query (con `SXXEXX` en modo serie) |
| `auto` | Siempre `true` con `--json` |
| `list` | `true` con `--list` |
| `file` | Ruta del `.txt` donde se anexan los magnets (con `--list` solo se lee) |
| `total` | Número de búsquedas |
| `stats` | Conteo por estado: `{"COPIED": 3, "SAVED": 5, "SKIPPED": 0, "NOT_FOUND": 1, "ERROR": 0, "FOUND": 0}` (siempre las 6 claves) |
| `items` | Una entrada por búsqueda |

Cada entrada de `items`:

| Campo | Descripción |
|---|---|
| `season`, `episode`, `code` | Temporada, episodio y `"S01E05"`; `null` con `-q` |
| `query` | Texto buscado |
| `state` | `COPIED`, `SAVED`, `SKIPPED`, `NOT_FOUND`, `ERROR` o `FOUND` (los [estados en consola](#estados-en-consola)) |
| `resultCount` | Resultados encontrados |
| `error` | Mensaje si falló la petición; si no, `null` |
| `result` | El torrent guardado (`COPIED`) o el que ya estaba en el archivo (`SAVED`); si no, `null` |
| `results` | Con `--list`: todos los resultados en el orden del sitio, cada uno con `saved` (si el magnet ya está en el `.txt`); sin `--list`, `null` |

`result` trae `title`, `magnet`, `size` (el texto del sitio, `"1.4 GiB"`), `sizeBytes` (número o `null`),
`seeders`, `leechers` (números o `null`) y `url` (página del torrent).

Ejemplo (`PBAY -q "Helluva Boss S03E01" --json`):

```json
{
  "command": "query",
  "site": "https://thepiratebay.bond",
  "serie": null,
  "query": "Helluva Boss S03E01",
  "auto": true,
  "file": "Z:\\dev\\py\\python-labs\\pbay-scrapper\\output\\general.txt",
  "total": 1,
  "stats": {"COPIED": 1, "SAVED": 0, "SKIPPED": 0, "NOT_FOUND": 0, "ERROR": 0},
  "items": [
    {
      "season": null, "episode": null, "code": null,
      "query": "Helluva Boss S03E01",
      "state": "COPIED", "resultCount": 4, "error": null,
      "result": {
        "title": "Helluva Boss S03E01 1080p WEB h264",
        "magnet": "magnet:?xt=urn:btih:...",
        "size": "1.4 GiB", "sizeBytes": 1503238554,
        "seeders": 1234, "leechers": 56,
        "url": "https://thepiratebay.bond/torrent/123456/..."
      }
    }
  ]
}
```
