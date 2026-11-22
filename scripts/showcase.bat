@echo off
rem MuJoCo showcase entry (Windows).
rem
rem Usage:
rem   scripts\showcase.bat                 interactive menu
rem   scripts\showcase.bat 1               flat straight run
rem   scripts\showcase.bat 3 --mode step   20 mm step, single-step with Space
rem   scripts\showcase.bat 4 --speed 1     30 mm step, real time (overrides default 0.25)
rem
rem This file must stay pure ASCII: Windows cmd parses .bat with the local code page,
rem so UTF-8 Chinese comments can be split into commands and crash the script.
rem Chinese instructions live in the showcase guide under docs\ (Chinese file name).
rem
rem The script only prepares .venv, shows the menu and calls scripts\view.py.
rem It does not modify models or cases, and it does not capture screenshots or video.

setlocal EnableExtensions

rem Keep Chinese HUD output readable in the console.
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul || goto :fail

if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage

rem ---------------------------------------------------------------- 1. env

echo [showcase] checking .venv and MuJoCo
if not exist ".venv\Scripts\python.exe" goto :install
".venv\Scripts\python.exe" -c "import mujoco" >nul 2>&1
if errorlevel 1 goto :install
echo [showcase] environment ready (reusing .venv)
goto :menu

:install
if exist ".venv\Scripts\python.exe" goto :pip_install
echo [showcase] first run: creating .venv (1-2 minutes, network required)
set "PYCMD=python"
where py >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3.13"
%PYCMD% -m venv .venv
if errorlevel 1 goto :fail

:pip_install
if not exist "requirements.lock.txt" (
  echo [showcase] requirements.lock.txt not found; cannot install dependencies
  goto :fail
)
echo [showcase] installing requirements.lock.txt
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
if errorlevel 1 goto :pip_fail
echo [showcase] environment ready

rem ---------------------------------------------------------------- 2. menu

:menu
set "CHOICE="
set "EXTRA="
if not "%~1"=="" (
  echo %~1| findstr /r "^[1-5qQ]$" >nul
  if not errorlevel 1 (
    set "CHOICE=%~1"
    shift
  )
)
:collect_extra
if not "%~1"=="" (
  set "EXTRA=%EXTRA% %1"
  shift
  goto :collect_extra
)

if not "%CHOICE%"=="" goto :dispatch

echo.
echo MuJoCo showcase - choose a case (no need to remember case names)
echo.
echo   1) Flat straight (flat)
echo   2) Step 12.5 mm (below shell limit)
echo   3) Step 20 mm (front lip dominant)
echo   4) Step 30 mm (beyond current model limit)
echo   5) Baseline self-check (baseline)
echo   q) Quit
echo.
echo   Chinese guide: see the showcase guide under docs\
echo.
set /p "CHOICE=Select [1-5/q]: "

:dispatch
if "%CHOICE%"=="1" set "VIEWARGS=--case cases/flat.json --config proto_v1 --speed 0.25"
if "%CHOICE%"=="2" set "VIEWARGS=--case cases/oomwoo_g25_step12p5.json --config oomwoo_g25 --speed 0.25"
if "%CHOICE%"=="3" set "VIEWARGS=--case cases/oomwoo_g25_step20.json --config oomwoo_g25 --speed 0.25"
if "%CHOICE%"=="4" set "VIEWARGS=--case cases/oomwoo_g25_step30.json --config oomwoo_g25 --speed 0.25"
if "%CHOICE%"=="5" set "VIEWARGS=--case cases/baseline.json --config proto_v1 --speed 0.25"
if /i "%CHOICE%"=="q" goto :quit
if not defined VIEWARGS (
  echo [showcase] invalid choice: %CHOICE% (expected 1-5 or q)
  goto :fail
)

echo [showcase] equivalent command: scripts\view.py %VIEWARGS%%EXTRA%
echo [showcase] in the window: drag=rotate / wheel=zoom / Space=pause or step / Esc=exit
echo.
".venv\Scripts\python.exe" "%SCRIPT_DIR%view.py" %VIEWARGS%%EXTRA%
set "RC=%errorlevel%"
popd >nul
exit /b %RC%

:quit
echo [showcase] quit
popd >nul
exit /b 0

:usage
echo MuJoCo showcase
echo.
echo   scripts\showcase.bat                 open the menu and choose a case
echo   scripts\showcase.bat ^<1-5^> [args]   choose directly; extra args go to view.py
echo.
echo Cases:
echo   1) Flat straight (flat)
echo   2) Step 12.5 mm (below shell limit)
echo   3) Step 20 mm (front lip dominant)
echo   4) Step 30 mm (beyond current model limit)
echo   5) Baseline self-check (baseline)
echo   q) Quit
echo.
echo Pass-through args (default --speed 0.25; a later value wins):
echo   --mode step          start paused, press Space to advance one frame
echo   --speed 1            real-time playback
echo   --step-size-s 0.05   advance 0.05 s per Space press in step mode
echo   -h, --help           show this help
echo.
echo Chinese guide: see the showcase guide under docs\
echo In the window: left-drag=rotate / wheel=zoom / right-drag=pan / Space=pause or step / Esc=exit.
popd >nul
exit /b 0

:pip_fail
echo.
echo [showcase] dependency install failed: check network and Python architecture.
echo [showcase] fallback: py -3.13 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.lock.txt
goto :fail

:fail
echo [showcase] environment preparation failed; check network or Python install and retry
popd >nul
exit /b 1
