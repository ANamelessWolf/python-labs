@echo off
REM Wrapper de yt_music_playlist.py. Puedes copiarlo a Z:\bin: usa rutas absolutas.
REM   ytmusic-sync                -> menu interactivo
REM   ytmusic-sync --list         -> lista playlists de Inputs
REM   ytmusic-sync --sync NOMBRE  -> sincroniza una playlist
REM   ytmusic-sync --sync-all     -> sincroniza todas
REM   ytmusic-sync --setup-auth   -> configura la autenticacion

setlocal
SET "APP_DIR=Z:\dev\py\python-labs\yt-music-playlist"

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate ytMusic
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "ytMusic"
    exit /b 1
)

python "%APP_DIR%\yt_music_playlist.py" %*
endlocal
