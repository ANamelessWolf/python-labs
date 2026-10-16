@echo off

IF "%1"=="" (
    echo Uso: run_clean_mkv_audio.bat archivo.mkv [opciones]
    echo.
    echo  archivo.mkv   - Ruta al archivo MKV a procesar
    echo.
    echo  Opciones:
    echo    --remove     - Eliminar una pista de audio ^(conservar el resto^)
    echo    --track N    - Indice de la pista ^(modo no interactivo^)
    echo    --replace    - Reemplazar el archivo original con el resultado
    echo.
    echo  Ejemplos:
    echo    run_clean_mkv_audio.bat video.mkv
    echo    run_clean_mkv_audio.bat video.mkv --remove
    echo    run_clean_mkv_audio.bat video.mkv --remove --track 2
    echo    run_clean_mkv_audio.bat video.mkv --remove --track 2 --replace
    echo    run_clean_mkv_audio.bat video.mkv --track 0 --replace
    pause
    exit /b 1
)

CALL conda activate mkv-audio
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "mkv-audio"
    pause
    exit /b 1
)

python clean-mkv-audio.py %*

pause
