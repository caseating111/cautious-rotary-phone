@echo off
setlocal
cd /d "%~dp0"

rem =========================================================================
rem Miniforge / Conda workflow controller launcher
rem Supports both normal and private/isolated testing modes (per IMAGE_BLIND_TESTING.md).
rem =========================================================================

set "PRIVATE_ROOT=C:\LocalWorkflowData"
set "PRIVATE_TEMP=%PRIVATE_ROOT%\PrivateTemp"
set "PRIVATE_WIN_TEMP=%PRIVATE_TEMP%\Windows"
set "PRIVATE_JAVA_TEMP=%PRIVATE_TEMP%\Java"
set "TELEMETRY_DIR=%~dp0.local-test-telemetry"

if not exist "%PRIVATE_ROOT%" mkdir "%PRIVATE_ROOT%" 2>nul
if not exist "%PRIVATE_WIN_TEMP%" mkdir "%PRIVATE_WIN_TEMP%" 2>nul
if not exist "%PRIVATE_JAVA_TEMP%" mkdir "%PRIVATE_JAVA_TEMP%" 2>nul
if not exist "%TELEMETRY_DIR%" mkdir "%TELEMETRY_DIR%" 2>nul

set "TEMP=%PRIVATE_WIN_TEMP%"
set "TMP=%PRIVATE_WIN_TEMP%"
set "CAUTIOUS_PRIVATE_DATA_ROOT=%PRIVATE_ROOT%"
set "CAUTIOUS_PRIVATE_TEMP_ROOT=%PRIVATE_TEMP%"
set "CAUTIOUS_TELEMETRY_DIR=%TELEMETRY_DIR%"

rem Configure Java temp directory and ensure localhost binding for RMI
set "JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=%PRIVATE_JAVA_TEMP% -Djava.rmi.server.hostname=127.0.0.1"

rem 1. Check if workflow-c or cautious-rotary-phone is already active
if /I "%CONDA_DEFAULT_ENV%"=="workflow-c" goto :RUN_ACTIVE
if /I "%CONDA_DEFAULT_ENV%"=="cautious-rotary-phone" goto :RUN_ACTIVE

rem 2. Check for direct Miniforge user environment Python
if exist "%USERPROFILE%\.conda\envs\workflow-c\python.exe" (
    "%USERPROFILE%\.conda\envs\workflow-c\python.exe" tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

rem 3. Check for ProgramData Miniforge environment Python
if exist "C:\ProgramData\miniforge3\envs\workflow-c\python.exe" (
    "C:\ProgramData\miniforge3\envs\workflow-c\python.exe" tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

rem 4. Use mamba / conda command if available
where mamba >nul 2>nul
if not errorlevel 1 (
    call mamba run --no-capture-output -n workflow-c python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

where conda >nul 2>nul
if not errorlevel 1 (
    call conda run --no-capture-output -n workflow-c python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

if exist "C:\ProgramData\miniforge3\condabin\mamba.bat" (
    call "C:\ProgramData\miniforge3\condabin\mamba.bat" run --no-capture-output -n workflow-c python tools\workflow_controller_extended.py
    if not errorlevel 1 exit /b 0
)

:RUN_ACTIVE
python tools\workflow_controller_extended.py
if errorlevel 1 (
    echo.
    echo Could not start workflow controller via Miniforge workflow-c environment.
    echo Please verify that the 'workflow-c' environment is created with:
    echo   mamba create -n workflow-c python=3.11 pillow pandas openpyxl
    pause
    exit /b 1
)
exit /b 0
