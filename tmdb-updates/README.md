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
| `MEDIA.MOVIE_PATHS` | Carpetas de películas; cada subcarpeta es un género (`TMDB movie -mv`). `TMDB movie -d` también busca ahí |
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
| `TMDB movie -d "Carpeta" -n "Película" -y 2012` | Renombra la carpeta a `Película (2012)` y guarda el poster de TMDB como `folder.jpg` / `folder.png` (`-y` es opcional) |
| `TMDB movie -mv "Carpeta" -g "Horror"` | Mueve la carpeta a `MOVIE_PATHS\Horror` (crea el género si no existe; sin `-g` te deja elegir) |
| `TMDB movie -ls` | Lista películas y colecciones por género (recursivo), valida los nombres con TMDB y baja los posters faltantes (`-g`, `-o archivo.json`, `--refresh`, `--no-posters`) |

`-sn` acepta coincidencias parciales y no distingue mayúsculas; si varias series coinciden, te pregunta cuál.

## Películas: `TMDB movie`

```
TMDB movie -d "Moonrise Kingdom (2012) (1080p BluRay x265 10bit EAC3 5.1 Silence)" -n "Moonrise Kingdom" -y 2012
```

- `-d`: la carpeta (relativa al directorio actual, absoluta, o dentro de `MOVIE_PATHS`). Se puede completar con Tab:
  la `\` final y las comillas que deja el autocompletado de cmd / PowerShell se manejan bien.
- `-n`: nombre de la película; es el que se usa para la carpeta (`:` pasa a ` -`, se quitan `<>"/\|?*`).
- `-y`: año (opcional). Ayuda a elegir la película correcta; si TMDB tiene otro año, se usa el de TMDB y avisa.
- La carpeta queda como `Nombre (YYYY)` y adentro se guarda el poster original como `folder.jpg` o `folder.png`
  según el formato que entregue TMDB (si había un `folder.*` de otro formato, se borra).
- Si la búsqueda o la descarga fallan, no se toca nada. Si la carpeta destino ya existe, termina con error.
- Con `--json` imprime `{command, path, folder, previousPath, renamed, poster, tmdbId, tmdbTitle, year, warnings}`;
  `path` es la ruta final de la carpeta.

## Películas: `TMDB movie -mv`

```
G:\Vuze> TMDB movie -mv "Moonrise Kingdom (2012)" -g "Horror"
```

- Mueve la carpeta a `<MOVIE_PATHS>\<género>`. El género no distingue mayúsculas (`-g horror` usa `Horror`).
- Si el género no existe, crea la carpeta (en el primer `MOVIE_PATHS` si hay varios).
- Sin `-g` muestra los géneros numerados: elige un número o escribe un nombre nuevo.
- En la misma unidad es un rename instantáneo; entre unidades (p. ej. `G:` → `M:`) copia con barra de progreso
  y luego borra el original. Si la copia falla se borra la copia parcial y el original queda intacto.
- Si ya existe una carpeta con ese nombre en el género, termina con error; si la película ya está ahí, no hace nada.
- `-mv` acepta Tab igual que `-d`. `-d` y `-mv` no se combinan; `-g` solo va con `-mv`.
- Con `--json` imprime `{command: "movie-move", path, folder, previousPath, genre, genrePath, createdGenre, moved}`;
  `path` es la ruta final de la carpeta.

## Películas: `TMDB movie -ls`

```
TMDB movie -ls                         todas, en árbol por género
TMDB movie -ls -g horror               solo un género (acepta parte del nombre si no hay uno exacto)
TMDB movie -ls -o M:\movies.json       además exporta todo a un archivo JSON
TMDB movie -ls --refresh               vuelve a validar todo con TMDB
TMDB movie -ls --no-posters            no baja posters
```

**Recursivo.** Dentro de cada género, una carpeta con videos es una *película*; una carpeta sin videos pero con
subcarpetas de películas es una *colección* (`Star Wars\`, `DC Universe\Batman\…`), hasta 3 niveles. Se ignoran
`Subs`, `Extras`, `Featurettes`, `Sample` y similares.

**Validación con TMDB (cache en `data/movies.json`).** Cada carpeta se busca en TMDB una sola vez; las siguientes
corridas usan el cache y solo consultan las carpetas nuevas o renombradas (el cache es por nombre de carpeta, así que
mover una película de género no la vuelve a buscar). Cada entrada guarda `genre`, `collection` y `path`, que se
actualizan en cada corrida. Si borras o renombras una carpeta, su entrada se quita del cache en la siguiente
corrida (con `-g`, solo las de ese género; nunca se tocan entradas de un disco de `MOVIE_PATHS` que no esté
conectado). Las quitadas se listan al final y en el JSON (`removedFromCache`). Estados:

| Estado | Significado |
|---|---|
| `OK` | La carpeta ya es `Título (Año)` y coincide con TMDB (título o título original) |
| `RENAME` (`→ Nombre (Año)`) | Match seguro, pero el nombre no tiene el formato; muestra el nombre sugerido para `TMDB movie -d` |
| `REVIEW` (`¿Nombre (Año)?`) | Match dudoso: el título no es exacto, el año no cuadra, o hay varias películas con ese título (`Poltergeist` sin año) |
| `NOT_FOUND` | Sin resultados en TMDB |

Un match es *seguro* cuando el título coincide exacto y el año de la carpeta cuadra (±1), o cuando no hay año y solo
existe una película con ese título (o una es mucho más conocida que las demás). Las colecciones se validan por
contenido: la colección de TMDB debe incluir al menos la mitad de tus películas de esa carpeta (así `Animation\Spiderman`
es la de Spider-Verse y no la de Raimi, y `Pixar` no se vuelve la colección de Monsters, Inc.).

**Posters.** A las películas y colecciones con match seguro que no tienen `folder.jpg/.jpeg/.png` se les baja el
poster de TMDB (`+poster`). Nunca reemplaza uno existente. Los `REVIEW` no reciben poster.

**Corregir un match.** En `data/movies.json`, en la entrada de la carpeta (llave = nombre en minúsculas) pon
`"tmdbId": N`, `"manual": true` y borra `"title"`; en la siguiente corrida se recarga con ese id y `--refresh` ya no
la toca. Funciona igual para `collections`.

**JSON** (`--json` a stdout, `-o archivo.json` a un archivo; se pueden usar juntos):
`{command: "movie-list", generated, cache, totalMovies, totalCollections, totalGenres, status: {OK, RENAME, REVIEW,
NOT_FOUND}, removedFromCache, withoutPoster, postersCreated, genres: [{name, path, count, items}]}`. Cada item es
`{type: "movie", name, path, status, year, suggestedName, tmdbId, tmdbTitle, tmdbOriginalTitle, tmdbYear, poster,
posterCreated, error}` o `{type: "collection", name, path, status, tmdbId, tmdbName, count, poster, posterCreated,
error, items}`.

## Salida en JSON

Todos los subcomandos aceptan `--json` (después del subcomando): `TMDB status --json`, `TMDB updates --json`,
`TMDB scan -sn "Rivals" --json`… En vez de las tablas, imprime en stdout un JSON con los mismos datos; el progreso,
los avisos y los errores van a stderr, y si algo falla termina con código 1. Lo usan los nodos TMDB de Node Board.

Todos traen `command`; los de series también `lastScan` (ISO) y `totalSeries`. Además:

| Comando | Campos |
|---|---|
| `status` | `tags` (conteo por tag) y `libraries`: `[{name, path, series: [serie]}]` |
| `status -sn` | `series`: la serie con sus temporadas y episodios |
| `updates` | `today`, `from`, `to`, `missing`, `upcoming` e `items`: `[{date, daysFromToday, series, library, code, title, state}]` (`state`: `MISSING` o `AVAILABLE`) |
| `missing` | `totalEpisodes`, `seriesWithMissing`, `wholeSeasons` y `series`: cada una con las temporadas que faltan (`wholeSeason`, `missingCount`, `missingEpisodes`) |
| `list` | `series`: `[{name, library, libraryPath, status, tag, tmdbId, tmdbName, nameDiffers}]` |
| `scan` | `scanned`, `skipped`, `tags`, `removed`, `unavailable`, `problems` y, con `-sn`, `series` |
| `fix` / `unfollow` | `message` y `series` (cómo quedó) |
| `movie -ls` | `command: "movie-list"`, `totalMovies`, `totalCollections`, `status`, `genres` con películas y colecciones (ver arriba) |
| `movie -mv` | `command: "movie-move"`, `path` (ruta final), `folder`, `previousPath`, `genre`, `genrePath`, `createdGenre`, `moved` |
| `movie -d` | `path` (ruta final de la carpeta), `folder`, `previousPath`, `renamed`, `poster`, `tmdbId`, `tmdbTitle`, `year`, `warnings` |

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
| `tmdb_app/movie.py` | Comando `movie`: `-d` renombra y guarda el poster, `-mv` mueve a un género |
| `tmdb_app/movielib.py` | `movie -ls`: recorre la biblioteca, cache `data/movies.json`, validación con TMDB y posters |

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
