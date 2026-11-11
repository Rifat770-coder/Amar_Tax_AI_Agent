@echo off
setlocal
cd /d "%~dp0"
title Amar Tax

if exist ".venv\Scripts\python.exe" goto launch

echo Preparing Amar Tax for the first run...
where uv >nul 2>nul
if errorlevel 1 goto python_setup
set "UV_PYTHON_INSTALL_DIR=%CD%\.python"
uv --cache-dir "%CD%\.uv-cache" sync --locked --extra ui --extra crew --python 3.12
if errorlevel 1 goto failed
goto launch

:python_setup
where py >nul 2>nul
if errorlevel 1 goto standard_python
py -3.12 -m venv .venv
if not errorlevel 1 goto launch

:standard_python
python -m venv .venv
if errorlevel 1 goto failed

:launch
".venv\Scripts\python.exe" "scripts\start_project.py" %*
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Amar Tax could not start. See the error above.
echo First setup requires internet and Python 3.11-3.13 or uv.
pause
exit /b 1
