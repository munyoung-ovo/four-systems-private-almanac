@echo off
REM 一键安装（Windows）：建独立 venv -> 装三个依赖 -> 跑金标准自校验。
REM 用法：双击本文件，或在终端运行  install.bat
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo [X] 未找到 Python，请先安装 Python 3.8-3.13: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo 使用解释器: %PY%
%PY% setup_env.py
pause
