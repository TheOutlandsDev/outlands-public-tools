@echo off
setlocal
"%~dp0runtime\python.exe" -I -B -X utf8 "%~dp0launch.py" --demo %*
set "outlands_result=%errorlevel%"
if "%outlands_result%"=="0" exit /b 0
echo.
echo Developer Workspace could not complete. Preserve your workspace and read START-HERE.txt.
if "%~1"=="" pause
exit /b %outlands_result%
