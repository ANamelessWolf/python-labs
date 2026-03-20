@echo off

IF "%1"=="" (
    echo Uso: run_clean_mkv_audio.bat archivo.mkv [numero_pista]
    echo.
    echo  archivo.mkv   - Ruta al archivo MKV a procesar
    echo  numero_pista  - (Opcional) Indice de la pista de audio a conservar
    pause
    exit /b 1
)

CALL conda activate mkv-audio
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "mkv-audio"
    pause
    exit /b 1
)

IF "%2"=="" (
    python clean-mkv-audio.py %1
) ELSE (
    python clean-mkv-audio.py %1 --track %2
)

pause
