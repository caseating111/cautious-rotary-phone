@echo off
setlocal
cd /d "%~dp0"

set "CONDA_CMD="
if defined CONDA_EXE if exist "%CONDA_EXE%" set "CONDA_CMD=%CONDA_EXE%"
if defined CONDA_CMD goto :configure
for /f "delims=" %%I in ('where conda 2^>nul') do if not defined CONDA_CMD set "CONDA_CMD=%%I"
if defined CONDA_CMD goto :configure

if exist "%USERPROFILE%\miniforge3\condabin\conda.bat" set "CONDA_CMD=%USERPROFILE%\miniforge3\condabin\conda.bat"
if defined CONDA_CMD goto :configure
if exist "%USERPROFILE%\miniforge3\Scripts\conda.exe" set "CONDA_CMD=%USERPROFILE%\miniforge3\Scripts\conda.exe"
if defined CONDA_CMD goto :configure
if exist "C:\ProgramData\miniforge3\condabin\conda.bat" set "CONDA_CMD=C:\ProgramData\miniforge3\condabin\conda.bat"
if defined CONDA_CMD goto :configure
if exist "C:\ProgramData\miniforge3\Scripts\conda.exe" set "CONDA_CMD=C:\ProgramData\miniforge3\Scripts\conda.exe"
if defined CONDA_CMD goto :configure

echo.
echo Miniforge/conda was not found. Install Miniforge, then run this file again.
pause
exit /b 1

:configure
call "%CONDA_CMD%" run -n workflow-c python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >nul 2>nul
if errorlevel 1 goto :create

call "%CONDA_CMD%" env update -n workflow-c -f "%~dp0runtime-environment.yml"
if errorlevel 1 goto :failed
goto :verify

:create
call "%CONDA_CMD%" env create -f "%~dp0runtime-environment.yml"
if errorlevel 1 goto :failed

:verify
call "%CONDA_CMD%" run -n workflow-c python -c "import PIL, tkinter, sys; raise SystemExit(sys.version_info[:2] != (3, 11))"
if errorlevel 1 goto :failed
echo.
echo workflow-c is ready. Start the program with start_controller.cmd.
pause
exit /b 0

:failed
echo.
echo The workflow-c environment could not be configured.
pause
exit /b 1
