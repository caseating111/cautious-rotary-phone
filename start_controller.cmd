@echo off
setlocal
set "CAUTIOUS_CONTROLLER_LAUNCHER=1"
cd /d "%~dp0"

rem Production runtime: Miniforge workflow-c (Python 3.11).  Candidate
rem fallbacks are used only when this runtime is unavailable, never after a
rem controller error or Ctrl+C.
set "WORKFLOW_PY=%USERPROFILE%\.conda\envs\workflow-c\python.exe"
if exist "%WORKFLOW_PY%" goto :run_direct
set "WORKFLOW_PY=C:\ProgramData\miniforge3\envs\workflow-c\python.exe"
if exist "%WORKFLOW_PY%" goto :run_direct

where conda >nul 2>nul
if not errorlevel 1 (
    call conda run --no-capture-output -n workflow-c python -c "import PIL, tkinter" >nul 2>nul
    if not errorlevel 1 goto :run_conda
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import PIL, tkinter" >nul 2>nul
    if not errorlevel 1 goto :run_py311
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import PIL, tkinter" >nul 2>nul
    if not errorlevel 1 goto :run_path
)

echo.
echo No compatible Python with Pillow and Tkinter was found.
echo Expected Miniforge workflow-c Python 3.11 at:
echo %USERPROFILE%\.conda\envs\workflow-c\python.exe
pause
exit /b 1

:run_direct
"%WORKFLOW_PY%" tools\workflow_controller_extended.py
goto :finish
:run_conda
call conda run --no-capture-output -n workflow-c python tools\workflow_controller_extended.py
goto :finish
:run_py311
py -3.11 tools\workflow_controller_extended.py
goto :finish
:run_path
python tools\workflow_controller_extended.py

:finish
set "CONTROLLER_EXIT=%ERRORLEVEL%"
call :exit_if_controller_requested
if not errorlevel 1 exit /b 0
if not "%CONTROLLER_EXIT%"=="0" (
    echo.
    echo Controller stopped with exit code %CONTROLLER_EXIT%. No alternate Python was started.
    pause
)
exit /b %CONTROLLER_EXIT%

:exit_if_controller_requested
if exist "%USERPROFILE%\.cautious-rotary-phone\controller_close.request" (
    del /q "%USERPROFILE%\.cautious-rotary-phone\controller_close.request"
    exit /b 0
)
exit /b 1