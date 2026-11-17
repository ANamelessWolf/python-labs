@echo off
REM Wrapper de nyaa.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   NYAA                        -> usa config\settings.json (pregunta cual agregar si hay varios)
REM   NYAA -c "ruta\otra.json"    -> usa otro archivo de configuracion
REM   NYAA -a  (o --auto)         -> no pregunta: toma siempre el primer resultado
REM   NYAA -w  (o --wizard)       -> configura settings.json paso a paso y busca
REM   NYAA -q "texto"             -> una sola busqueda, se agrega a output\general.txt
REM   NYAA -h                     -> ayuda con todos los comandos
REM   NYAA --delay 2              -> segundos entre busquedas (default 1)
REM   NYAA -q "texto" -ln es      -> solo resultados cuya descripcion mencione el idioma (es, en, ja, pt, fr)
REM   NYAA -q "texto" --json      -> imprime el resultado como JSON (mensajes a stderr; implica -a)
REM   NYAA -q "texto" -l           -> solo busca: lista todos los resultados sin guardar nada
REM   NYAA -s "https://..."        -> usa otro sitio

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\nyaa-scrapper"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate WebScrapper
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "WebScrapper" 1>&2
    exit /b 1
)

SET "PYTHONIOENCODING=utf-8"
python "%APP_DIR%\nyaa.py" %*
endlocal & exit /b %ERRORLEVEL%
