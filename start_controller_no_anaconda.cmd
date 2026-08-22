@echo off
setlocal
cd /d "%~dp0"

rem Deliberately skip conda/Anaconda. Use ordinary Windows Python 3.14 only.
where py >nul 2>nul
if not errorlevel 1 (
    py -3.14 tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
    echo.
    echo Windows Python 3.14 launcher failed; trying python.exe on PATH.
)

where python >nul 2>nul
if not errorlevel 1 (
    python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

echo.
echo Could not start the controller without Anaconda.
echo Current supported target is Windows with Python 3.14. Use start_controller.cmd for conda/Anaconda fallbacks.
pause
exit /b 1
