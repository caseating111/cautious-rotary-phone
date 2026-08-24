@echo off
setlocal
cd /d "%~dp0"

rem Prefer the same Miniforge workflow-c Python 3.11 as the controller.
if defined WORKFLOW_C_PYTHON (
    set "WORKFLOW_PY=%WORKFLOW_C_PYTHON%"
    call :direct_available
    if not errorlevel 1 goto :run_direct
)
if defined CONDA_PREFIX (
    set "WORKFLOW_PY=%CONDA_PREFIX%\python.exe"
    call :direct_available
    if not errorlevel 1 goto :run_direct
    set "WORKFLOW_PY=%CONDA_PREFIX%\envs\workflow-c\python.exe"
    call :direct_available
    if not errorlevel 1 goto :run_direct
)
set "WORKFLOW_PY=%USERPROFILE%\miniforge3\envs\workflow-c\python.exe"
call :direct_available
if not errorlevel 1 goto :run_direct
set "WORKFLOW_PY=%USERPROFILE%\.conda\envs\workflow-c\python.exe"
call :direct_available
if not errorlevel 1 goto :run_direct
set "WORKFLOW_PY=C:\ProgramData\miniforge3\envs\workflow-c\python.exe"
call :direct_available
if not errorlevel 1 goto :run_direct
if defined CONDA_EXE if exist "%CONDA_EXE%" (
    call "%CONDA_EXE%" run --no-capture-output -n workflow-c python -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
    if not errorlevel 1 goto :run_conda_exe
)
where conda >nul 2>nul
if not errorlevel 1 (
    call conda run --no-capture-output -n workflow-c python -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
    if not errorlevel 1 goto :run_conda
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
    if not errorlevel 1 goto :run_py311
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
    if not errorlevel 1 goto :run_path
)

echo.
echo No compatible Python 3.11 with Pillow and Tkinter was found for Custom matrices.
pause
exit /b 1

:direct_available
if not exist "%WORKFLOW_PY%" exit /b 1
"%WORKFLOW_PY%" -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
exit /b %ERRORLEVEL%

:run_direct
"%WORKFLOW_PY%" tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_conda
call conda run --no-capture-output -n workflow-c python tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_conda_exe
call "%CONDA_EXE%" run --no-capture-output -n workflow-c python tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_py311
py -3.11 tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
:run_path
python tools\custom_matrix_gui_recorded.py
exit /b %ERRORLEVEL%
