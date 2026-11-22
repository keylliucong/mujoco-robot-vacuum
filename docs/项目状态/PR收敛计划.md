# PR 收敛计划

> 数据口径：2026-11-22 用 `gh pr list` / `gh pr view --json files` 读取 `keylliucong/mujoco-robot-vacuum` 的全部 open PR。任务给出的 17 个（#2–#18）之外，分析期间新开了 **#19**，当前共 **18 个**；#19 零文件冲突，不改变合并顺序。`base` 与文件重叠均来自 GitHub 实际返回，未读到的信息不猜；GitHub 的变更类型字段是 `changeType`（`ADDED`/`MODIFIED`/`REMOVED`/`RENAMED`），不是 `status`。注意 PR #5 的不确定度预算 stub 已在 `bdb8db0` 删除，下表为删除后的最新状态。本计划只做分析，不合并任何 PR。

## 状态更新（2026-11-22 晚）

下表写于第一批收敛之前，**已不再代表当前远端**，保留作历史判断。现状：

| PR | 现状 |
| --- | --- |
| #1 / #2 / #5 | 已并入 main（源分支已删） |
| #10 / #16 / #18 | 已收敛成 `docs/lit`，PR #22 并入 main，三个旧 PR 关闭、分支删除 |
| #7 / #19 / #20 | 已收敛成 `docs/state`，PR #23 并入 main，三个旧 PR 关闭、分支删除 |
| #6 / #11 | 已收敛成 `trial/g4`，PR #24 开放、对 main 为 `MERGEABLE/CLEAN`，两个旧 PR 关闭、分支删除 |
| #8 / #13 / #15 / #17 / #21 | 仍开放，全部归 `feat/g2-pipeline`；方案见文末「第二批」 |
| #3 / #4 / #9 / #12 / #14 | 仍开放，尚需指定归属（见文末 §8） |

## 合并计划表

| PR | 标题 | base | 文件重叠（与哪些 PR 改同一文件） | 建议动作 | 理由一句 | 依赖（等哪个先合） |
| --- | --- | --- | --- | --- | --- | --- |
| #2 | G1: 接触力读数校验（R1/R4） | main | #3、#4、#13：`README.md`、`docs/仿真环境安装与版本.md`、`scripts/verify_env.py` | **暂不合** | 老板已明确"先不合并，等 G2 一起看"；正文也声明不碰 G2 的 `models/`、`cases/`、`scripts/run_cases.py`。 | 等 G2（#5/#15）评审后人工解除 |
| #3 | docs: 按 MuJoCo 4.0.1 实测校正仿真参数与接触力口径 | main | #2、#4、#13：`docs/仿真参数表.md`、`docs/仿真环境安装与版本.md`；#4：`docs/检索日志与证据表.md` | **后合（rebase 重开）** | 虽非 draft 且只改文档，但与上游 #4 同改参数表/证据表两份文件，须待 #4 落盘后统一口径再 rebase。 | #4 |
| #4 | docs: 资料检索第二轮/第三轮（证据表、参数表校核、文献清单） | main | #2、#3、#13：`README.md`、`docs/仿真参数表.md`、`docs/检索日志与证据表.md`、`.gitignore`；#15、#18：`.gitignore` | **先合** | 资料检索是参数表/证据表的上游稿，先合它再让 #3/#13/#18 rebase，符合"上游先合"原则。 | 无 |
| #5 | 契约 v1.1–v1.7.1（冻结） | main | #17：全部 `docs/契约/`（15 文件，add/add）；#6/#11 的 `docs/不确定度预算.csv` 冲突已随 `bdb8db0` 删 stub 消除 | **先合（最高优先）** | 是 G2 实现 #15 的 base，#5 不合 #15 必不能合；契约路径只留声明、不留实现副本的做法已落实。 | 无（#15 硬依赖它） |
| #6 | 试验: G4 记录表模板 v2 + 数据字典 + uB 分量清单 + 验收限冻结骨架 | main | #11、#17：`docs/不确定度预算.csv`、`docs/参数溯源.csv`；#15：`docs/参数溯源.csv` | **后合（rebase 后合）** | 试验模板依赖 #5 的 §6.4 口径，且两份台账 csv 被 #11/#15/#17 重复新增，须以 #6 为准消副本。 | #5、#9；台账以它为准 |
| #7 | docs: 新增项目状态目录（状态、决策记录、进度看板、口径索引） | main | 无 | **暂不合** | 零冲突且只改文档，但正文明示"请勿合并，等待 Program-leader 与老板确认口径内容"。 | 老板/PL 确认口径 |
| #8 | OOMWOO 独立最小模型与 Windows 对照 | main | 无 | **后合** | 零冲突但含模型与脚本、属独立复核产物，既不依赖也不推进 G2 主线，排在主线之后。 | 无 |
| #9 | docs: 基准机型来源可信度分级与 oomwoo-one 参数抄录 | main | 无 | **先合** | 只改文档且零冲突，是 #11/#12/#17 基准机型取数的上游输入。 | 无 |
| #10 | docs: 越障仿真 Obsidian 阅读库与 Zotero 集合 | main | 无 | **先合** | 只改文档且零冲突，内容派生自 #4 的文献阅读清单，排在 #4 之后即可降低堆积。 | #4（内容口径，非文件冲突） |
| #11 | 试验: oomwoo 基准机型端到端穿跑（取数 → 标签 → 台账 → 报告骨架） | main | #6、#17：`docs/不确定度预算.csv`、`docs/参数溯源.csv`；#15：`docs/参数溯源.csv` | **后合（rebase 后合）** | 与 #6 同改两份台账 csv（均为 add/add），且来源/口径依赖 #5/#9，须删副本后 rebase。 | #5、#6、#9 |
| #12 | docs(基准机型): 提取 OOMWOO 基准参数、S17 血缘与 P0 缺口 | main | 无（与 #9 同目录但不同文件） | **后合** | 与 #9 同为基准机型来源侧且文件不重叠，但结论应吸收 #9 的分级，排在 #9 之后。 | #9 |
| #13 | proto: oomwoo 结构模板 + 参数外置 + 通用样机批运行入口 | main | #2、#3、#4：`README.md`、`docs/仿真参数表.md`、`docs/仿真环境安装与版本.md`、`.gitignore`、`scripts/verify_env.py`；#15：`cases/baseline.json`、`models/baseline.xml`、`scripts/run_cases.py`（add/add）及 `.gitignore`；#17：`cases/baseline.json`、`models/baseline.xml`、`params/oomwoo.json`、`scripts/run_cases.py`（add/add）；#18：`.gitignore` | **后合（rebase 收编）** | 非 draft 但同时撞上文档簇与 #15/#17 的 runner 文件（均 add/add），须等 #4、#15 定稿后删副本 rebase，仅保留 `build_model.py`、`params/hypothetical.json` 等独有内容。 | #4、#5、#15 |
| #14 | docs: G5 参数扫描设计（只设计，不跑扫描） | main | 无 | **先合** | 只改文档且零冲突，设计稿可先落盘；其执行依赖 #13 与实测数据，但不阻塞文档合入。 | 执行依赖 #13（合入不依赖） |
| #15 | G2: baseline-case runner, judge, model self-checks (draft) | contract/g2-interface（即 #5 的 head） | #6、#11：`docs/参数溯源.csv`；#13：`.gitignore` + `cases/baseline.json`、`models/baseline.xml`、`scripts/run_cases.py`；#17：16 文件（runner/judge/cases/契约）；#18：`.gitignore` | **后合（#5 后立即合）** | base 就是 #5 的分支，#5 不合必不能合；它是契约基线的 runner，#13/#17 的 add/add 副本应以它为基准删除。 | #5（硬依赖） |
| #16 | docs: PDF 获取情况（越障动力学文献） | main | 无 | **后合（或收编）** | 只改文档且零冲突，纯文献侧分析产物，可随第二批零冲突 doc 一并合。 | 无 |
| #17 | dryrun(oomwoo): STEP→质量属性→MJCF→runner 全流程试跑 | main（正文自述实际基于 `feature/g2-baseline-runner`） | #5：`docs/契约/`（15 文件，add/add）；#6、#11：`docs/不确定度预算.csv`、`docs/参数溯源.csv`；#13：`cases/baseline.json`、`models/baseline.xml`、`params/oomwoo.json`、`scripts/run_cases.py`；#15：16 文件（含 14 个 add/add） | **关闭重开（最该先关）** | 47 文件里约 31 个是依赖分支（#5 契约 15 个 + #15 runner 16 个）整包带进 base=main 的 PR，几乎全是 add/add 结构性冲突，硬合会把契约与 runner 重复落进 main 并制造 5 对冲突。 | #5、#15（删副本 rebase 后重开） |
| #18 | docs: 镜像 Obsidian 文献精读笔记到仓库（16 篇） | main | #4、#13、#15：`.gitignore` | **后合（rebase 后合）** | 主体是零冲突的文献镜像文档，只有 `.gitignore` 与三个 PR 同改，待 #4 先合后 rebase 即可。 | #4（`.gitignore` 上游） |
| #19 | docs: 可自动重算的交付物清单（索引，非评审结论）（分析期间新开） | main | 无 | **后合（零冲突）** | 只新增 `docs/项目状态/交付物清单.md` 与 `scripts/refresh-deliverables.sh`，与任何 PR 无文件重叠，随第二批收尾即可。 | 无 |

## 建议的合并顺序

**第一批（5 个，能立刻推进主线）**：`#5 → #4 → #9 → #10 → #14`。#5 是契约冻结稿，也是 #15 的硬依赖，必须先合才能启动 G2；#4 是参数表/证据表的上游稿，先合可让 #3、#13、#18 有稳定的 rebase 基准；#9 提供基准机型来源分级，是 #11/#12/#17 的共同输入；#10 与 #14 都是零冲突的纯文档，内容分别派生自 #4、服务于后续 G5 扫描，先合能直接降低堆积。注意 #5 正文写"等 PR #2 合并后"，但老板已改口 #2 暂不合，按本计划以 #5 为准解耦，不必等 #2。

**第二批**：#5 落地后立即合 **#15**（G2 主线），同时收尾零冲突文档 **#12、#16、#19**，以及删副本/rebase 后的 **#6、#11**（台账以 #6 为准，#11 删自己的副本）；**#8** 作为独立对照随后合入。**第三批**：rebase 重开 **#3**（基于 #4）、**#13**（基于 #15，只留独有内容）、**#18**（基于 #4 的 `.gitignore`）、**#17**（基于 #5+#15，只留 dryrun 增量）。**#2 与 #7 保持暂不合**：#2 等 G2 一起看，#7 等老板/PL 确认口径，均不进入任何合并批次。

## 文件冲突清单

脚本 `scripts/check-pr-conflicts.sh` 在 #5 删 stub 后实测 **19 对**冲突（删 stub 前为 21 对，少了 #5↔#6、#5↔#11 两对），集中在以下文件簇：`docs/仿真参数表.md` 被 **#3、#4、#13** 改，`docs/仿真环境安装与版本.md` 被 **#2、#3、#13** 改，`docs/检索日志与证据表.md` 被 **#3、#4** 改，`README.md` 被 **#2、#4、#13** 改，`scripts/verify_env.py` 被 **#2、#13** 改；`.gitignore` 是最广的共享文件，被 **#4、#13、#15、#18** 四个 PR 同时改（这四处是 `MODIFIED`，不是 add/add）。契约/试验侧：`docs/不确定度预算.csv` 被 **#6、#11、#17** 改（#5 的 stub 已删），`docs/参数溯源.csv` 被 **#6、#11、#15、#17** 改，`docs/契约/` 整套 15 个文件被 **#5 与 #17** 同时改（#17 把 #5 整包带了进来）。运行器侧：`cases/baseline.json`、`models/baseline.xml`、`scripts/run_cases.py` 被 **#13、#15、#17** 三者同改；`params/oomwoo.json` 被 **#13、#17** 改，`params/prototype.json` 被 **#15、#17** 改；#15 与 #17 另共享 `_runner.json`、`flat.json`、`cases/invalid/*`、各 `step_*.json`、`judge.py`、`scripts/model_checks.py`、`scripts/params_io.py`、`scripts/verify_structure.py` 等共 16 个文件。按"上游先合"处理：`.gitignore` 以 #4 为基准，两份台账 csv 以 #6 为基准，契约以 #5 为基准，runner 以 #15 为基准，其余一律 rebase 重开；凡两处都 `ADDED` 的路径按下一节先消一方，不硬合。

## add/add 与结构性冲突

判定规则：**契约只声明路径，文件由实现侧提供，库里只留一份**。同一路径在两个 PR 上都是 `changeType=ADDED` 即为结构性冲突，谁先合都会撞，必须先删一方；保留实现侧/权威侧那份，副本侧删除并改为引用。

| 路径 | 涉及的 PR（均为 ADDED） | 保留谁 | 已消 / 待消 |
| --- | --- | --- | --- |
| `docs/不确定度预算.csv` | #6、#11、#17（另有 #5 旧 stub） | 保留 #6（33 行真数据）；#11/#17 删副本引用 #6 | **已消一例**：#5 stub 已在 `bdb8db0` 删除；#11/#17 副本**待消** |
| `docs/参数溯源.csv` | #6、#11、#15、#17 | 保留 #6（41 行×9 列试验侧台账）；#15 对齐 #6 列口径后合入，#11/#17 删副本 | **待消** |
| `docs/契约/ADR/ADR-001..012`、`docs/契约/README.md`、`docs/契约/G2-接口契约.md`、`docs/契约/G2-结构规则-违反即失败.md`（15 文件） | #5、#17 | 保留 **#5**（契约权威稿，此类是契约正文不是实现副本）；#17 删这 15 个副本 | **待消** |
| `models/baseline.xml`、`cases/baseline.json`、`scripts/run_cases.py` | #13、#15、#17 | 保留 **#15**（契约基线实现，含 S01–S21 自检）；#13/#17 删副本后 rebase | **待消** |
| `params/oomwoo.json` | #13、#17 | 保留 **#17**（已吸收 #9/#12 来源分级与 STEP 质量属性）；#13 删副本 | **待消** |
| `params/prototype.json` | #15、#17 | 保留 **#15**（G2 契约基线参数集）；#17 删副本 | **待消** |
| `cases/_runner.json`、`cases/flat.json`、`cases/invalid/*`、`cases/step_*.json`、`judge.py`、`scripts/model_checks.py`、`scripts/params_io.py`、`scripts/verify_structure.py`（14 文件） | #15、#17 | 保留 **#15**（G2 runner 权威实现）；#17 删副本 | **待消** |

**契约侧副本核查**：#5 当前 16 个文件全部是 `docs/契约/` 正文，**没有**契约指定路径（`models/`、`cases/`、`scripts/`、两份台账 csv）的实现副本——#5 原带的 `docs/不确定度预算.csv` stub 已在 `bdb8db0` 删除，这一例已消。不要再给 #5 补任何实现文件，补了就变成两个家。#17 是唯一仍把契约/runner 整包复制进来的 PR，必须先删副本再重开。

## 建议关闭或收编的 PR

**#17（最该先关）→ 关闭后 rebase 重开**：它把 #5 契约 15 个文件和 #15 runner 16 个文件整包塞进 base=main 的 PR（共 47 文件），几乎全是 add/add 结构性冲突，硬合会把依赖分支内容重复落进 main 并与 5 个 PR 冲突；关闭本 PR，待 #5/#15 合并后从新 main rebase，只保留 `docs/试跑/`、`models/oomwoo.xml`、`scripts/run_oomwoo.py`、`scripts/step_mass_properties.py`、`cases/oomwoo_*.json` 等 dryrun 增量，再开新 PR。**#13 → 收编进 #15/#17**：其 `cases/baseline.json`、`models/baseline.xml`、`scripts/run_cases.py` 已被契约基线 #15 和 oomwoo dryrun #17 覆盖，rebase 后仅保留 `build_model.py`、`params/hypothetical.json`、`docs/判据/口径裁定记录.md` 等独有内容合入，确认无独有内容则关闭。**#16 → 收编进 #10**：同为文献侧纯分析产物（PDF 获取情况 + 外部文献库说明），作为 #10 的一节合入，少留一个独立 PR；#10 本身先按第一批合入。**#3 与 #18 不关闭**：二者各有真实增量，按上表 rebase 后重开即可。

## 2026-11-22 第二批：feat/g2-pipeline 收敛方案（#8 #13 #15 #17 #21）

> 口径：基于 main `5ee880c`。文件清单用 `git diff --name-status origin/main...<head>`（三点 = PR 自身改动）；重叠按逐文件 blob 比对；冲突数用 `git merge-tree --write-tree` 实测；cherry-pick 结论是在 `origin/dryrun/oomwoo-step` 上开临时 worktree 逐个 `git cherry-pick -n` 跑出来的（worktree 与探针分支已删）。**本节只出方案：不建 `feat/g2-pipeline`、不合并、不关闭这五个 PR。**

### 1. 每个 PR 的文件清单

**#17 `dryrun/oomwoo-step`（建议骨架）**：25 提交，32 文件（31 新增 + 1 改既有）

- `cases/` 13：`_runner.json`、`_runner_oomwoo.json`、`baseline.json`、`flat.json`、`invalid/expected_key.json`、`invalid/flat_with_obstacle.json`、`oomwoo_flat.json`、`oomwoo_step10.json`、`oomwoo_step10_lowtorque.json`、`oomwoo_step20_casterblock.json`、`step_forward_20mm_low_torque.json`、`step_oblique_minus30.json`、`step_oblique_plus30.json`
- 模型/参数 4：`models/baseline.xml`、`models/oomwoo.xml`、`params/prototype.json`、`params/oomwoo.json`
- 脚本 8：`judge.py`、`scripts/model_checks.py`、`scripts/params_io.py`、`scripts/run_cases.py`、`scripts/run_oomwoo.py`、`scripts/slope_hold.py`、`scripts/step_mass_properties.py`、`scripts/verify_structure.py`
- 台账 1：`docs/参数溯源.csv`（108 行，见 §7）
- 试跑 5：`docs/试跑/oomwoo-全流程试跑.md`、`docs/试跑/step-质量属性-oomwoo.{csv,meta.json}`、`docs/试跑/step-质量属性-逐实体-oomwoo.csv`、`docs/试跑/参数溯源-oomwoo.csv`
- 改既有 1：`docs/契约/G2-接口契约.md`（main 1.7.1 → 支上 1.8.1）

**#15 `feature/g2-baseline-runner`**：23 提交，18 文件（17 新增 + `.gitignore`）

- `cases/` 8：`_runner.json`、`baseline.json`、`flat.json`、`invalid/expected_key.json`、`invalid/flat_with_obstacle.json`、`step_forward_20mm_low_torque.json`、`step_oblique_minus30.json`、`step_oblique_plus30.json`
- `judge.py`、`models/baseline.xml`、`params/prototype.json`、`scripts/{model_checks,params_io,run_cases,verify_structure}.py`、`docs/G2-运行与验证记录.md`、`docs/参数溯源.csv`（110 行运行器 xpath 台账 = #17 的 108 行 + `wheel/caster.frictionloss_nm` 2 行）

**#13 `proto/baseline-cases`**：27 提交，23 文件（18 新增 + 5 改既有）

- 新增 18：`.gitattributes`、`cases/baseline.json`、`models/baseline.xml`、`params/{hypothetical,oomwoo}.json`、`scripts/{build_model,run_cases,verify_contact_readout}.py`、`docs/判据/口径裁定记录.md`、`docs/基准机型/oomwoo.md`、`docs/验证输出/` 8 份（3 批次 × run/summary + 2 份接触力原始读数）
- 改既有 5：`.gitignore`、`README.md`、`docs/仿真参数表.md`、`docs/仿真环境安装与版本.md`、`scripts/verify_env.py`（base 是 `ddf8875`，对 main 现值属回退）

**#21 `feat/mujoco-viewer`**：39 提交，51 文件（相对 base `d121b86`）；对 main 是 **36 新增 + 8 个会回退 main**

- 新增 36：pipeline 旧副本 26（`cases/` 13、`judge.py`、`models/` 2、`params/` 2、`scripts/` 7、`docs/参数溯源.csv`）+ `docs/试跑/` 5 + `docs/不确定度预算.csv` 1 + viewer 4（`scripts/view.py`、`view.sh`、`view.bat`、`docs/使用/启动Viewer看仿真.md`）
- 会回退 main 的 8：`.gitignore`、`README.md`、`docs/仿真环境安装与版本.md`、`docs/契约/ADR-011-不确定度分量用status三值.md`、`docs/契约/ADR/README.md`、`docs/契约/G2-接口契约.md`、`docs/契约/G2-结构规则-违反即失败.md`、`scripts/verify_env.py`

**#8 `keylliucong/codex-check`**：2 提交，3 文件（`models/codex-check.xml`、`scripts/codex_run.py`、`docs/复核/独立建模对照.md`），与任何支零重叠。

### 2. 两两交集

单元格 = `共同文件数 / 其中逐字相同数 / 整支 merge 的冲突文件数`。

| | #13 | #15 | #17 | #21 | #8 |
| --- | --- | --- | --- | --- | --- |
| **#13** | — | 4 / 0 / 5 | 4 / 0 / 6 | 4 / 0 / 4 | 0 / 0 / 0 |
| **#15** | | — | 16 / 1 / 13 | 16 / 1 / 15 | 0 / 0 / 0 |
| **#17** | | | — | 32 / 8 / 15 | 0 / 0 / 0 |
| **#21** | | | | — | 0 / 0 / 0 |
| **#8** | | | | | — |

- **#15 ∩ #17 = 16 个**（runner 全套）：`cases/{_runner,baseline,flat,invalid/*,step_*}.json`、`judge.py`、`models/baseline.xml`、`params/prototype.json`、`scripts/{model_checks,params_io,run_cases,verify_structure}.py`、`docs/参数溯源.csv`。**只有 `scripts/params_io.py` 逐字相同**，其余 15 个全不同 → 不是"一前一后"，是两条独立演化的实现线。
- **#17 ∩ #21 = 32 个**（viewer 支几乎整包是 #17 的旧快照）：8 个逐字相同（`cases/_runner.json`、`docs/参数溯源.csv`、`docs/试跑/step-质量属性-*` 3 个、`params/prototype.json`、`scripts/params_io.py`、`scripts/step_mass_properties.py`）。
- **#13 ∩ #15 / #17 / #21 = 4 个**：`cases/baseline.json`、`models/baseline.xml`、`scripts/run_cases.py`（+ 对 #15 是 `.gitignore`、对 #17/#21 是 `params/oomwoo.json`），0 个逐字相同。
- 冲突数里有一部分是"老 base 的整文件回退型冲突"（#13 的 `README.md`/`docs/仿真环境安装与版本.md`/`scripts/verify_env.py`，#21 的 4 份契约/ADR），不是双方真在同一段代码上打架——但结论一样：这两支不能整支 merge。

### 3. 同一件事的不同实现：留谁、丢谁

| 主题 | 谁做过 | 实测差异 | 保留 | 丢掉 |
| --- | --- | --- | --- | --- |
| runner 主线（`run_cases.py`+`judge.py`+`cases/`+`models/baseline.xml`） | #13 / #15 / #17 | #13：1832 行、模板 `{{}}` + `build_model.py` 预生成 XML、契约 1.7.1；#15：1301 行、`${}` 运行时展开、契约 1.8.0、有 `frictionloss` 与 12 mm 行程；#17：1305 行、契约 1.8.1（`t_wheel_touch_s`、`belly_contact`）、多 `model_has_suspension`、含 oomwoo 模型与试跑 | **#17** | #13、#15 的 runner 副本（#15 的 `frictionloss`/12 mm 是否回灌单独定） |
| 模型模板语法 | #13 vs #15/#17 | `{{}}` 预生成 `build/models/*.xml` vs `${}` 运行时展开，同一路径互斥 | #17 | #13 的 `models/baseline.xml` |
| 契约正文 | main 1.7.1 / #17 1.8.1 / #21 旧副本 | #21 还把 main 的 ADR-011 补记整段删掉 | main ⊕ #17（手工合 1.8.1） | #21 的 15 份契约副本 |
| `docs/不确定度预算.csv` | #21（`label` 表头 stub）/ trial/g4（`status` 15 列 43 行） | #21 是 v1.7.2 之前的旧 schema；ADR-011 补记已裁定该路径归试验侧 | **trial/g4（#24）** | #21 |
| `docs/参数溯源.csv` | #15（110 行）/ #17、#21（108 行）运行器 xpath 台账；trial/g4（77 行）试验台账 | 同名同表头（9 列），**三支 `param_id` 与试验侧零重叠**；#15 = #17 的 108 行 + `frictionloss` 2 行 | **trial/g4 ∪ 运行器台账（108，回灌 frictionloss 则 110）** | 谁都不能整份丢（见 §7） |
| 独立对照模型 | #8 独有 | 零重叠 | #8 全收 | — |
| viewer | #21 独有（`view.py` 1076 行 + 包装 + 使用文档） | 依赖 `run_cases.build_scenario_xml`/`judge.judge_case`/`build_judge_params`，`sample_row` 签名差一个 `has_suspension` | #21 的 4 个文件 + 1 行补丁 | 其余 47 个旧副本 |

### 4. 哪些能直接 cherry-pick、哪些要手工

实测（在 #17 的 head 上逐个跑）：

| 对象 | 形式 | 结果 |
| --- | --- | --- |
| `3c740a8`（#21 viewer 4 文件） | 提交 | **干净**，+1320 行 |
| `a35c21e`、`dbb2eda`（#8） | 提交 | **干净**，3 文件 |
| `d167531`（#13 `.gitattributes`） | 提交 | **干净**，+9 行 |
| `db0025d`（#15 isotropic friction） | 提交 | **空**：与 #17 的 `2535084` 同 patch-id，已含 |
| `bc93175`（#15 契约 1.8.0） | 提交 | 11 文件冲突（cases/judge/model_checks/run_cases/verify_structure） |
| `9c6a1af`（#15 frictionloss） | 提交 | 7 文件冲突（cases + 参数） |
| `fbc4942`（#13 proto 首版） | 提交 | 6 文件冲突（README/cases/model/params/run_cases） |
| `5c0f26d`、`1a7f5c3`（#13 docs） | 提交 | 冲突（`docs/基准机型/oomwoo.md`、`docs/仿真环境安装与版本.md` 在 #17 不存在 → modify/delete） |
| `e34ab85`、`c52b229`（#15 运行记录） | 提交 | 同上；**文件级取用干净** |
| #13 的 8 份验证输出 + 口径裁定记录 + 基准机型 + `build_model.py` + `verify_contact_readout.py` + `hypothetical.json` | 文件级 `git checkout <ref> -- <paths>` | **干净** |
| `docs/契约/G2-接口契约.md` | 手工 | main 1.7.1 与 #17 1.8.1 需人工定版 |
| `docs/参数溯源.csv` | 手工 | 77 ∪ 108 = 185 行 |
| `scripts/view.py` | 手工补丁 | `sample_row(..., has_suspension)` 补一参，否则运行时 TypeError |

### 5. 建议的分支构成

```sh
# 骨架 = #17 的 head（338db4b），不是 main
feat/g2-pipeline ← origin/dryrun/oomwoo-step
  + cherry-pick 3c740a8                     # viewer 4 文件
  + cherry-pick a35c21e dbb2eda             # #8 独立模型 3 文件
  + cherry-pick d167531                     # .gitattributes（LF）
  + checkout #15 -- docs/G2-运行与验证记录.md
  + checkout #13 -- docs/验证输出/ docs/判据/口径裁定记录.md docs/基准机型/oomwoo.md \
                    scripts/build_model.py scripts/verify_contact_readout.py params/hypothetical.json
  + 手工：docs/契约/G2-接口契约.md（main 1.7.1 ⊕ #17 1.8.1）
  + 手工：docs/参数溯源.csv（trial/g4 77 行 ∪ #17 108 行）
  + 补丁：scripts/view.py 的 sample_row 调用补 has_suspension
```

规模预估：22 文件 / 约 +12000 行（骨架之外），`py_compile` 已过。建议**先合 #24（trial/g4）再起 pipeline**，否则 `docs/参数溯源.csv` 要做两遍并集。

### 6. base 会不会断（明确回答）

**建分支这一刻不会断，但删分支的顺序错了会连带关掉 #21。**

- 五个 PR 里**只有 #21 的 base 是 `dryrun/oomwoo-step`**（PR #21 → base `dryrun/oomwoo-step`）；#13/#15/#17/#8 以及其余全部 open PR 的 base 都是 `main`（已用 `gh pr list --json baseRefName` 核对）。
- 新分支从 #17 的 head 起、不删不改 `dryrun/oomwoo-step`，所以任何人的 base 都还在。
- 真正的断点：**先删 `dryrun/oomwoo-step`，GitHub 会连同 #21 一起关掉**（目标分支消失 = PR 自动关闭）。安全顺序：① 建 `feat/g2-pipeline` → ② 收 `3c740a8`（viewer 落进新支）→ ③ 把 #21 的 base 改到 `feat/g2-pipeline`（或直接关 #21，评论里指向新 PR）→ ④ 最后才删 `dryrun/oomwoo-step`。
- #17 自身 base=main，被吸收后关 #17、删分支不影响任何人（没有别的 PR 以它为 base）。
- 另外 **#21 现在对自己 base 已是 `CONFLICTING`**（它从 `d121b86` 分叉，base 支后来涨了 25 个提交），"保持原样等它自己合"本来走不通，改 base 是必须动作，不是可选项。

### 7. 最容易丢东西的一处

**`docs/参数溯源.csv`。** 名字一样、表头一样（9 列），但 #17 是**运行器的 108 行 xpath 台账**（`mass.chassis`、`geom.wheel_radius_m`、`susp.travel_limit_m`…；#15 的 110 行是同一套再加 `frictionloss` 2 行），trial/g4 是**试验侧 77 行**（`m_dry`、`com_x`…），两边 `param_id` **零重叠**。一句"台账以试验侧为准"就会静默丢掉 108 行，而 `run_cases.load_ledger_rows()`、`model_checks.MODEL_CONSTANTS`、viewer 都靠它取 `wheel_radius_m`/`susp_range_m`/`com_offset_B_m`——删掉的不是一份文档，是 runner 的取值来源。只能并集（77 + 108 = 185 行，回灌 `frictionloss` 则 187 行），不能选一侧。

同类的坑：#13 的 8 份 `docs/验证输出/` 与 #15 的 `docs/G2-运行与验证记录.md`，路径在 #17 不存在，cherry-pick 会以 modify/delete 冲突拦住**整个提交**，`--skip` 一次就整份没了；而这些是 Windows 实跑证据/契约 1.7.1 历史证据，丢了无法重跑。

### 8. 仍需拍板

1. **runner 主线选 #17 还是 #15**：建议 #17（契约 1.8.1 + 审阅返工 + oomwoo），但 #15 的 `frictionloss`（轮轴干摩擦，静置蠕滑红线的现实依据）与 12 mm 行程是否回灌要单独定——这是语义冲突，不能自动合。
2. **#13 的 `build_model.py` 路线是否保留**（与 #17 的 `${}` 运行时展开互斥）。
3. **#13 的 8 份验证输出**是契约 1.7.1 证据，入库需注明"不可用现行 runner 复现"。
4. **契约 1.8.1 归属**：随 pipeline 支带进，还是先在 `docs/prd` 落定再 rebase。
5. **#13 的 `docs/基准机型/oomwoo.md`** 与 #9/#12 主题重叠，按六支结构应归 `docs/prd` 的机型包，不宜留在 pipeline 支。

### 9. 复现命令

```sh
git merge-tree --write-tree --name-only origin/dryrun/oomwoo-step origin/feature/g2-baseline-runner
git worktree add /tmp/g2probe -b probe/g2-pipeline origin/dryrun/oomwoo-step
cd /tmp/g2probe
git cherry-pick -n 3c740a8 && git reset --hard        # viewer：干净
git cherry-pick a35c21e dbb2eda                       # #8：干净
git cherry-pick d167531                               # .gitattributes：干净
git cherry-pick -n bc93175                            # #15 契约：11 文件冲突
git checkout origin/feature/g2-baseline-runner -- "docs/G2-运行与验证记录.md"
git checkout origin/proto/baseline-cases -- .gitattributes "docs/判据/口径裁定记录.md" "docs/基准机型/oomwoo.md" docs/验证输出 params/hypothetical.json scripts/build_model.py scripts/verify_contact_readout.py
```
