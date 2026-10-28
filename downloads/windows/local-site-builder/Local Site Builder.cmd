@echo off
setlocal
set NODE_OPTIONS=
set NODE_PATH=
"%~dp0runtime\node.exe" "%~dp0launch.js" %*
set "result=%errorlevel%"
if not "%result%"=="0" if "%~1"=="" pause
exit /b %result%
