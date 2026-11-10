@echo off
setlocal
cd /d "%~dp0"
if defined RESOURCE_MONITOR_PYTHON (
  "%RESOURCE_MONITOR_PYTHON%" -B launch.py %*
  exit /b
)
python -c "import sys; sys.exit(sys.version_info[:2] not in ((3,12),(3,13),(3,14),(3,15)))" >nul 2>nul
if not errorlevel 1 (
  python -B launch.py %*
  exit /b
)
for %%V in (3.15 3.14 3.13 3.12) do (
  py -%%V -c "import sys" >nul 2>nul
  if not errorlevel 1 (
    py -%%V -B launch.py %*
    exit /b
  )
)
echo Install Python 3.12 through 3.15 from https://www.python.org/downloads/ then reopen this terminal.
echo See START-HERE.md. No package was installed.
exit /b 2
