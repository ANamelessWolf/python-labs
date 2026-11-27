@echo off
REM Wrapper de tmdb.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   TMDB                      -> menu interactivo
REM   TMDB scan [--full]        -> escanea la biblioteca (--full incluye terminadas)
REM   TMDB scan -sn "Serie"     -> escanea una sola serie
REM   TMDB status -tv           -> resumen de todas las series
REM   TMDB status -sn "Serie"   -> detalle de una serie
REM   TMDB updates              -> faltantes / proximos (hoy -2 meses .. +1 semana)
REM   TMDB list                 -> lista de series
REM   TMDB fix -sn "Serie"      -> recarga con el tmdbId del JSON (--id N / --search)
REM   Cualquier subcomando + --json -> salida en JSON (TMDB updates --json)
REM   TMDB unfollow -sn "Serie" -s 14 -> revisa solo hasta la temporada 14 (--all quita el limite)
REM   TMDB movie -d "Carpeta" -n "Pelicula" -y 2012 -> renombra a "Pelicula (2012)" y baja folder.jpg/png
REM   TMDB movie -mv "Carpeta" -g "Horror" -> mueve a MOVIE_PATHS\Horror (sin -g pregunta)
REM   TMDB movie -ls [-g "Horror"] [-o archivo.json] -> lista por genero, valida con TMDB, baja posters faltantes

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\tmdb-updates"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate tmdb
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "tmdb"
    exit /b 1
)

SET "PYTHONIOENCODING=utf-8"
python "%APP_DIR%\tmdb.py" %*
endlocal & exit /b %ERRORLEVEL%
