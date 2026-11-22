#!/usr/bin/env bash
# 把 Obsidian 库 越障仿真/ 单向镜像进仓库 docs/文献/精读笔记/。
# 只搬运 md（排除 .obsidian），目录 文献精读/ 在仓库侧改名为 精读/，
# 并在每个 md 顶部插入/刷新一行镜像注释（幂等，可重复运行）。
set -euo pipefail

# ---- 路径变量（按需修改）---------------------------------------------------
# Obsidian 库内的源目录（老板主库）
SRC="/Users/liucong/Documents/Codex/塑胶疲劳知识库/越障仿真"
# 仓库根目录：默认取脚本所在目录的上一级，便于在任意 worktree / 主仓库运行
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 镜像目标目录
DST="$REPO/docs/文献/精读笔记"
# 每个镜像文件顶部插入的注释
HEADER='<!-- 镜像自 Obsidian 库 越障仿真/，**以库内文件为准**；修改请先改库，再跑 scripts/sync-lit-notes.sh -->'

# ---- 同步 ------------------------------------------------------------------
if [ ! -d "$SRC" ]; then
  echo "错误：找不到 Obsidian 源目录：$SRC" >&2
  exit 1
fi

# 先同步到空暂存目录，只保留 md、排除 .obsidian
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
rsync -a --exclude '.obsidian' --include='*/' --include='*.md' --exclude='*' \
  "$SRC/" "$STAGE/"

# 文献精读/ -> 精读/
if [ -d "$STAGE/文献精读" ]; then
  mv "$STAGE/文献精读" "$STAGE/精读"
fi

# 单向覆盖到目标（--delete 清理库里已删除的文件）
mkdir -p "$DST"
rsync -a --delete "$STAGE/" "$DST/"

# ---- 顶部插入/刷新镜像注释（幂等）------------------------------------------
while IFS= read -r -d '' f; do
  if [ "$(head -n 1 "$f")" != "$HEADER" ]; then
    tmp="${f}.sync.tmp"
    { printf '%s\n' "$HEADER"; cat "$f"; } > "$tmp"
    mv "$tmp" "$f"
  fi
done < <(find "$DST" -name '*.md' -print0)

echo "同步完成：$SRC  ->  $DST"
