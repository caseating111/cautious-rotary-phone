@echo off
setlocal
cd /d "%~dp0"

rem Deliberately skip conda/Anaconda. Use ordinary Windows Python only.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
    echo.
    echo Windows py launcher failed; trying python.exe on PATH.
)

where python >nul 2>nul
if not errorlevel 1 (
    python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

echo.
echo Could not start the controller without Anaconda.
echo Install or expose a normal Python 3 on PATH, or use start_controller.cmd for conda/Anaconda fallbacks.
pause
exit /b 1
