@echo off
setlocal
cd /d "%~dp0"

if /I "%CONDA_DEFAULT_ENV%"=="cautious-rotary-phone" (
    python tools\custom_matrix_gui_recorded.py
    if not errorlevel 1 exit /b 0
    echo.
    echo Active cautious-rotary-phone environment failed; trying other Python routes.
)

where conda >nul 2>nul
if not errorlevel 1 (
    rem conda is commonly a .bat/.cmd entry point on Windows, so use CALL.
    call conda run --no-capture-output -n cautious-rotary-phone python tools\custom_matrix_gui_recorded.py
    if not errorlevel 1 exit /b 0
    call conda run --no-capture-output -n base python tools\custom_matrix_gui_recorded.py
    if not errorlevel 1 exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3.14 tools\custom_matrix_gui_recorded.py
    if not errorlevel 1 exit /b 0
)

python tools\custom_matrix_gui_recorded.py
if errorlevel 1 (
    echo.
    echo Could not start Custom matrices. Current supported target is Windows with Python 3.14.
    pause
    exit /b 1
)
exit /b 0
