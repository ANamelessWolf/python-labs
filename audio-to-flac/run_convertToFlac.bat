@echo off

REM === Activate conda ===
call "%USERPROFILE%\anaconda3\Scripts\activate.bat"

REM === Activate environment ===
call conda activate convertToFlac

REM === Move to script directory ===
cd /d Z:\dev\py\python-labs\audio-to-flac

REM === Run script ===
python convertToFlac.py audios flac

pause