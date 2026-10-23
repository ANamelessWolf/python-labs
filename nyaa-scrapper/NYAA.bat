@echo off
REM Wrapper de nyaa.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   NYAA                        -> usa config\settings.json
REM   NYAA -c "ruta\otra.json"    -> usa otro archivo de configuracion
REM   NYAA --delay 2              -> segundos entre busquedas (default 1)

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\nyaa-scrapper"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate WebScrapper
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "WebScrapper"
    exit /b 1
)

SET "PYTHONIOENCODING=utf-8"
python "%APP_DIR%\nyaa.py" %*
endlocal & exit /b %ERRORLEVEL%
