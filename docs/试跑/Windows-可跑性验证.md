# Windows 可跑性验证（G2 基线，rebase 后，2026-11-22）

- 任务：在台账迁到三段键（`#44`，main `0c8b5bf`）之后，把本分支 rebase 到新基，并在 Windows 上重跑 G2 基线证据。
- 分支：`feat/g2-pipeline-winverify`，PR [#36](https://github.com/keylliucong/mujoco-robot-vacuum/pull/36)（base `main`，**未合并**）。
- 测试提交：`8f41d95924f8a85b7303d60ea76e0644e08809a4`（下文简称 `8f41d95`），父提交 `0c8b5bf`（main）。
  本文与证据在紧随其后的文档提交里；该提交与 `8f41d95` 的差异只在 `docs/试跑/` 下，
  `git diff 8f41d95 HEAD -- cases params models scripts judge.py machine_packs` 为空，故数值证据对 HEAD 同样成立。
- 执行位置：Windows 主机 `DESKTOP-RGG6DMC`，项目目录 `E:\mujoco-robot-vacuum`。
- 证据目录：`docs/试跑/证据-windows-8f41d95/`（本目录替换了 rebase 前 `5380699` 的旧证据；旧提交已不在本分支历史中）。

## 0. 结论

**能在 Windows 上独立复跑，判定与 Mac 一致，跨平台不逐位一致。** 三段键台账在两边都直接可用：`check_param_ids --counts`
退出码 0（309 行：own=40、prototype=117、oomwoo=152），`verify_structure.py --run` 退出码 0（32 项、0 失、S19/S20 按规则 SKIP），
三条基线工况 `--repeat 2` 全部跑通，批内 r1/r2 与两次独立运行（A/B）的 `timeseries.csv` **逐位相同**。
rebase 时把旧的“机型前缀兼容补丁”整段丢弃：main 的 `load_ledger_rows(machine, config_id)` 已原生按三段键取行，补丁不再需要。

## 1. rebase 记录

| 项 | 值 |
| --- | --- |
| 旧基 | `5849d0b`（基于 `0ae1db2`，含前缀兼容补丁 `5380699`） |
| 新基 | `0c8b5bf`（main，`#44` 三段键台账 v1.8.4） |
| rebase 后代码基 | `8f41d95`（首个提交；本文与证据在其后的文档提交，差异只在 `docs/试跑/`） |
| 推送方式 | `git push --force-with-lease=feat/g2-pipeline-winverify:5849d0b`（rebuild 历史，非强推覆盖他人提交） |

冲突处理（按任务要求一律取 main 侧）：

- `scripts/run_cases.py`、`scripts/view.py`：取 main。main 已实现 `load_ledger_rows(machine, config_id)` →
  `model_checks.load_ledger(LEDGER_PATH, machine=..., config_id=...)`，旧的裸 id 别名补丁随之作废，**未保留**。
- `docs/参数溯源.csv`、`docs/不确定度预算.csv`、`params/*.json`：本分支未改，rebase 后与 main 完全一致。
- 工况/脚本中的两段键字符串：本分支没有需要改写的两段键；`cases/*.json` 不含台账键字面量，
  键由 `params/<config_id>.json` + 台账匹配生成，rebase 后运行输出的 `run.json.parameter_set.missing` 与 `params[].id`
  均为三段键（如 `prototype.proto_v1.com.chassis.z`、`oomwoo.oomwoo_public_v1.F0`）。

## 2. Windows 检出与环境

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git checkout 8f41d95
git rev-parse HEAD
git status --porcelain
```

结果：`HEAD=8f41d95924f8a85b7303d60ea76e0644e08809a4`。工作区原有未跟踪文件 `g2r2-fric.py` 临时移到
`.tools\hold\`（跑完未动回原处以外的任何文件；该文件不属于本次提交），运行期间 `git status --porcelain` 为空，
三次 `run.json` 均为 `git.dirty=false`、`git.branch=HEAD`（detached）。

| 项 | Windows | Mac（对照） |
| --- | --- | --- |
| 主机 | `DESKTOP-RGG6DMC` | `liucongdeMac-mini.local` |
| OS | Windows 11 `10.0.26200`（`Windows-11-10.0.26200-SP0`） | macOS 27.2.1 arm64 |
| Python | `3.13.1`（`E:\mujoco-robot-vacuum\.venv\Scripts\python.exe`） | `3.13.18`（`dryrun-oomwoo/.venv/bin/python`） |
| MuJoCo | `4.0.1` | `4.0.1` |
| NumPy | `2.5.5` | `2.5.5` |
| 数值设置 | `timestep_s=0.002`、`integrator=implicitfast`、`solver=Newton`、`cone=pyramidal`、`iterations=100` | 同左 |

两端 `run.json` 的 `numerics.effective` 完全相同（`timestep_s=0.002, integrator=3, solver=2, cone=0, iterations=100`）。

## 3. 命令原文与输出路径

Windows（PowerShell，`E:\mujoco-robot-vacuum`，`.venv`）：

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'

# 台账键检查（三段键）
.venv\Scripts\python.exe scripts\check_param_ids.py --counts
# 结构自查（含集成抽查，会跑仿真）
.venv\Scripts\python.exe scripts\verify_structure.py --run

# 基线批次 A（B 批次同命令，只把 --out 的 A_ 换成 B_）
.venv\Scripts\python.exe scripts\run_cases.py --config cases\baseline.json --out outputs\win_rebase_8f41d95\A_baseline --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\flat.json --out outputs\win_rebase_8f41d95\A_flat --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\step_forward_20mm_low_torque.json --out outputs\win_rebase_8f41d95\A_step_lowtorque --repeat 2

# 判定模块（无 CLI，退出码 0、无输出）
.venv\Scripts\python.exe judge.py
```

Mac 对照（同提交、同参数，`--out outputs/mac_rebase_8f41d95/<case>`）。

输出路径（Windows，全部在 `E:\mujoco-robot-vacuum\outputs\`）：

| 内容 | 路径 |
| --- | --- |
| A 批次 | `win_rebase_8f41d95\A_baseline`、`A_flat`、`A_step_lowtorque` |
| B 批次（独立第二次） | `win_rebase_8f41d95\B_baseline`、`B_flat`、`B_step_lowtorque` |
| `check_param_ids` 原文 | `outputs\win_rebase_check_param_ids.txt`、`win_rebase_8f41d95\check_param_ids_utf8.txt` |
| `verify_structure --run` 原文 | `win_rebase_8f41d95\verify_structure_utf8.txt` |
| 批次 stdout | `win_rebase_8f41d95\A_*_stdout.log`、`B_*_stdout.log` |

`judge.py` 只是判定模块、没有 CLI：直接运行退出码 `0`、无输出（`JUDGE_EXIT=0`）。实际判定入口是
`scripts/run_cases.py` 内部调用的 `judge.judge_case(...)`，结果写入 `run.json` / `summary.csv`。

### 3.1 交付的可入库证据（`docs/试跑/证据-windows-8f41d95/`）

- `check_param_ids.txt`（UTF-8，1 行）、`verify_structure.txt`（UTF-8，34 行）、`env.txt`
- `Windows_baseline_run.json`、`Windows_flat_run.json`、`Windows_step_lowtorque_run.json`
- `Windows_baseline_summary.csv`、`Windows_flat_summary.csv`、`Windows_step_lowtorque_summary.csv`
- `A_baseline_stdout.log`、`A_flat_stdout.log`、`A_step_lowtorque_stdout.log`（批次控制台原文）
- `tsdiff-flat.csv`、`tsdiff-baseline_step.csv`、`tsdiff-lowtorque_step.csv`（逐列跨平台差值）

完整 `timeseries.csv`（1.3–2.3 MB/份）按项目规则不入库，保留在上表 Windows 路径，按 sha256 核对。

## 4. 键检查与结构自查

| 检查 | 命令 | 退出码 | 输出 |
| --- | --- | --- | --- |
| 台账三段键 | `scripts\check_param_ids.py --counts` | `0` | `OK docs\参数溯源.csv: 309 行（own=40, prototype=117, oomwoo=152）`，1 行 |
| 结构自查（含集成） | `scripts\verify_structure.py --run` | `0` | `32 项检查，0 项失败`，34 行 |

`verify_structure --run` 中 `S19`、`S20` 为规则内 SKIP（预算表 prototype 机型覆盖 0 行；无实测↔仿真比对行），
其余 32 项 PASS，含“抽查5: `--repeat 2` 两次 timeseries 与判定逐位一致”“抽查9(topple): 60 mm 实跑
pitch_max=89.84°、passed=False primary=topple”。
rebase 前该脚本在 Windows/Mac 上都在 S16 报 `台账缺行：mass.assembly` 不可跑，本次已随 main 的三段键改造解除。

## 5. 判定结果（Windows，`8f41d95`）

| 工况 | status | passed | primary | flags | advance_m | t_trigger_s | t_climb_s | t_recover_s | pitch_max / roll_max (deg) | 轮端扭矩 max | contact_normal_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline.json`（0.8 N·m 正向 20 mm） | ok | 1 | — | torque_limit;slip | 1.136148060 | 4.788 | 0.922 | 0.744 | 6.953104571 / 3.952075915 | 0.8000 N·m | 174.778019156 N |
| `flat.json`（平地对照） | ok | 1 | — | slip | 1.117132953 | 0.002 | — | 0.812 | 3.185926892 / 0.000000000 | 0.0918 N·m | 13.923618423 N |
| `step_forward_20mm_low_torque.json`（限扭 20 mm） | ok | 0 | retreat | retreat;cross_fail;stall;torque_limit;slip | −0.000011318 | 4.790 | — | — | 2.155978705 / 0.022922494 | 0.0500 N·m | 22.008084473 N |

限扭算例与配置的 `regression_expect={passed:false, failure_primary:retreat}` 一致（`run.json.cases[0].regression.matched=true`）。
与 rebase 前的旧报告相比，限扭工况的 `flags` 多了 `cross_fail`：这是 `judge.py` 从 1.9.0 起新增的失败模式，
不是本次运行引入的变化。静置蠕滑三工况均 `drift=0.0000 mm`、`residual=0.0000 mm/s`、`redline=False`，仅 base tier、无降档。

`run.json` 自证（三批次一致）：`contract_version=1.9.0`、`git.commit=8f41d95…`、`git.dirty=false`、
`model.sha256=153b76975830102fbb19e2bf5f810ece9093aa4ae511d586061f65ce68591d01`、
`rendered_sha256=591793f9f648e3de8dd2d361893f4dc1a626dc061bcb7f6f92d9124b8746f8f9`、
`scenario_xml_sha256`（批次级）：baseline `e8fd1c69…`、flat `ecace89f…`、low_torque `17ea5ad1…`，与 Mac 完全相同。
`repeat.consistent=true`、`key_metrics_tol=0.0`、`conclusion_level=mechanism`（`z_cg` 缺失）。

## 6. 两次一致性

| 比较 | flat | baseline（20 mm） | 限扭 20 mm |
| --- | --- | --- | --- |
| 批内 r1 vs r2（`timeseries.csv` sha256） | 相同 | 相同 | 相同 |
| A 批次 vs B 批次（独立进程再跑一遍） | 相同 | 相同 | 相同 |
| 两次的 `run.json.git.dirty` | `false` | `false` | `false` |

Windows `timeseries.csv` sha256（A/B 相同，r1/r2 相同）：

| 批次 | r1/r2 sha256 | 大小 |
| --- | --- | --- |
| `A_baseline` | `f5f938bd51062d5e5c94a0ae0cf0c9d13822d6ce9db99a81d3d3b9d471169c8d` | 2 136 152 B |
| `A_flat` | `de91c7e4fbd6f483056ad2b175a61bdcc96c3f57379029b589dac025fefa4e55` | 1 277 893 B |
| `A_step_lowtorque` | `72e46b7388aa5ac70abd17915717e941a3bf83d7b3375d6cb56301d19ce402a4` | 2 336 411 B |

`run.json` 的 sha256 在 A/B 之间不同（`57e62905…` vs `5be4090d…` 等），差异只来自 `batch_id` 与输出目录路径，
与数值无关；同一批次内 r1/r2 的时程逐位相同。Mac 侧同提交亦 `repeat.consistent=true`、r1/r2 sha256 相同。

## 7. 与 Mac 的跨平台差值

同提交 `8f41d95`、同 `--repeat 2`、同数值设置。**不逐位一致是预期**，逐列明细见 `tsdiff-*.csv`。

### 7.1 判定层

| 项 | Windows | Mac | 结论 |
| --- | --- | --- | --- |
| baseline passed / primary / flags | 1 / — / torque_limit;slip | 同 | 一致 |
| flat passed / primary / flags | 1 / — / slip | 同 | 一致 |
| 限扭 passed / primary / flags | 0 / retreat / retreat;cross_fail;stall;torque_limit;slip | 同 | 一致 |
| `summary.csv` 判定列 | — | — | 全部一致（除 `slip_max_L/R`、`susp_travel_max_L/R` 左右互换与接触力末位，见下） |

### 7.2 summary 数值

- flat：27 个数值/判定列（除 `output_dir`/`batch_id`）**全部逐列相同**（含 `advance_m`、`t_recover_s`、扭矩、悬挂、`contact_normal_max_n`）。
- baseline（20 mm）：27 列中 25 列相同。差异仅 `slip_max_R`（Win `7.324650712` / Mac `7.324650721`，Δ=9e-9）与
  `contact_normal_max_n`（Win `174.778019156` / Mac `174.778019167`，Δ=1.1e-8）。
- 限扭 20 mm：27 列中 22 列相同，其余 5 列是**镜像互换与末位差**，不是量级失控：
  `slip_max_L/R` Win `0.622210526 / 0.637269360`，Mac `0.637269360 / 0.622210526`（2.36%）；
  `susp_travel_max_L/R` 4.562930 / 4.567495 mm 对调；`contact_normal_max_n` Win `22.008084473` / Mac `22.008084477`（Δ=4e-9）。

### 7.3 时程层（逐列）

| 工况 | 列数 | 逐位相同 | 有差列的最大绝对差 |
| --- | --- | --- | --- |
| flat | 33 | 20 | 4.7e-08 N（轮-地法向力），轮速 2e-09 rad/s |
| baseline 20 mm | 45 | 17 | 2.3e-07 rad/s（轮速），接触力 6.5e-08 N |
| 限扭 20 mm | 45 | 18 | 11.8 N（台阶法向力，第 2396 行起的左右先后互换） |

flat 的 13 个“有差”列里有 7 列（`pos_y_m`、`quat_x/z`、`roll_rad`、`yaw_rad`、`vel_y_mps`、`vel_z_mps`）
最大绝对差为 **0**，差别只是文本里的 `-0.000000000` 与 `0.000000000`（符号零），数值等价。
baseline 20 mm 的分歧起点是第 1714 行（`vel_z_mps`）与第 1795 行（轮速）的 1e-9 级末位差，到第 2395 行台阶接触
仍只有 6e-08 N 级差，**没有任何左右镜像翻转**，判定量与整机运动量（`advance_m`、`pos_x_m`、`pitch_rad`）在 9 位小数上一致。
限扭工况从第 1380 行起接触力末位差积累，到第 ~2404 行左右轮谁先压上台阶/地面的接触计数互换，
随后左右对称量整体反号——这是对称工况把浮点末位差放大成镜像分支，两侧各自逐位可复现，但不能要求跨平台逐位一致。

## 8. 复跑步骤（复核用）

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git checkout 8f41d95
.venv\Scripts\python.exe scripts\check_param_ids.py --counts
.venv\Scripts\python.exe scripts\verify_structure.py --run
.venv\Scripts\python.exe scripts\run_cases.py --config cases\baseline.json --out outputs\recheck_baseline --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\flat.json --out outputs\recheck_flat --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\step_forward_20mm_low_torque.json --out outputs\recheck_step --repeat 2
```

`--out` 目录必须不存在（S12），重复跑请换目录名。核对 `run.json.git.commit`、`git.dirty=false`、
`scenario_xml_sha256`、`repeat.consistent` 与本报告一致；`timeseries.csv` 的 sha256 应与第 6 节相同（逐位复现）。

## 9. 未覆盖与卡点

1. **只跑三条工况**：baseline、flat、限扭 20 mm。斜向 ±30°、60 mm topple、baseline 0.8 N·m 之外的参数档未在 Windows 重跑；
   topple 60 mm 仅在 `verify_structure --run` 的抽查9 里跑过一次。
2. **`conclusion_level` 仍是 `mechanism`**：`prototype.proto_v1.com.chassis.z` 缺失（`params: ... missing=[...]`），
   本报告只证明“可复跑 + 判定一致”，不改变参数等级或物理结论。
3. **Windows 工作区的 `g2r2-fric.py`**：属于既有未跟踪文件，运行期间临时移到 `.tools\hold\` 以取得 `dirty=false`，
   未纳入版本管理；仓库若长期保留建议清理或加忽略规则。
4. **Python 小版本不同**（Win 3.13.1 / Mac 3.13.18）：这是跨平台末位差的一个可能来源，本次未做同小版本对照。
5. **PR #36 的原始目的（机型前缀兼容补丁）已被 main 的 `#44` 取代**：本 PR 现在只承载“rebase 后的 Windows 复跑证据”，
   合并时不需要任何 `scripts/*` 改动。
