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
| `TMDB list` | Lista de series con status de TMDB, tmdbId y nombre en TMDB si difiere de la carpeta |
| `TMDB fix -sn "Serie"` | Recarga la serie usando el `tmdbId` guardado en el JSON |
| `TMDB fix -sn "Serie" --id 1198654` | Asigna ese tmdbId y recarga |
| `TMDB fix -sn "Serie" --search` | Busca en TMDB y te deja elegir de una lista |

`-sn` acepta coincidencias parciales y no distingue mayúsculas; si varias series coinciden, te pregunta cuál.

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
