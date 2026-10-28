@echo off
setlocal
cd /d "%~dp0"
py -3.13 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3.13 -B launch.py %*
  exit /b
)
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3.12 -B launch.py %*
  exit /b
)
where python >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 or 3.13 from https://www.python.org/downloads/ then reopen this terminal.
  echo See START-HERE.md. No package was installed.
  exit /b 2
)
python -B launch.py %*
exit /b %errorlevel%
