> 本文件摘录自 Program-leader 的 Home 会话（2026-11-21 至 2026-11-22），只保留项目决策与事实；原对话仍在 Orca 历史里。

## G2 验收与返工

- 2026-11-22 仿真专家对 G2 不签，结论为"机理级未通过，需返工"，列三条阻断（B1 倾角单位、B2 斜向假通过、B3 时步依赖），修完只做一次针对性复审（依据：无依据，仅对话）。
- 2026-11-22 架构师结构验收结论为"结构能承接 G3，但这个提交不能"，全文见 `review/g2-structure` 的 `docs/评审/G2-结构验收-架构师.md`（依据：384b2a9）。
- 2026-11-22 架构师列必须改的第一条：台账迁移未同步到代码与 params（1a58707 改 `prototype.*` 前缀，但 `model_checks.py`、`run_cases.py`、`verify_structure.py`、`params/prototype.json` 仍用无前缀键），该提交没有自动化证据（依据：384b2a9 / 1a58707）。
- 2026-11-22 架构师指出倾角单位错：`judge.py:233-234` 从 `pitch_rad` 取值、`:249` 直接与 25 度阈值比、`:284-299` 又把弧度写进 `pitch_max_deg`，实测 `step_forward_20mm` 峰值 0.1214 rad = 7.0°、`summary.csv` 写 `pitch_max_deg=0.121354568`，倾覆判据实际要 25 rad 才响（依据：384b2a9）。
- 2026-11-22 仿真专家复算 B1：baseline summary `pitch_max_deg=0.12135`、timeseries `|pitch_rad|` 最大 0.12135 rad = 6.95°，`topple` 按 45 rad 比较永不触发；修复要求 judge 内换算并补"把某帧 pitch 置 50°必须触发"的负例（依据：无依据，仅对话）。
- 2026-11-22 仿真专家复算 B2：斜向 +30° 末帧仅 `wheel_L--floor`/`wheel_R--floor` 接触、`pos_z=-0.0045 m`、`pos_y=-1.223 m`、`yaw=-53.7°`、`t_climb=null` 却判 `passed=1`；修复要求加 `end_on_platform` 纳入 passed，并把该 case 改判 blocked 或 invalid（依据：无依据，仅对话）。
- 2026-11-22 仿真专家复算 B3：2 ms 通过、1 ms 通过但 `t_recover` 0.744→4.188 s（5.6×）、接触峰值 174.8→290.7 N（+66%）、0.5 ms timeout，破 G1 定的耗时差 <10%、峰值差 <20%、判定不变三条门槛，故本轮任何"通过"只能当机理演示（依据：无依据，仅对话）。
- 2026-11-22 仿真专家十项逐条结论：质量与质心/平地对照/接触顺序/法向力自洽/悬挂限位/数值卫生为部分签，限扭与失速为签，打滑判据与 μ 对齐/托底/时步依赖为不签（依据：无依据，仅对话）。
- 2026-11-22 仿真专家给出的最小返工清单含 7 条：judge 单位换算与 topple 负例、`end_on_platform`、打滑补 `abs(Ft)/Fn` 与 μ 对照、托底改间隙时程或声明 h ≤ 12.5 mm 上限、`run.json` 记 `d.warning.number`、报告结论区把 20 mm 与斜向"通过"改为机理级演示、时步三档双档同报复跑；复审只验 B1–B3 与第 5/6/10 项（依据：无依据，仅对话）。
- 2026-11-22 Program-leader 把两位专家清单合并为 10 条必须改并派 worker 在 `feat/g2-pipeline` 返工，验收门固定为 `verify_structure --run` 与 `check_param_ids --counts` 双双退出 0、加 topple 负例，复审只验 6 项不重跑全量（依据：无依据，仅对话）。
- 2026-11-22 排期后果：G3 参数扫描不能开跑，`item 5` 继续挂着；main 上这套 G2 代码处于未通过状态，任何对外引用都不能用（依据：item 5 / 无依据，仅对话）。

## 契约版本演进

- v1.8.2 把轮速符号从 `-qvel` 改成 `+qvel`，#15 声称按"前进为正"实现（依据：#15 / f712289）。
- 2026-11-22 仿真专家核实轮速 +qvel 实现通过：平地 `vx=+0.14905 m/s`、`wheel_L=+4.2742 rad/s`、R=0.035 → ωR=0.1496 同号吻合，实现直接取 `qvel` 无负号，`data_quality.torque_axis="wheel_end_-y_forward_positive"`，该条可结（依据：无依据，仅对话）。
- v1.8.3 摩擦口径为 pair 生效，真因是 3 分量写进 5 分量（依据：#27 @ ea544fa / `docs/评审/G2-验收证据/干跑-契约暴露的问题.md`）。
- 2026-11-22 架构师指出契约版本三处未升：`run_cases.py:32`、`judge.py:14`、`verify_structure.py:27` 均为 1.8.0 而文档为 1.8.3（S14）（依据：384b2a9）。

## 分支与 PR 收敛

- 2026-11-22 viewer 进 main：`3ee0512`（PR #34）；因 #21 的 base 是已淘汰的 `dryrun/oomwoo-step`、重开到 main 会 CONFLICTING，只抽 4 个文件（`scripts/view.py`、`view.sh`、`view.bat`、`docs/使用/启动Viewer看仿真.md`）到 `feat/g2-pipeline` 再合，实现基线仍是 main 的 #15（f712289）；三个脚本未亲自跑过，靠 #21 原 worker 的验证记录带进来（依据：PR #34 / 3ee0512）。
- 2026-11-22 证据按老板裁定恢复：`docs/state` 上 `be29ab3` 取回 8f76c4e 删掉的 13 份原始证据与 2 篇说明，目录与索引保留不动（依据：be29ab3）。
- 2026-11-22 PR #26 合入 main（`0ae1db2`），内容为 G2 收敛方案与 #17/#27/#28 报告摘录，证据文件与验收证据目录/README 索引两套并存（依据：PR #26 / 0ae1db2）。
- 2026-11-22 G2 收口：只留 #15（f712289）为实现，#17 #27 #28 #13 #21 的实现未合、报告已摘入 `docs/state`，`item 28` 已 Done（依据：item 28 / PR #34 / PR #26）。
- 2026-11-22 两次核对均判"没有分支要 rebase"——五支已全部收口，不存在落后于 main 的实现分支（依据：无依据，仅对话）。
- 2026-11-22 删了 `feat/mujoco-viewer`（#21 的头，4 个文件已进 main，删了不丢东西）；`docs/state` 是固定分支，保留未删（依据：无依据，仅对话）。
- 2026-11-22 四条已关但未擅自动的远端分支：`dryrun/oomwoo`(#27)、`dryrun/oomwoo-step`(#17)、`proto/baseline-cases`(#13)、`qa/g2-check`(#28)；删了只能靠 GitHub 的 Restore branch 找回（依据：无依据，仅对话）。
- PR 收敛计划第二批（`docs/项目状态/PR收敛计划.md`）覆盖 #8 #13 #15 #17 #21：只有 #21 的 base 是 `dryrun/oomwoo-step`，建分支不会断，先删该分支会连带关掉 #21；最容易丢的是 `docs/参数溯源.csv`（同名同表头、`param_id` 零重叠的 108 行台账）（依据：1770608 / `docs/项目状态/PR收敛计划.md`）。

## 机型包与文档

- 2026-11-22 `item 16` 缺 `machine=oomwoo` 的 MJCF 模板，机型包还差 1/3（依据：无依据，仅对话）。
- 2026-11-22 验收证据摘录落在 `docs/评审/G2-验收证据/`：#17 @ 76e57a0 → `全流程试跑-oomwoo.md`、#27 @ ea544fa → `干跑-契约暴露的问题.md`、#28 @ bffb193 → `结构抽查-16项.md`（12 过 / 5 未覆盖，S19 假通过已修）（依据：PR #26 / 8f76c4e）。
- 2026-11-22 未取三支分支的 `models/`、`cases/`、`scripts/`、`judge.py`，#21 不在本轮摘录范围；上一版摘录（`docs/干跑/`、`docs/试跑/`、`docs/评审/G2-结构抽查-2026-11-22.md`）已被 `docs/评审/G2-验收证据/` 取代（依据：PR #26 / 8f76c4e）。
- 2026-11-22 viewer 入口见 `docs/使用/启动Viewer看仿真.md`（依据：PR #34 / 3ee0512）。
- 未完成的三件（G2 返工 10 条、G2.5 壳体几何、G4 等机型数据）记在群内条目 #31 / #33（依据：item 31 / item 33）。

## 试验与判据

- 2026-11-22 架构师：S24 摩擦回读在 main 上不存在（全仓无 `S24` 命中，只在未合并的 #27），`run_cases.py:435-440` 把 4 分量补一位写成 pair 的 5 分量后不回读，正是 v1.8.3 点名的风险区（依据：384b2a9）。
- 2026-11-22 架构师：S19 / S20 是占位检查，`verify_structure.py:618` / `:627` 只判 `verified_tol` 非空 → FAIL，从不打开已存在的 `docs/不确定度预算.csv`（依据：384b2a9）。
- 2026-11-22 架构师：`check_param_ids.py --counts` 退出 0，共 302 行（own 40 / prototype 110 / oomwoo 152）；S16 五条断言真跑且外部扰动有效、S22 正反双向有效、S23 键唯一无占位、E 条 `--repeat 2` 逐位一致（比对用 `SUMMARY_METRIC_KEYS`，不含 `repeat`/`output_dir`）（依据：384b2a9）。
- 2026-11-22 架构师结论：M1–M5 都是小改、不动架构，修完以 `verify_structure.py --run` 与 `check_param_ids.py` 双双退出 0 作为 G3 开工条件即可（依据：384b2a9）。
- 2026-11-22 仿真专家：静置蠕滑基线已执行、红线未触发（baseline `drift_m=1.99e-10 m`、`residual_speed=2.89e-11 m/s`、`redline=false`、`tiers` 仅 `base`），记录于 `run.json.cases[].repeats[].creep`，该条可结；但静置只在平地做，建议复审补"轮顶在台阶棱边上的静置"（依据：无依据，仅对话）。
- 2026-11-22 仿真专家：托底只有接触对 active 判定，`chassis_min_z_m` 全程约 −0.161 m 不能当间隙用，12.5 mm 前沿几何未建模，h>12.5 mm（20/30/40）全在模型未覆盖区，20 mm 的"无托底"不能算结论（依据：无依据，仅对话）。
- 2026-11-22 仿真专家确认 condim=3 没有引用 `res[3..5]`：`data_quality` 写明 `condim_quoted=3`、`rolling_resistance="not_modelled(condim=3)"`，滚阻用关节 `frictionloss=0.002 N·m`【待标定】近似，交付未拿扭转/滚阻力矩当物理量，该条可结（依据：无依据，仅对话）。
- 2026-11-22 架构师在 macOS 临时 venv（mujoco 4.0.1 / numpy 2.5.5）跑的结构结论与平台无关，但 `summary.csv` 里的数值结论没有在 Windows 复核，不得引用（依据：384b2a9）。

## 工具与路由问题

- 2026-11-22 `item 4`、`item 6` 被 cancel，迁移到群内主条目 #31 / #33（老板要求所有任务与审批集中到 `mujoco_` 群），后续更新只在 #31 / #33（依据：item 4 / item 6 / item 31 / item 33）。
- 2026-11-22 老板下令"所有工作停止"：G2 返工 worker（`ctx_dda645901f77`，`feat/g2-pipeline`）state=stopped，每 15 分钟的看板巡检已移除，其余 5 个 worker 早已 succeeded（依据：无依据，仅对话）。
- 2026-11-22 没停掉的：`g25-lip` 工作区 G2.5 worker 仍在跑（跨 Run 被拒 `consumer_fenced`）；两条事件自动化（PR 合并后、新 PR 到达）还开着，Orca 没有禁用开关只能删，工作停了就不会有 PR，故留着（依据：无依据，仅对话）。
- 2026-11-22 恢复方式：重建巡检（15 分钟、跑在群里）、重派 G2 返工 10 条，原配置与 prompt 留着可原样恢复（依据：无依据，仅对话）。
- 2026-11-22 自检 #38：群名下条目的答复邮件能到 Home（event e312），但只验了一条一次，群会话是否同时收到看不到（依据：item 38 / e312）。
- 2026-11-22 自检 #39：唤醒仍落 Home（e319），"item 答复直接叫醒群会话"未生效；但 Home → 群发送守卫已放行，往 `mujoco_` 群发 status 成功返回 `msg_5233442fcc4b`；两条通路不对称——能发进群，群会话不会被 item 邮件叫醒（依据：item 39 / e319 / msg_5233442fcc4b）。
- 2026-11-22 简单报错处理更正：发送守卫报错 `Group bot sessions accept peer requests only from current members of their own group` 已在本地补丁放行（Orca 1.4.269）；`This mail is outside the active group request` 是收信守卫、从代码推的静默拒收（10 封 item 邮件 `delivered_at` 为空），属推断而非实测报错；补丁状态为发送守卫已放行、地址与过滤两项试验已回退（依据：无依据，仅对话）。
- 2026-11-22 硬规则（老板第三次强调）：项目交互只在 `mujoco_` 群、Home 只做转达，开工先自查条目（`orca bot item list --status needs-you` / `--status in-progress`）；原因：Orca 1.4.269 群成员会话收信校验邮件属于当前群请求，item 答复不属于任何群请求，故条目答复只叫醒 Home；可靠做法只有开工自查加群里每 15 分钟巡检兜底（依据：无依据，仅对话）。
- 2026-11-22 Program-leader 反馈：上述两条规则已在 SOUL 里不需要重写，SOUL 只有老板本人授权修改，口头照做当前阶段效果一样；并校对项目里把发送守卫与收信守卫并成一条的写法不当，两者报错文案不同、结论相同但原因归属不同（依据：SOUL.md / 无依据，仅对话）。
- 2026-11-22 更正：群会话 id 要各自查（`orca bot chats --bot "<你的名字>"`，取标题为 "You are responding in the shared group…" 的那一行 id），不能照抄 Program-leader 的 0883bf02…（依据：无依据，仅对话）。
- 2026-11-22 看板巡检规则：只在本群 `mujoco_` 说话，按顺序查"老板已答但没执行"、查空转（`orca worktree ps`）、都没有则 NO_REPLY；硬规矩为不合并 PR（除非老板在条目上明确答合并）、不重复派工、派不出去如实说（依据：无依据，仅对话）。

## 环境与资源

- 2026-11-22 main 停在 `0ae1db2`（G2 未通过的那一版），别对外引用，报告里 20 mm 与斜向的"通过"要改成"机理级演示"（依据：0ae1db2 / 无依据，仅对话）。
- 2026-11-22 本地 `mujoco_` 工作副本 HEAD 停在 `0a61078`，比 origin/main 落后几个合并（用 `gh` 合的、没 pull），在该目录直接跑脚本会跑到旧代码（依据：0a61078 / 无依据，仅对话）。
- 2026-11-22 `docs/state`、`feat/g2-pipeline`、`trial/g4` 等固定分支都在，没有未推送的东西（依据：无依据，仅对话）。

## 已失效的结论

- 把 pair 摩擦当"不生效"：后来按 v1.8.3 口径改为 pair 生效，真因是 3 分量写进 5 分量（依据：#27 @ ea544fa）。
- 把 #17 当作要合并的 PR：后来 G2 收口只留 #15 为实现，#17 实现未合、报告已摘入 `docs/state`（依据：item 28）。
- "27 项通过"的说法：后来架构师指出这个提交没有自动化证据，"27 项通过"是另一份代码跑出来的（依据：384b2a9 / 无依据，仅对话）。
- 把 #21 直接重开到 main 合并：后来发现其 base 是已淘汰的 `dryrun/oomwoo-step`、重开到 main 会 CONFLICTING，改为只抽 4 个文件走 PR #34（依据：PR #34 / 3ee0512）。
- 倾覆判据"存在且有效"：后来发现 judge 把弧度当度比较，`topple` 实际永不触发（依据：384b2a9 / 无依据，仅对话）。
- 斜向 +30° 判"通过"：后来发现末帧只接触地面、横移 1.2 m、yaw −53.7°，是假通过（依据：无依据，仅对话）。
- 契约 v1.8.2 的轮速符号 −qvel：后来改为 +qvel，且核实 +qvel 实现正确、未按字面取负（依据：f712289 / 无依据，仅对话）。
- `item 4` / `item 6` 作为项目条目继续推进：后来被 cancel，迁移到群内主条目 #31 / #33（依据：item 4 / item 6）。
- "item 答复能叫醒群会话"：后来两次自检（#38 / #39）证明答复只落 Home，群会话不会被唤醒（依据：item 38 / item 39）。
