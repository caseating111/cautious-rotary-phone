@echo off
setlocal enabledelayedexpansion

REM ============================================================================
REM Gemini Prototype Launcher
REM Automatically selects Python 3.11 / Miniforge conda environment for running
REM isolated Gemini prototype modules, test suites, and applets.
REM ============================================================================

set "PY_EXE="

REM 1. Check if already inside an active Conda environment
if defined CONDA_PREFIX (
    if exist "%CONDA_PREFIX%\python.exe" (
        set "PY_EXE=%CONDA_PREFIX%\python.exe"
        goto :FOUND_PYTHON
    )
)

REM 2. Check workflow-c conda environment (Python 3.11 for ImageJ / analysis)
if exist "%USERPROFILE%\.conda\envs\workflow-c\python.exe" (
    set "PY_EXE=%USERPROFILE%\.conda\envs\workflow-c\python.exe"
    goto :FOUND_PYTHON
)

REM 3. Check Miniforge base environment
if exist "C:\ProgramData\miniforge3\python.exe" (
    set "PY_EXE=C:\ProgramData\miniforge3\python.exe"
    goto :FOUND_PYTHON
)
if exist "%USERPROFILE%\miniforge3\python.exe" (
    set "PY_EXE=%USERPROFILE%\miniforge3\python.exe"
    goto :FOUND_PYTHON
)

REM 4. Fallback to py launcher for Python 3.11 or standard python
where py.exe >nul 2>nul
if %errorlevel% equ 0 (
    py -3.11 -c "import sys; print(sys.version)" >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_EXE=py -3.11"
        goto :FOUND_PYTHON
    )
)

where python.exe >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :FOUND_PYTHON
)

echo [ERROR] No compatible Python executable found in Miniforge / Conda / PATH.
exit /b 1

:FOUND_PYTHON
if "%~1"=="" (
    echo Gemini Prototype Launcher
    echo Usage: run_gemini_prototype.cmd ^<path_to_script_or_test^> [args...]
    echo Selected Python: !PY_EXE!
    !PY_EXE! --version
    exit /b 0
)

!PY_EXE! %*
exit /b %errorlevel%
