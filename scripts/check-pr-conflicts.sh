#!/usr/bin/env bash
# 拉取仓库全部 open PR 的文件列表，两两求交集，打印文件冲突对；
# 若同一路径在两个 PR 上 changeType 都是 ADDED，标为 [add/add]（结构性冲突，需先消一方）。
# 依赖：gh（已登录）、comm/sort/mktemp（macOS 自带）。无需 jq/python。
# 用法：./scripts/check-pr-conflicts.sh
#   REPO=owner/repo ./scripts/check-pr-conflicts.sh   # 指定仓库
set -euo pipefail

REPO="${REPO:-keylliucong/mujoco-robot-vacuum}"

if ! command -v gh >/dev/null 2>&1; then
  echo "错误：找不到 gh，请先安装 GitHub CLI。" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "错误：gh 未登录，请先执行 gh auth login。" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "正在读取 $REPO 的 open PR 列表…" >&2
prs="$(gh pr list --repo "$REPO" --state open --limit 200 --json number --jq '.[].number' | sort -n)"
if [[ -z "$prs" ]]; then
  echo "没有 open PR。"
  exit 0
fi

count=0
while IFS= read -r n; do
  [[ -z "$n" ]] && continue
  # 只用 gh pr view --json files 拉文件列表；重定向避免 ANSI 进度符混入。
  # 注意：GitHub 返回的字段是 changeType（ADDED/MODIFIED/REMOVED/RENAMED），不是 status。
  if ! gh pr view "$n" --repo "$REPO" --json files --jq '.files[].path' \
      | LC_ALL=C sort -u > "$tmp/$n.files" 2>/dev/null; then
    echo "警告：PR #$n 文件列表拉取失败，已跳过。" >&2
    continue
  fi
  gh pr view "$n" --repo "$REPO" --json files \
    --jq '.files[] | select(.changeType=="ADDED") | .path' \
    | LC_ALL=C sort -u > "$tmp/$n.added" 2>/dev/null || true
  count=$((count + 1))
done <<< "$prs"

echo
echo "=============================================================================="
echo " PR 文件冲突检查  repo=$REPO"
echo " 生成时间=$(date '+%Y-%m-%d %H:%M:%S')  成功读取 PR 数=$count"
echo " [add/add] = 两处都是 changeType=ADDED 的结构性冲突，需先消一方"
echo "=============================================================================="
echo

# 建立 文件 -> PR 列表 映射，用于末尾汇总。
: > "$tmp/file2pr.tsv"
while IFS= read -r n; do
  [[ -f "$tmp/$n.files" ]] || continue
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    printf '%s\t#%s\n' "$f" "$n" >> "$tmp/file2pr.tsv"
  done < "$tmp/$n.files"
done <<< "$prs"

pair_count=0
addadd_pair_count=0
nums=()
while IFS= read -r n; do
  [[ -z "$n" ]] && continue
  [[ -f "$tmp/$n.files" ]] && nums+=("$n")
done <<< "$prs"

for ((i=0; i<${#nums[@]}; i++)); do
  for ((j=i+1; j<${#nums[@]}; j++)); do
    a="${nums[$i]}"
    b="${nums[$j]}"
    common="$(LC_ALL=C comm -12 "$tmp/$a.files" "$tmp/$b.files")"
    [[ -z "$common" ]] && continue
    pair_count=$((pair_count + 1))
    added_common="$(LC_ALL=C comm -12 "$tmp/$a.added" "$tmp/$b.added")"
    n_added=0
    [[ -n "$added_common" ]] && n_added="$(printf '%s\n' "$added_common" | wc -l | tr -d ' ')"
    [[ "$n_added" -gt 0 ]] && addadd_pair_count=$((addadd_pair_count + 1))
    nfiles="$(printf '%s\n' "$common" | wc -l | tr -d ' ')"
    printf '[冲突对 %02d] PR #%s  <->  PR #%s   (%s 个重叠文件，其中 add/add %s 个)\n' \
      "$pair_count" "$a" "$b" "$nfiles" "$n_added"
    printf '%s\n' "$common" | while IFS= read -r f; do
      if printf '%s\n' "$added_common" | grep -Fqx -- "$f"; then
        printf '    [add/add] %s\n' "$f"
      else
        printf '    %s\n' "$f"
      fi
    done
    echo
  done
done

echo "=============================================================================="
echo " 汇总：重叠次数 >= 2 的文件"
echo "------------------------------------------------------------------------------"
printf '%-4s  %-60s  %s\n' "PR数" "文件路径" "涉及的 PR"
LC_ALL=C sort "$tmp/file2pr.tsv" \
  | awk -F '\t' '{ c[$1]++; p[$1] = p[$1] " " $2 }
                  END { for (f in c) if (c[f] >= 2) printf "%d\t%s\t%s\n", c[f], f, p[f] }' \
  | LC_ALL=C sort -k1,1nr -k2,2 \
  | while IFS=$'\t' read -r c f p; do printf '%-4s  %-60s %s\n' "$c" "$f" "$p"; done

echo
echo "冲突对总数：${pair_count}（其中含 add/add 的对数：${addadd_pair_count}）"
