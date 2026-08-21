@echo off
setlocal
cd /d "%~dp0"

rem Prefer the repository's named conda environment when it is already active.
if /I "%CONDA_DEFAULT_ENV%"=="cautious-rotary-phone" (
    python tools\workflow_controller.py
    exit /b %ERRORLEVEL%
)

rem Otherwise use the named conda environment if conda is available.
where conda >nul 2>nul
if %ERRORLEVEL%==0 (
    conda run --no-capture-output -n cautious-rotary-phone python tools\workflow_controller.py
    if %ERRORLEVEL%==0 exit /b 0
    echo.
    echo Named conda environment was unavailable or failed; trying the Windows Python launcher.
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 tools\workflow_controller.py
    if %ERRORLEVEL%==0 exit /b 0
)

rem Last fallback for systems where python.exe itself is on PATH.
python tools\workflow_controller.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Could not start the controller. Create the conda environment from environment.yml or make Python 3 available on PATH.
    pause
)
