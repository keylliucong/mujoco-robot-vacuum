#!/usr/bin/env bash
# 重建 docs/项目状态/交付物清单.md 的可重算表格。
# macOS 直接运行：bash scripts/refresh-deliverables.sh
# 只依赖 gh（用 gh 内置 --jq，不需要系统装 jq）和 bash 3.2+。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO_ROOT/docs/项目状态/交付物清单.md"
REPO_URL="$(gh repo view --json url -q .url 2>/dev/null || printf '%s' 'https://github.com/keylliucong/mujoco-robot-vacuum')"

# ---------------------------------------------------------------------------
# 人工标注区（脚本不生成、不覆盖）。
# 首次生成时用下面的种子；文件已存在时从文件里原样保留 BEGIN/END 之间的整段。
# 脚本只读取这里的值去填表格最后一列，绝不改写它。
# ---------------------------------------------------------------------------
read -r -d '' MANUAL_DEFAULT <<'MANUAL_EOF' || true
<!-- MANUAL:BEGIN -->
### 人工标注（脚本不覆盖，改这里即可）

> 本区人工维护。脚本重写表格时原样保留本区，并用这里的取值填表格「需要谁做什么」列。
> 取值只能是：老板定 / 专家签 / 无需动作（可在括号里补一句理由）。
> 新 PR 若未登记，该列显示「（待人工标注）」。

| PR | 需要谁做什么 |
|---|---|
| #18 | 无需动作（仅镜像搬运，正文未改） |
| #17 | 专家签（仿真专家评审，G2 基线候选） |
| #16 | 无需动作（仅 PDF 获取情况说明） |
| #15 | 专家签（架构师 + 仿真专家，G2 闸） |
| #14 | 老板定（是否按 688 算例预算开扫描；签字方待确认） |
| #13 | 无需动作（原型与验证输出已交付） |
| #12 | 老板定（4 个 P0 缺口需补数据，G0 输入冻结） |
| #11 | 无需动作（端到端穿跑骨架，不建模不实测） |
| #10 | 无需动作（仅文献库说明） |
| #9 | 无需动作（仅登记来源与抄录） |
| #8 | 无需动作（独立对照，供参考） |
| #7 | 老板定（PR 注明请勿合并，等 Program-leader 与老板确认口径） |
| #6 | 专家签（试验标定 + 仿真专家，验收限冻结） |
| #5 | 专家签（架构师 + 仿真专家；合并时机由 Program-leader 定） |
| #4 | 老板定（与 #2/#3 重叠 docs/仿真参数表.md 需先统一；签字方待确认） |
| #3 | 专家签（仿真专家确认 4.0.1 口径，评审中） |
| #2 | 无需动作（G1 仿真专家已签，待老板合并） |
<!-- MANUAL:END -->
MANUAL_EOF

if [[ -f "$OUT" ]] && grep -q '<!-- MANUAL:BEGIN -->' "$OUT" && grep -q '<!-- MANUAL:END -->' "$OUT"; then
  MANUAL_BLOCK="$(awk '/<!-- MANUAL:BEGIN -->/{f=1} f{print} /<!-- MANUAL:END -->/{exit}' "$OUT")"
else
  MANUAL_BLOCK="$MANUAL_DEFAULT"
fi

manual_value() {
  local n="$1" line v
  line="$(printf '%s\n' "$MANUAL_BLOCK" | grep -E "^\| #${n}[[:space:]]*\|" | head -1 || true)"
  if [[ -z "$line" ]]; then
    printf '%s' '（待人工标注）'
    return
  fi
  v="$(printf '%s' "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')"
  printf '%s' "$v"
}

# ---------------------------------------------------------------------------
# 人工整理的注释表：PR 号 -> 组号^一句话内容^看哪里^由谁产出（agent 类型）。
# 不是评审结论，只是索引用的描述与定位信息。字段里不含 ^ 和 |。
# ---------------------------------------------------------------------------
annot() {
  local n="$1" s=""
  case "$n" in
    18) s='3^把 Obsidian 里 16 篇文献精读笔记镜像进仓库，正文不改，附单向同步脚本^docs/文献/精读笔记/、scripts/sync-lit-notes.sh^CodeBuddy（同步 worker）' ;;
    17) s='1^用 oomwoo 可信 STEP 穿跑 STEP→质量属性→MJCF→runner→judge 全流程，含 Windows 四工况试跑报告^docs/试跑/oomwoo-全流程试跑.md、docs/试跑/step-质量属性-oomwoo.csv、cases/oomwoo_*.json、models/oomwoo.xml^CodeBuddy（试跑 worker）' ;;
    16) s='3^记录越障动力学文献 PDF 的开放渠道来源与校验结果；PDF 存本机不进仓库^docs/文献/PDF获取情况.md^CodeBuddy（pdf-fetch worker）' ;;
    15) s='1^G2 基线工况 runner 与 judge：工况配置、模型自检、重复一致性验证与运行记录^scripts/run_cases.py、judge.py、scripts/model_checks.py、cases/、docs/G2-运行与验证记录.md^CodeBuddy（实现 worker）' ;;
    14) s='2^G5 参数扫描设计：变量分级、区间与方法、灵敏度指标与 688 算例预算；只设计不跑^docs/判据/G5-扫描设计.md^CodeBuddy（判据 worker）' ;;
    13) s='1^原型整机越障：oomwoo 结构模板 + 参数外置 + 批运行入口，附两种接触锥验证输出^models/baseline.xml、scripts/build_model.py、scripts/run_cases.py、params/oomwoo.json、docs/验证输出/^CodeBuddy（原型 worker）' ;;
    12) s='4^提取 oomwoo 基准参数并区分公开参考与图纸推算，列出 S17 血缘和 4 个 P0 缺口^docs/基准机型/oomwoo-参数提取.md、docs/基准机型/oomwoo-缺口与影响.md、docs/基准机型/oomwoo-drive-wheel-dimensions.md^CodeBuddy（参数提取 worker）' ;;
    11) s='4^用 oomwoo 把取数→资产盘点→标签→台账→不确定度预算→报告骨架端到端穿跑，不建模不实测^docs/试验/基准机型/、docs/参数溯源.csv、docs/不确定度预算.csv^CodeBuddy（试验标定 worker）' ;;
    10) s='3^记录 Obsidian 越障仿真阅读库与 Zotero 集合的位置、结构和新增文献步骤；库在仓库外^docs/文献/Obsidian与Zotero文献库.md^CodeBuddy（资料检索 worker）' ;;
    9) s='3^三个基准机型仓库的来源可信度分级（A/B/C）与 oomwoo-one 全部 76 项参数原样抄录^docs/基准机型/来源清单.md、docs/基准机型/oomwoo-one-params.csv^CodeBuddy（资料核验 worker）' ;;
    8) s='1^OOMWOO 独立最小 MJCF 与 Windows 无界面三轮对照，记录三档台阶结果^models/codex-check.xml、scripts/codex_run.py、docs/复核/独立建模对照.md^Codex' ;;
    7) s='2^新增项目状态目录：状态说明、D-01 至 D-10 决策记录、G0–G6 进度看板与口径索引^docs/项目状态/README.md、docs/项目状态/决策记录.md、docs/项目状态/进度看板.md、docs/项目状态/口径索引.md^CodeBuddy（Program-leader bot）' ;;
    6) s='2^G4 试验侧模板与台账：记录表 v2、数据字典、uB 分量清单、验收限冻结骨架（只文档）^docs/试验/记录表模板-2026-11-21.md、docs/试验/数据字典.md、docs/试验/验收限冻结-2026-11-21.md、docs/不确定度预算.csv^CodeBuddy（试验标定 worker）' ;;
    5) s='2^G2 前置契约 v1.1–v1.7.1 冻结：机体系 B、图纸推算标签、verified_tol 口径与 12 条 ADR^docs/契约/G2-接口契约.md、docs/契约/G2-结构规则-违反即失败.md、docs/契约/ADR/^opencode（架构师 bot）' ;;
    4) s='2^资料检索第二/三轮：证据表、参数表校核、核心文献清单与算例校核；PR 由 Program-leader 代开^docs/检索日志与证据表.md、docs/文献阅读清单.md、docs/轮式台阶算例校核.md、docs/仿真参数表.md^CodeBuddy（资料检索 worker；PR 由 Program-leader 代开）' ;;
    3) s='1^按 MuJoCo 4.0.1 实测校正仿真参数与接触力口径：接触锥、mj_contactForce、积分器、环境^docs/仿真参数表.md、docs/仿真环境安装与版本.md、docs/检索日志与证据表.md^opencode（仿真专家 bot）' ;;
    2) s='1^G1 接触力读数校验：用 mj_contactForce 验证平地与斜面法向/切向误差，两种摩擦锥对照^scripts/verify_env.py、docs/接触力读数校验.md、docs/验证输出/2026-11-21_接触力读数_3f8b993.txt^opencode（仿真专家 bot）' ;;
  esac
  printf '%s' "$s"
}

# ---------------------------------------------------------------------------
# 从 gh 取数：PR 编号降序。失败时表格 cell 写「获取失败（原因）」。
# ---------------------------------------------------------------------------
GH_ERR=""
if ! ROWS="$(gh pr list --state open --json number,title,headRefName,isDraft,changedFiles,additions,updatedAt \
  --jq 'sort_by(-.number) | .[] | [.number, .title, .headRefName, (.isDraft|tostring), .changedFiles, .additions, .updatedAt] | @tsv' 2>&1)"; then
  GH_ERR="$ROWS"
  ROWS=""
fi

TH='| PR | 标题 | 分支 | 状态（draft\|open） | 改动规模 | 一句话内容 | 看哪里（关键文件路径） | 由谁产出（agent 类型） | 需要谁做什么（老板定 / 专家签 / 无需动作） |'
TD='|---|---|---|---|---|---|---|---|---|'
G0=''; G1=''; G2=''; G3=''; G4=''
LATEST_UPD=''

while IFS=$'\t' read -r num title branch draft cf add upd; do
  [[ -z "${num:-}" ]] && continue
  if [[ -n "$upd" && ( -z "$LATEST_UPD" || "$upd" > "$LATEST_UPD" ) ]]; then LATEST_UPD="$upd"; fi
  title="${title//|/\\|}"
  branch="${branch//|/\\|}"
  if [[ "$draft" == 'true' ]]; then status='draft'; else status='open'; fi

  ann="$(annot "$num")"
  if [[ -n "$ann" ]]; then
    IFS='^' read -r grp summary files agent <<< "$ann"
  else
    grp='0'; summary='（待补注）'; files='（待补注）'; agent='（待补注）'
  fi

  row="| [#${num}](${REPO_URL}/pull/${num}) | ${title} | \`${branch}\` | ${status} | ${cf} 文件 / +${add} 行 | ${summary} | ${files} | ${agent} | $(manual_value "$num") |"
  case "$grp" in
    1) G1="${G1}${row}"$'\n' ;;
    2) G2="${G2}${row}"$'\n' ;;
    3) G3="${G3}${row}"$'\n' ;;
    4) G4="${G4}${row}"$'\n' ;;
    *) G0="${G0}${row}"$'\n' ;;
  esac
done <<< "$ROWS"

emit_group() {
  local id="$1" name="$2" body
  case "$id" in
    1) body="$G1" ;; 2) body="$G2" ;; 3) body="$G3" ;; 4) body="$G4" ;; *) body="$G0" ;;
  esac
  printf '### %s\n\n' "$name"
  printf '%s\n%s\n' "$TH" "$TD"
  if [[ -n "$body" ]]; then
    printf '%s' "$body"
  elif [[ -n "$GH_ERR" ]]; then
    printf '| 获取失败（%s） | — | — | — | — | — | — | — | — |\n' "$(printf '%s' "$GH_ERR" | tr '\n\r|' '   ' | tr -d '\`')"
  else
    printf '| （本组暂无 PR） | — | — | — | — | — | — | — | — |\n'
  fi
  printf '\n'
}

TS="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
mkdir -p "$(dirname "$OUT")"
{
  printf '本表由脚本生成，最后一次：%s\n\n' "$TS"
  printf '# 交付物清单\n\n'
  printf '> 这是索引，不是评审结论。PR 号、标题、分支、状态、改动规模、更新时间均由 `gh pr list` 取数。\n'
  printf '> 数据快照：最新 updatedAt = %s。重算：`bash scripts/refresh-deliverables.sh`（按 PR 编号降序）。\n\n' "${LATEST_UPD:-（无）}"

  printf '%s\n\n' "$MANUAL_BLOCK"

  printf '## 分组总表\n\n'
  emit_group 1 '1. 能直接判断结果的（结论性交付）'
  emit_group 2 '2. 要你定或要专家签字的（卡主线的）'
  emit_group 3 '3. 文献相关'
  emit_group 4 '4. 流程与状态（不必细看）'
  if [[ -n "$G0" ]]; then emit_group 0 '未归类（新 PR，待人工补注）'; fi

  cat <<'PATH_EOF'
## 本机可直接看的路径

- Obsidian 库（文献精读笔记主库，以库内文件为准）：`/Users/liucong/Documents/Codex/塑胶疲劳知识库/越障仿真/`
- `refs/`（文献 PDF 原件，不进仓库）：`/Users/liucong/orca/projects/mujoco_/refs/`
- worker 工作区（`orca worktree ps` 可列出）：
  - `oomwoo-sources` → `/Users/liucong/orca/workspaces/mujoco_/oomwoo-sources`
  - `lit-mirror` → `/Users/liucong/orca/workspaces/mujoco_/lit-mirror`
  - `pdf-fetch` → `/Users/liucong/orca/workspaces/mujoco_/pdf-fetch`
  - `pr-merge-plan` → `/Users/liucong/orca/workspaces/mujoco_/pr-merge-plan`
  - `deliverables-index` → `/Users/liucong/orca/workspaces/mujoco_/deliverables-index`（本清单）
  - `架构师`（bot）→ `/Users/liucong/.orca/bots/bot-2`
  - `仿真专家`（bot）→ `/Users/liucong/.orca/bots/new-bot`

## 列含义与维护方式

- `PR / 标题 / 分支 / 状态 / 改动规模` 和文件头的 UTC 时间由脚本从 `gh` 重算；改动规模格式为「文件数 / 新增行数」。
- `一句话内容 / 看哪里 / 由谁产出` 是人工整理的索引注释，写在脚本的 `annot()` 里；新 PR 未登记时显示「（待补注）」。
- `需要谁做什么` 只在上文「人工标注」区维护；脚本保留该区原样，并据此填表，不会自己生成或覆盖它。
- 各分组按上表顺序固定；新出现的 PR 若未登记分组，会落到最后的「未归类」区，等待人工补注。
PATH_EOF
} > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
printf '已重建：%s（%s 行表格内容）\n' "$OUT" "$(printf '%s' "$G0$G1$G2$G3$G4" | grep -c '^| \[' || true)"
