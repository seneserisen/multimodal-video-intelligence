@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\clean.ps1" %*
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" if not defined CI pause
exit /b %CODE%
