# PR 收敛计划

> 数据口径：2026-11-22 用 `gh pr list` / `gh pr view --json files` 读取 `keylliucong/mujoco-robot-vacuum` 的全部 open PR。任务给出的 17 个（#2–#18）之外，分析期间新开了 **#19**，当前共 **18 个**；#19 零文件冲突，不改变合并顺序。`base` 与文件重叠均来自 GitHub 实际返回，未读到的信息不猜；GitHub 的变更类型字段是 `changeType`（`ADDED`/`MODIFIED`/`REMOVED`/`RENAMED`），不是 `status`。注意 PR #5 的不确定度预算 stub 已在 `bdb8db0` 删除，下表为删除后的最新状态。本计划只做分析，不合并任何 PR。

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
