@echo off
REM Wrapper de setlistfm.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   SETLISTFM -b "Gorillaz" -d "11/20/2026"           -> setlist del concierto (Cancion / Album)
REM   SETLISTFM -b "Gorillaz" -d "11/20/2026" --json    -> playlist JSON para yt-music-playlist (mensajes a stderr)
REM   SETLISTFM -b "Gorillaz" -d "11/20/2026" -o        -> ademas guarda el JSON en OUTPUT_DIR (o -o "ruta")
REM   SETLISTFM -b "Gorillaz" -d "11/20/2026" --no-album -> sin buscar albumes (mas rapido)
REM   SETLISTFM -b "Gorillaz" -y 2026                   -> conciertos de la banda en ese anio
REM   SETLISTFM -b "Gorillaz" -y 2024-2026              -> conciertos en un rango de anios
REM   SETLISTFM -b "Gorillaz" -y 2026 --json            -> la lista de conciertos como JSON
REM   SETLISTFM -b "Gorillaz" -s "eastwood" -y 2020-2026 -> conciertos donde se toco una cancion que contiene el texto
REM   SETLISTFM -b "Gorillaz" -s "eastwood" -y 2026 --refresh -> igual, sin usar la cache de setlists
REM   SETLISTFM -b "Gorillaz" -y 2026 -c "ruta\otra.json" -> usa otro archivo de configuracion
REM   SETLISTFM -h                                      -> ayuda con todos los comandos

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\setlist-fm-scrapper"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate WebScrapper
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "WebScrapper" 1>&2
    exit /b 1
)

SET "PYTHONIOENCODING=utf-8"
python "%APP_DIR%\setlistfm.py" %*
endlocal & exit /b %ERRORLEVEL%
