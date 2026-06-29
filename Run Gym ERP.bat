@echo off
REM Double-click to launch the built Gym ERP desktop app.
REM If the app hasn't been built yet, run:  python scripts\build.py
set "EXE=%~dp0build\nuitka\launcher.dist\GymERP.exe"
if not exist "%EXE%" (
  echo Gym ERP is not built yet. Run:  python scripts\build.py
  pause
  exit /b 1
)
start "" "%EXE%"
