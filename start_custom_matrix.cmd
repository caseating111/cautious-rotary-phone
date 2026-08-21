@echo off
setlocal
cd /d "%~dp0"

if /I "%CONDA_DEFAULT_ENV%"=="cautious-rotary-phone" (
    python tools\custom_matrix_gui_recorded.py
    exit /b %errorlevel%
)

where conda >nul 2>nul
if not errorlevel 1 (
    conda run --no-capture-output -n cautious-rotary-phone python tools\custom_matrix_gui_recorded.py
    if not errorlevel 1 exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 tools\custom_matrix_gui_recorded.py
    exit /b %errorlevel%
)

python tools\custom_matrix_gui_recorded.py
if errorlevel 1 pause
