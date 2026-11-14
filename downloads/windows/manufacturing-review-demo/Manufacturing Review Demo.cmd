@echo off
setlocal
"%~dp0runtime\python.exe" -I -B "%~dp0launch.py" %*
set "demo_exit=%ERRORLEVEL%"
if "%~1"=="" (
  if not "%demo_exit%"=="0" echo Review did not complete. Keep the private run folder and read START-HERE.txt.
  pause
)
exit /b %demo_exit%
