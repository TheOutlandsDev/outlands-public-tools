@echo off
setlocal
"%~dp0runtime\python.exe" -I -B -X utf8 "%~dp0launch.py" --exercise %*
set "outlands_result=%errorlevel%"
if not "%outlands_result%"=="0" echo Import workflow could not complete. Preserve your private instance and read START-HERE.txt.
if "%~1"=="" pause
exit /b %outlands_result%
