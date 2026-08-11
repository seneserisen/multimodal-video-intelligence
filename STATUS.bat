@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\control.ps1" -Action STATUS %*
exit /b %ERRORLEVEL%
