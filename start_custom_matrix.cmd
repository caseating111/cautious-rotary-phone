@echo off
setlocal
cd /d "%~dp0"

rem Prefer the same Miniforge workflow-c Python 3.11 as the controller.
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
echo No compatible Python with Pillow and Tkinter was found for Custom matrices.
pause
exit /b 1

:run_direct
"%WORKFLOW_PY%" tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_conda
call conda run --no-capture-output -n workflow-c python tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_py311
py -3.11 tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_path
python tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%