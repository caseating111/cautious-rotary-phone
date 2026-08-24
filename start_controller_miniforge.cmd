@echo off
setlocal
cd /d "%~dp0"

rem Miniforge workflow-c launcher with the image-blind private temp boundary.
rem Runtime selection and controller exit handling remain centralized in
rem start_controller.cmd.
set "PRIVATE_ROOT=C:\LocalWorkflowData"
set "PRIVATE_TEMP=%PRIVATE_ROOT%\PrivateTemp"
set "PRIVATE_WIN_TEMP=%PRIVATE_TEMP%\Windows"
set "PRIVATE_JAVA_TEMP=%PRIVATE_TEMP%\Java"
set "TELEMETRY_DIR=%~dp0.local-test-telemetry"

if not exist "%PRIVATE_ROOT%" mkdir "%PRIVATE_ROOT%"
if not exist "%PRIVATE_WIN_TEMP%" mkdir "%PRIVATE_WIN_TEMP%"
if not exist "%PRIVATE_JAVA_TEMP%" mkdir "%PRIVATE_JAVA_TEMP%"
if not exist "%TELEMETRY_DIR%" mkdir "%TELEMETRY_DIR%"
if not exist "%PRIVATE_WIN_TEMP%" goto :private_dir_failed
if not exist "%PRIVATE_JAVA_TEMP%" goto :private_dir_failed
if not exist "%TELEMETRY_DIR%" goto :private_dir_failed

set "TEMP=%PRIVATE_WIN_TEMP%"
set "TMP=%PRIVATE_WIN_TEMP%"
set "CAUTIOUS_PRIVATE_DATA_ROOT=%PRIVATE_ROOT%"
set "CAUTIOUS_PRIVATE_TEMP_ROOT=%PRIVATE_TEMP%"
set "CAUTIOUS_TELEMETRY_DIR=%TELEMETRY_DIR%"
set "JAVA_TOOL_OPTIONS=%JAVA_TOOL_OPTIONS% -Djava.io.tmpdir=%PRIVATE_JAVA_TEMP%"

rem Give the unified launcher the proven workflow-c interpreter first.
if /I "%CONDA_DEFAULT_ENV%"=="workflow-c" if exist "%CONDA_PREFIX%\python.exe" (
    set "WORKFLOW_C_PYTHON=%CONDA_PREFIX%\python.exe"
    goto :run
)
if exist "%USERPROFILE%\.conda\envs\workflow-c\python.exe" (
    set "WORKFLOW_C_PYTHON=%USERPROFILE%\.conda\envs\workflow-c\python.exe"
    goto :run
)
if exist "%USERPROFILE%\miniforge3\envs\workflow-c\python.exe" (
    set "WORKFLOW_C_PYTHON=%USERPROFILE%\miniforge3\envs\workflow-c\python.exe"
    goto :run
)
if exist "C:\ProgramData\miniforge3\envs\workflow-c\python.exe" set "WORKFLOW_C_PYTHON=C:\ProgramData\miniforge3\envs\workflow-c\python.exe"

:run
call "%~dp0start_controller.cmd"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" endlocal & exit /b 0
echo.
echo Could not start tools\workflow_controller_extended.py in workflow-c.
echo Configure it with setup_environment.cmd, or run:
echo   mamba create -n workflow-c python=3.11 pillow pandas openpyxl
endlocal & exit /b %RC%

:private_dir_failed
echo.
echo START BLOCKED: required private temp/telemetry directories could not be created.
endlocal & exit /b 3