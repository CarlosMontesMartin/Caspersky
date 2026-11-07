@echo off
rem Windows. Toda la logica esta en run.py.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3 run.py) else (python run.py)
