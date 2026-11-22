@echo off
setlocal EnableExtensions
chcp 65001 >nul
rem Usage: scripts\view.bat --case step_20mm --config oomwoo --speed 0.25
rem
rem Windows entry point: create .venv on first run (about 1-2 minutes), then open the MuJoCo viewer.
rem Windows calls launch_passive with python directly (no mjpython); on macOS use scripts/view.sh.
rem Keep this file pure ASCII. cmd.exe parses .bat files with the OEM/ANSI code page, so
rem UTF-8 Chinese comments get split into bogus commands and the run fails before view.py starts.
rem Chinese guidance lives in the docs folder (the Viewer guide is under docs).

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul || goto :fail

if exist ".venv\Scripts\python.exe" goto :run

echo [view.bat] First run: creating .venv and installing dependencies (about 1-2 minutes)
set "PYCMD=python"
where py >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"

%PYCMD% -m venv .venv
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
if errorlevel 1 goto :fail

if exist "requirements.lock.txt" (
  echo [view.bat] Installing requirements.lock.txt
  ".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
) else (
  echo [view.bat] Installing requirements.txt
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
if errorlevel 1 goto :fail

:run
".venv\Scripts\python.exe" "%SCRIPT_DIR%view.py" %*
set "RC=%errorlevel%"
popd >nul
exit /b %RC%

:fail
echo [view.bat] Environment setup failed. Check network or Python installation, then retry.
popd >nul
exit /b 1
