# Nyaa Scrapper

Busca cada episodio de una serie en [nyaa.si](https://nyaa.si) y guarda el magnet link en
`output/<serie en camelCase>.txt`, uno por línea. Si hay varios resultados te pregunta cuál agregar.

## Instalación

```powershell
conda env create -f environment.yml      # crea el entorno "WebScrapper" (compartido con otros scrapers)
copy config\settings.example.json config\settings.json
```

`NYAA.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Configuración

```json
{
  "SITE": "https://nyaa.si",
  "SERIE": "Thousand-Year Blood War",
  "QUERY": "[ToonsHub] Thousand-Year Blood War SXXEXX [Multi-Subs]",
  "SEASON": [
    { "INDEX": 1, "START": 1, "END": 49 }
  ]
}
```

| Clave | Descripción |
|---|---|
| `SITE` | URL base del sitio |
| `SERIE` | Nombre de la serie; define el archivo de salida (`thousand-YearBloodWar.txt`) |
| `QUERY` | Texto de búsqueda; `SXXEXX` se reemplaza por `S01E01`, `S01E02`, ... |
| `SEASON` | Lista de temporadas: `INDEX` = número de temporada, `START`/`END` = rango de episodios |

## Comandos

| Comando | Qué hace |
|---|---|
| `NYAA` | Usa `config\settings.json`; si hay varios resultados muestra una tabla y pregunta cuál agregar |
| `NYAA -c ruta\otra.json` | Usa otro archivo de configuración |
| `NYAA -a` (o `--auto`) | No pregunta: toma siempre el primer resultado |
| `NYAA -w` (o `--wizard`) | Wizard: pregunta sitio, serie, query, temporada inicial y final (vacía = solo una) y el rango de episodios de cada temporada; guarda `settings.json` y busca. Acepta `-a` |
| `NYAA -q "[ToonsHub] Thousand-Year Blood War S01E01"` | Una sola búsqueda; el magnet elegido se agrega a `output\general.txt`. Acepta `-a` |
| `NYAA -h` | Ayuda con todos los modos, opciones y ejemplos |
| `NYAA --delay 2` | Espera 2 s entre búsquedas (default 1) |
| `NYAA -q "[ToonsHub] Thousand-Year Blood War S01E01" --json` | Imprime el resultado como JSON en vez del reporte (ver [Salida en JSON](#salida-en-json)). Funciona con cualquier modo menos `-w` |
| `NYAA -q "Hunter x Hunter" -ln es` | Filtra por idioma: abre la página de detalle de cada resultado y deja solo los que mencionan el idioma en la descripción (`Audio: Spanish`, `Sub Tracks: Español`, ...) o en el título. Funciona con cualquier modo |

### Filtro de idioma (`-ln` / `--lang`)

| Código | Palabras que busca (sin distinguir mayúsculas, palabra completa) |
|---|---|
| `es` | spanish, español, espanol, castellano, latino, latin american, spa, esp |
| `en` | english, inglés, ingles, eng |
| `ja` | japanese, japonés, japones, 日本語, jpn |
| `pt` | portuguese, português, portugues |
| `fr` | french, français, francais, fre, fra |

Varios códigos separados por coma aceptan cualquiera (`-ln es,en`). Un valor que no está en la tabla se busca
tal cual (`-ln german`). Como abre una página por resultado (4 en paralelo), la búsqueda tarda más; solo revisa la
primera página de resultados (75).

La tabla muestra nombre, tamaño, seeds (▲) y leechers (▼) de cada torrent. Al elegir: escribe el número de la fila,
`Enter` toma la 1 y `0` omite el episodio.

## Estados en consola

| Estado | Significado |
|---|---|
| `[Copied]` | Se guardó el magnet elegido (o el único resultado) |
| `[Saved]` | Uno de los resultados ya está en el archivo (de esta u otra ejecución, p. ej. un batch); no pregunta otra vez |
| `[Skipped]` | Elegiste `0` |
| `[Not Found]` | La búsqueda no tuvo resultados |
| `[Error]` | Falló la petición HTTP |

El archivo nunca se borra: si vuelves a correr con la misma `SERIE` (por ejemplo con otro `QUERY`), los magnets
nuevos se anexan al final, y cada elección se guarda en cuanto la haces (si cancelas con `Ctrl+C` no se pierde lo
ya elegido). Para empezar de cero, borra el `.txt`.

## Estructura

| Archivo | Qué tiene |
|---|---|
| `nyaa.py` | Punto de entrada (lo llama `NYAA.bat`) |
| `nyaa_app/cli.py` | Opciones, comandos (`cmd_series`, `cmd_query`), wizard y `main` |
| `nyaa_app/config.py` | Rutas, constantes y lectura de `settings.json` |
| `nyaa_app/scraper.py` | Peticiones al sitio y lectura de resultados, filtro de idioma |
| `nyaa_app/search.py` | Archivo de salida: elige, guarda el magnet y registra cada búsqueda |
| `nyaa_app/report.py` | Reporte de consola (tabla para elegir, líneas y resumen) |
| `nyaa_app/export.py` | Salida en JSON (`--json`): los mismos datos que el reporte |

## Salida en JSON

Con `--json`, en vez del reporte imprime en stdout un único objeto JSON; el panel, el progreso y los avisos van a
stderr. Funciona con el modo de `settings.json` (`NYAA --json`, `NYAA -c otra.json --json`) y con
`NYAA -q "texto" --json`.

- **Implica `--auto`**: nadie puede elegir, así que toma el primer resultado (y lo guarda en el `.txt` como siempre).
- `-w --json` falla: el wizard es interactivo.
- Un error de configuración termina con código 1, el mensaje va a stderr y no se imprime JSON.
- Si falla la petición de algún episodio, el JSON se imprime igual (con código 0) y ese episodio queda con
  `state: "ERROR"` y el mensaje en `error`. Así no se pierden los que sí se guardaron.

| Campo | Descripción |
|---|---|
| `command` | `"series"` (búsqueda con `settings.json`) o `"query"` (`-q`) |
| `site`, `serie`, `query` | Sitio, serie (`null` con `-q`) y query (con `SXXEXX` en modo serie) |
| `languages` | Códigos de `-ln` (`[]` sin filtro) |
| `auto` | Siempre `true` con `--json` |
| `file` | Ruta del `.txt` donde se anexan los magnets |
| `total` | Número de búsquedas |
| `stats` | Conteo por estado: `{"COPIED": 3, "SAVED": 5, "SKIPPED": 0, "NOT_FOUND": 1, "ERROR": 0}` (siempre las 5 claves) |
| `items` | Una entrada por búsqueda |

Cada entrada de `items`:

| Campo | Descripción |
|---|---|
| `season`, `episode`, `code` | Temporada, episodio y `"S01E05"`; `null` con `-q` |
| `query` | Texto buscado |
| `state` | `COPIED`, `SAVED`, `SKIPPED`, `NOT_FOUND` o `ERROR` (los [estados en consola](#estados-en-consola)) |
| `resultCount` | Resultados encontrados (después del filtro de idioma) |
| `error` | Mensaje si falló la petición; si no, `null` |
| `result` | El torrent guardado (`COPIED`) o el que ya estaba en el archivo (`SAVED`); si no, `null` |

`result` trae `title`, `magnet`, `size` (`"1.4 GiB"`, tal cual el sitio), `sizeBytes` (número o `null`),
`seeders`, `leechers` (números o `null`) y `url` (página del torrent).
