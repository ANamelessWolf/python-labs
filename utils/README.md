# utils

Scripts sueltos para ordenar archivos de series y películas. No tienen dependencias (solo la biblioteca estándar de
Python 3.10+).

Excepto `FixNaming.py`, se configuran **editando las constantes al inicio del archivo** (`DIRECTORIO`, `DRY_RUN`…).
Todos traen `DRY_RUN = True`: solo muestran qué harían. Revisa la salida y cambia a `False` para renombrar o mover
de verdad (en `FixNaming.py`, con `--apply`).

| Script | Qué hace | Configuración |
|---|---|---|
| `FixNaming.py` | `S01E01 Hot Tub.en.avi` → `S01E01 - EN - Hot Tub.avi` | Argumentos: carpeta y `--apply` |
| `FormatSeasonRename.py` | `05 Nombre.mkv` → `S01E05 Nombre.mkv` (número al inicio → código de episodio) | `DIRECTORIO`, `SEASON`, `DRY_RUN` |
| `InitName.py` | Renombra los videos en orden alfabético a `S01E01 Serie.mkv`, `S01E02 Serie.mkv`… | `DIRECTORIO`, `SERIE`, `TEMPORADA`, `OFFSET_EPISODE`, `DRY_RUN` |
| `MoveToMovieFolder.py` | Mueve cada película a su carpeta `Título (Año)` a partir del nombre del archivo | `DIRECTORIO`, `REGEX`, `DRY_RUN` |

En todos, si el destino ya existe el archivo se omite, y solo se procesan los archivos de la carpeta indicada
(no las subcarpetas).

## FixNaming.py

Para versiones con idioma en el nombre (`S01E01 Something.es.mkv`). Por defecto solo simula; con `--apply` renombra.

```powershell
python FixNaming.py "D:\Anime\Season 01"            # simulación
python FixNaming.py "D:\Anime\Season 01" --apply    # renombra
```

Cada archivo sale con `RENAME`, `OK` (ya está bien) o `SKIP` (no coincide con el patrón o el destino ya existe).

## FormatSeasonRename.py

Para archivos que empiezan con el número del episodio (`1 Piloto.mkv`, `012 Final.mkv`). Usa `SEASON` para el código.

## InitName.py

Numera los videos de la carpeta en orden alfabético, así que los nombres originales deben ordenarse bien.
`OFFSET_EPISODE` se suma al número: con `OFFSET_EPISODE = 13`, el primer archivo queda como `E14` (útil para
temporadas partidas en dos carpetas).

## MoveToMovieFolder.py

`REGEX` debe tener los grupos `year` y `title`. El archivo trae dos formatos:

| Formato | Ejemplo |
|---|---|
| `Año - Título` (comentado) | `1940 - Fantasia.mkv` → `Fantasia (1940)\` |
| `Año.Título.calidad…` (activo) | `1995.Toy.Story.1080p.BluRay.mkv` → `Toy Story (1995)\` |

Los puntos del título se cambian por espacios y se quitan los caracteres no válidos en Windows.
