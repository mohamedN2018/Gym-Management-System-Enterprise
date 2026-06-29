@echo off
REM Run Gym ERP from source using the project virtual environment.
REM Double-click this file (or run it) to launch the app and see the login screen.
cd /d "%~dp0\.."
".venv\Scripts\python.exe" launcher.py %*
