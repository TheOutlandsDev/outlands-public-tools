@echo off
setlocal
"%~dp0runtime\python.exe" -I -B -X utf8 "%~dp0launch.py" --demo %*
set "result=%errorlevel%"
if not "%result%"=="0" if "%~1"=="" pause
exit /b %result%
