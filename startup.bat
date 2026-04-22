@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0startup.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Startup failed with exit code %EXIT_CODE%.
)

exit /b %EXIT_CODE%
