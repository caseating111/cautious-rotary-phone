@echo off
setlocal
cd /d "%~dp0"

rem Prefer the repository's named conda environment when it is already active.
if /I "%CONDA_DEFAULT_ENV%"=="cautious-rotary-phone" (
    python tools\workflow_controller_extended.py
    if errorlevel 1 exit /b 1
    exit /b 0
)

rem Otherwise use the named conda environment if conda is available.
rem conda is commonly a .bat/.cmd entry point on Windows, so CALL is required
rem or this launcher may never regain control to reach the Python fallbacks.
where conda >nul 2>nul
if not errorlevel 1 (
    call conda run --no-capture-output -n cautious-rotary-phone python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
    echo.
    echo Named conda environment was unavailable or failed; trying Anaconda base.
    call conda run --no-capture-output -n base python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
    echo.
    echo Anaconda base could not run the controller; trying the Windows Python launcher.
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

rem Last fallback for systems where python.exe itself is on PATH.
python tools\workflow_controller_extended.py
if errorlevel 1 (
    echo.
    echo Could not start the controller. Create the conda environment from environment.yml or make Python 3 available on PATH.
    pause
    exit /b 1
)
exit /b 0
