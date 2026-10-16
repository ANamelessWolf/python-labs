@echo off

CALL "C:\Users\migue\anaconda3\Scripts\activate.bat" "C:\Users\migue\anaconda3"
CALL conda activate mkv-audio
IF ERRORLEVEL 1 (
    echo Error: no se pudo activar el entorno conda "mkv-audio"
    pause
    exit /b 1
)

for /L %%i in (11,1,47) do (
    python "Z:\dev\py\python-labs\mkv-cleaner\clean-mkv-audio.py" "M:\S01E%%i NANA.mkv" --remove --track 0 --replace
)

pause
