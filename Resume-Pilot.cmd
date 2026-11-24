@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0tools\phase13_windows.ps1" -Mode Review
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Failed with exit code %RC%. See message above.
pause
exit /b %RC%
