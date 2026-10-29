@echo off
setlocal
"%~dp0runtime\python.exe" -I -B -X utf8 "%~dp0launch.py" --demo %*
set "outlands_result=%errorlevel%"
if not "%outlands_result%"=="0" echo Dataset Review could not complete. Preserve your private workspace and reports; read START-HERE.txt.
if "%~1"=="" pause
exit /b %outlands_result%
