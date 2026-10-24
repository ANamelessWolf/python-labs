@echo off
REM Wrapper de pbay.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   PBAY                        -> usa config\settings.json (pregunta cual agregar si hay varios)
REM   PBAY -c "ruta\otra.json"    -> usa otro archivo de configuracion
REM   PBAY -a  (o --auto)         -> no pregunta: toma siempre el primer resultado
REM   PBAY -w  (o --wizard)       -> configura settings.json paso a paso y busca
REM   PBAY -q "texto"             -> una sola busqueda, se agrega a output\general.txt
REM   PBAY -h                     -> ayuda con todos los comandos
REM   PBAY --delay 2              -> segundos entre busquedas (default 1)

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\pbay-scrapper"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate WebScrapper
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "WebScrapper"
    exit /b 1
)

SET "PYTHONIOENCODING=utf-8"
python "%APP_DIR%\pbay.py" %*
endlocal & exit /b %ERRORLEVEL%
