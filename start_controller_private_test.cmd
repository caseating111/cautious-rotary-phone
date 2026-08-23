@echo off
setlocal

rem Image-blind/private desktop-test launcher.
rem Pixel-bearing temp/output data stays outside the Git worktree.
rem The production Miniforge workflow-c runtime inherits these private paths.

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

rem Keep any pre-existing Java options and add a process-local java.io.tmpdir.
set "JAVA_TOOL_OPTIONS=%JAVA_TOOL_OPTIONS% -Djava.io.tmpdir=%PRIVATE_JAVA_TEMP%"

rem Privacy-sensitive tests must not reuse an older Fiji instance that was
rem launched without these inherited TEMP/TMP/java.io.tmpdir settings.
tasklist /FI "IMAGENAME eq ImageJ-win64.exe" 2>NUL | find /I "ImageJ-win64.exe" >NUL
if not errorlevel 1 goto :fiji_running
tasklist /FI "IMAGENAME eq fiji-windows-x64.exe" 2>NUL | find /I "fiji-windows-x64.exe" >NUL
if not errorlevel 1 goto :fiji_running

rem Use the unified Miniforge-first launcher.
call "%~dp0start_controller.cmd"
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%

:fiji_running
echo.
echo PRIVACY TEST BLOCKED: Fiji/ImageJ is already running.
echo Close Fiji completely, then run this launcher again so Fiji inherits
echo the private TEMP/TMP/java.io.tmpdir locations.
echo.
exit /b 2

:private_dir_failed
echo.
echo PRIVACY TEST BLOCKED: required private temp/telemetry directories could not be created.
echo.
exit /b 3
