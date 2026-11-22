#!/usr/bin/env bash
# 用法: ./scripts/view.sh --case step_20mm --config oomwoo --speed 0.25
#
# 一键入口：没有 .venv 就先建环境（约 1–2 分钟），然后打开 MuJoCo viewer 看仿真。
# macOS 上 mujoco.viewer.launch_passive 必须用 mjpython 启动，本脚本自动选解释器；
# Windows 用 scripts\view.bat（逻辑相同）。
# 不带参数直接跑：./scripts/view.sh（平地，实时）。

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  echo "[view.sh] 首次运行：在 .venv 创建项目环境并安装依赖（约 1–2 分钟）"
  PYBIN=""
  for candidate in python3.13 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYBIN="$candidate"
      break
    fi
  done
  if [ -z "$PYBIN" ]; then
    echo "[view.sh] 找不到 python3，请先安装 Python 3.11+ 再重试" >&2
    exit 1
  fi
  "$PYBIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  if [ -f requirements.lock.txt ]; then
    REQ="requirements.lock.txt"
  elif [ -f requirements.txt ]; then
    REQ="requirements.txt"
  else
    echo "[view.sh] 仓库里既没有 requirements.lock.txt 也没有 requirements.txt" >&2
    exit 1
  fi
  echo "[view.sh] 安装 $REQ"
  .venv/bin/python -m pip install -r "$REQ"
fi

RUNNER=".venv/bin/python"
if [ "$(uname -s)" = "Darwin" ] && [ -x ".venv/bin/mjpython" ]; then
  RUNNER=".venv/bin/mjpython"
fi

exec "$RUNNER" "$HERE/view.py" "$@"
