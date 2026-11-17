# TMDB Updates

Revisa tu biblioteca local de series contra [The Movie Database](https://www.themoviedb.org/) y te dice qué temporadas
están completas, qué episodios te faltan y qué está por salir.

## Instalación

```powershell
conda env create -f environment.yml      # crea el entorno "tmdb"
copy config\settings.example.json config\settings.json
```

Llena `config/settings.json`:

| Clave | Descripción |
|---|---|
| `MEDIA.TV_PATHS` | Carpetas de bibliotecas de series (cada subcarpeta es una serie) |
| `MEDIA.MOVIE_PATHS` | Reservado para películas (aún no se usa) |
| `TMDB.API_KEY` | API key v3 o token v4 (Read Access Token) de TMDB |
| `TMDB.LANGUAGE` | Idioma de títulos de episodio (default `en-US`) |

`TMDB.bat` usa rutas absolutas, así que puedes copiarlo a `Z:\bin`.

## Comandos

| Comando | Qué hace |
|---|---|
| `TMDB` | Menú interactivo |
| `TMDB scan` | Escanea todo y guarda `data/library.json`. Omite series `[Ended]`/`[Canceled]` que ya están `OK` |
| `TMDB scan --full` | Igual, pero incluye también las terminadas |
| `TMDB scan -sn "South Park"` | Escanea una sola serie |
| `TMDB status -tv` | Resumen de todas las series |
| `TMDB status -sn "South Park"` | Árbol de temporadas y episodios faltantes / próximos |
| `TMDB updates` | Episodios faltantes o por salir entre hoy −2 meses y hoy +1 semana |
| `TMDB missing` | Solo lo ya emitido que te falta, en árbol por serie (temporadas `MISSING` en una línea) |
| `TMDB missing -sn "Harley Quinn"` | Igual, para una sola serie |
| `TMDB list` | Lista de series con status de TMDB, tmdbId y nombre en TMDB si difiere de la carpeta |
| `TMDB fix -sn "Serie"` | Recarga la serie usando el `tmdbId` guardado en el JSON |
| `TMDB fix -sn "Serie" --id 1198654` | Asigna ese tmdbId y recarga |
| `TMDB fix -sn "Serie" --search` | Busca en TMDB y te deja elegir de una lista |
| `TMDB unfollow -sn "Simpsons" -s 14` | Revisa la serie solo hasta la temporada 14; las posteriores se ignoran en scans y reportes. Si queda `OK` se trata como terminada (el scan normal la omite) |
| `TMDB unfollow -sn "Simpsons" --all` | Quita el límite y vuelve a revisar todas las temporadas |

`-sn` acepta coincidencias parciales y no distingue mayúsculas; si varias series coinciden, te pregunta cuál.

## Salida en JSON

Todos los subcomandos aceptan `--json` (después del subcomando): `TMDB status --json`, `TMDB updates --json`,
`TMDB scan -sn "Rivals" --json`… En vez de las tablas, imprime en stdout un JSON con los mismos datos; el progreso,
los avisos y los errores van a stderr, y si algo falla termina con código 1. Lo usan los nodos TMDB de Node Board.

Todos traen `command`, `lastScan` (ISO) y `totalSeries`. Además:

| Comando | Campos |
|---|---|
| `status` | `tags` (conteo por tag) y `libraries`: `[{name, path, series: [serie]}]` |
| `status -sn` | `series`: la serie con sus temporadas y episodios |
| `updates` | `today`, `from`, `to`, `missing`, `upcoming` e `items`: `[{date, daysFromToday, series, library, code, title, state}]` (`state`: `MISSING` o `AVAILABLE`) |
| `missing` | `totalEpisodes`, `seriesWithMissing`, `wholeSeasons` y `series`: cada una con las temporadas que faltan (`wholeSeason`, `missingCount`, `missingEpisodes`) |
| `list` | `series`: `[{name, library, libraryPath, status, tag, tmdbId, tmdbName, nameDiffers}]` |
| `scan` | `scanned`, `skipped`, `tags`, `removed`, `unavailable`, `problems` y, con `-sn`, `series` |
| `fix` / `unfollow` | `message` y `series` (cómo quedó) |

Una *serie* tiene `name`, `path`, `library`, `libraryPath`, `status` (de TMDB), `tag`, `finished`, `tmdbId`, `tmdbName`,
`firstAirDate`, `maxSeason`, `lastScan`, `error`, `sizeBytes`, `size` (`"4.7 GB"`), `looseFiles` y `seasons`
(`number`, `folder`, `tag`, `localEpisodes`, `tmdbEpisodes`, `airDate`, `sizeBytes`, `size`, `namingErrors` y, en el
detalle, `episodes`: `[{code, number, name, airDate, daysFromToday, state}]`).

## Código

`TMDB.bat` llama a `tmdb.py`, que solo arranca `tmdb_app.cli.main`.

| Archivo | Qué tiene |
|---|---|
| `tmdb.py` | Punto de entrada (lo llama `TMDB.bat`) |
| `tmdb_app/cli.py` | Subcomandos (`cmd_scan`, `cmd_status`, `cmd_updates`…), menú interactivo y `main` |
| `tmdb_app/config.py` | Rutas y lectura de `config/settings.json` |
| `tmdb_app/tmdb_client.py` | Cliente de la API de TMDB |
| `tmdb_app/scanner.py` | Escaneo de carpetas locales y comparación con TMDB (tags) |
| `tmdb_app/store.py` | Lectura y escritura de `data/library.json` |
| `tmdb_app/report.py` | Reportes de consola con rich |
| `tmdb_app/export.py` | Salida en JSON (`--json`): los mismos datos que los reportes |

## Estructura esperada

```
M:\TV\South Park\
    Season 1\        (o "Season 01")
        South Park - S01E01 - Cartman Gets an Anal Probe.mkv
    Specials\        (se ignora, igual que "Season 00")
```

Cada video debe tener `SxxEyy` en el nombre (también `S01E01E02` y `S01E01-E03`).
Si una carpeta "Season XX" tiene un archivo con otro formato, o con una temporada distinta, esa temporada es `NAMING_ERROR`.
Si hay videos sueltos en la raíz de la serie, la serie es `NAMING_ERROR`.

## Tags

| Tag | Significado |
|---|---|
| `COMPLETE` | Tienes todos los episodios que lista TMDB |
| `INCOMPLETE` | Faltan episodios, ya emitidos o por salir |
| `MISSING` | La temporada ya salió y no tienes la carpeta |
| `UPCOMING` | La temporada todavía no se estrena |
| `NAMING_ERROR` | Hay archivos con un formato que no se reconoce; se arreglan a mano |
| `EXTRA` | Temporada o episodio local que no existe en TMDB |
| `OK` (serie) | Todas las temporadas están completas (o por estrenarse) |
| `NOT_FOUND` / `ERROR` (serie) | No se encontró en TMDB, o la API falló |

Episodios: `OK`, `MISSING (Released on …)`, `AVAILABLE ON …`, `TBA`.

## Corregir un match incorrecto

Al buscar se usa el nombre de la carpeta; un año al final, como `Breaking Bad (2008)`, ayuda a desambiguar.
Si la serie que eligió no es la correcta, cambia su `tmdbId` en `data/library.json` (o usa `--id` / `--search`) y corre `TMDB fix -sn "Serie"`.
Los scans posteriores siempre usan el `tmdbId` guardado.

Para el anime, TMDB a veces agrupa las temporadas de forma distinta a como están en disco, y esas series pueden salir `INCOMPLETE` aunque las tengas completas.
