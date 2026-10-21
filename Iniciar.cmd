@echo off
cd /d "%~dp0"
if exist "dist\DuploPlayer\DuploPlayer.exe" (
    start "" "dist\DuploPlayer\DuploPlayer.exe" %*
) else (
    start "" ".venv\Scripts\pythonw.exe" "main.py" %*
)
