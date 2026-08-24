@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\control.ps1" -Action OPEN_APP %*
exit /b %ERRORLEVEL%
