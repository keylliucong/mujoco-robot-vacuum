@echo off
rem 用法: scripts\view.bat --case step_20mm --config oomwoo --speed 0.25
rem
rem Windows 一键入口：没有 .venv 就先建环境（约 1-2 分钟），然后打开 MuJoCo viewer。
rem Windows 直接用 python 调 launch_passive，不需要 mjpython；macOS 用 scripts/view.sh。
chcp 65001 >nul
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.." >nul || goto :fail

if exist ".venv\Scripts\python.exe" goto :run

echo [view.bat] 首次运行：在 .venv 创建项目环境并安装依赖（约 1-2 分钟）
set "PYCMD=python"
where py >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"

%PYCMD% -m venv .venv
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
if errorlevel 1 goto :fail

if exist "requirements.lock.txt" (
  echo [view.bat] 安装 requirements.lock.txt
  ".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
) else (
  echo [view.bat] 安装 requirements.txt
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
if errorlevel 1 goto :fail

:run
".venv\Scripts\python.exe" "%SCRIPT_DIR%view.py" %*
set "RC=%errorlevel%"
popd >nul
exit /b %RC%

:fail
echo [view.bat] 环境准备失败，请检查网络或 Python 安装后重试
popd >nul
exit /b 1
