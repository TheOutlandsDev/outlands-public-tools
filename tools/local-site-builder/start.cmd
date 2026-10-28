@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Install Node.js 24 LTS with npm from https://nodejs.org/ then reopen this terminal.
  echo See START-HERE.md. No package was installed.
  exit /b 2
)
if "%~1"=="--check" (
  node scripts\doctor.js --check
) else (
  node scripts\doctor.js --start
)
exit /b %errorlevel%
