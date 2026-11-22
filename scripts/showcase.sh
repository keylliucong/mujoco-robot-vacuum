#!/usr/bin/env bash
# MuJoCo 展示台：一条命令装好环境、给出菜单、打开 viewer。
#
# 用法:
#   ./scripts/showcase.sh                 # 菜单选工况
#   ./scripts/showcase.sh 1               # 平地直行（flat）
#   ./scripts/showcase.sh 3 --mode step   # 20 mm 台阶，空格单步
#   ./scripts/showcase.sh 4 --speed 1     # 30 mm 台阶，实时（透传参数覆盖默认 0.25）
#
# 本脚本只负责"装环境 + 选工况 + 调 scripts/view.sh"；物理、判定、HUD 全在
# scripts/view.py 里，模型和 case 文件都不改。不截图、不导出视频。
#
# 首次运行会在 .venv 建项目环境并安装 requirements.lock.txt（约 1–2 分钟，需联网）。

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"

say() { printf '%s\n' "$*"; }

usage() {
  cat <<'EOF'
MuJoCo 展示台

  ./scripts/showcase.sh                 打开菜单，按序号选工况
  ./scripts/showcase.sh <1-5> [参数…]    直接选工况；后续参数原样传给 view.py

工况:
  1) 平地直行（flat）
  2) 台阶 12.5 mm（未到壳体极限）
  3) 台阶 20 mm（壳体前下缘主导）
  4) 台阶 30 mm（超出当前模型上限）
  5) 基线自检（baseline）
  q) 退出

透传参数（默认已带 --speed 0.25；再给一次以最后的值为准）:
  --mode step          暂停起跑，按空格一帧一帧推进
  --speed 1            实时播放
  --step-size-s 0.05   单步模式每次前进 0.05 s
  -h, --help           显示本帮助

窗口内：左键拖拽旋转 / 滚轮缩放 / 右键拖拽平移 / 空格暂停或单步 / Esc 退出。
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

# ---------------------------------------------------------------- 1. 环境

say "[showcase] 检查 .venv 与 MuJoCo"
NEED_INSTALL=0
if [ ! -x ".venv/bin/python" ]; then
  NEED_INSTALL=1
elif ! .venv/bin/python -c "import mujoco" >/dev/null 2>&1; then
  NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" -eq 1 ]; then
  if [ ! -x ".venv/bin/python" ]; then
    say "[showcase] 首次运行：创建 .venv（约 1–2 分钟，需联网）"
    PYBIN=""
    for candidate in python3.13 python3 python; do
      if command -v "$candidate" >/dev/null 2>&1; then
        PYBIN="$candidate"
        break
      fi
    done
    if [ -z "$PYBIN" ]; then
      say "[showcase] 找不到 python3，请先安装 Python 3.11+ 再重试" >&2
      exit 1
    fi
    "$PYBIN" -m venv .venv
  fi

  if [ ! -f "requirements.lock.txt" ]; then
    say "[showcase] 缺少 requirements.lock.txt，无法安装依赖" >&2
    exit 1
  fi
  say "[showcase] 安装 requirements.lock.txt"
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  if ! .venv/bin/python -m pip install -r requirements.lock.txt; then
    say "" >&2
    say "[showcase] 依赖安装失败：先查网络，再确认 Python 架构（macOS arm64 需要 cp313 arm64 wheel）。" >&2
    say "[showcase] 替代命令（装好后仍用本脚本）：python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.lock.txt" >&2
    exit 1
  fi
  say "[showcase] 环境就绪"
else
  say "[showcase] 环境就绪（复用 .venv）"
fi

# ---------------------------------------------------------------- 2. 菜单

EXTRA=("$@")
CHOICE=""
if [ "${#EXTRA[@]}" -gt 0 ]; then
  case "${EXTRA[0]}" in
    1|2|3|4|5|q|Q) CHOICE="${EXTRA[0]}"; EXTRA=("${EXTRA[@]:1}") ;;
  esac
fi

if [ -z "$CHOICE" ]; then
  say ""
  say "MuJoCo 展示台 — 选一个工况，不用记工况名"
  say ""
  say "  1) 平地直行（flat）"
  say "  2) 台阶 12.5 mm（未到壳体极限）"
  say "  3) 台阶 20 mm（壳体前下缘主导）"
  say "  4) 台阶 30 mm（超出当前模型上限）"
  say "  5) 基线自检（baseline）"
  say "  q) 退出"
  say ""
  printf "选择 [1-5/q]: "
  if ! read -r CHOICE; then
    CHOICE="q"
  fi
fi

case "$CHOICE" in
  1) FIXED=(--case cases/flat.json --config proto_v1 --speed 0.25) ;;
  2) FIXED=(--case cases/oomwoo_g25_step12p5.json --config oomwoo_g25 --speed 0.25) ;;
  3) FIXED=(--case cases/oomwoo_g25_step20.json --config oomwoo_g25 --speed 0.25) ;;
  4) FIXED=(--case cases/oomwoo_g25_step30.json --config oomwoo_g25 --speed 0.25) ;;
  5) FIXED=(--case cases/baseline.json --config proto_v1 --speed 0.25) ;;
  q|Q|"")
    say "[showcase] 退出"
    exit 0
    ;;
  *)
    say "[showcase] 无效选择：$CHOICE（只能是 1–5 或 q）" >&2
    exit 2
    ;;
esac

# ---------------------------------------------------------------- 3. 启动

CMD=("$HERE/view.sh" "${FIXED[@]}")
if [ "${#EXTRA[@]}" -gt 0 ]; then
  CMD+=("${EXTRA[@]}")
fi

say "[showcase] 等价命令：scripts/view.py ${CMD[*]:1}"
say "[showcase] 窗口内：拖拽旋转 / 滚轮缩放 / 空格暂停或单步 / Esc 退出"
say ""
exec "${CMD[@]}"
