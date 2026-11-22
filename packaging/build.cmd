@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" pause
if "%~1"=="" pause
endlocal & exit /b %EXITCODE%
