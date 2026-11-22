# Windows 可跑性验证（G2 基线，2026-11-22）

- 任务：证明 G2 基线（#15，main `0ae1db2`）能在 Windows 上独立复跑，并留下可复核记录。
- 分支：`feat/g2-pipeline-winverify`（基于 `origin/main` `0ae1db2`，PR #36；**未合并**）。
- 测试提交：`53806998a1d12bfef22f0df77213b396fa6fede2`（下文简称 `5380699`）。
- 执行位置：Windows 主机 `DESKTOP-RGG6DMC`，项目目录 `E:\mujoco-robot-vacuum`。
- 证据目录：`docs/试跑/证据-windows/`。

## 0. 结论

**能在 Windows 上复跑，但有前提。** 直接检出 main `0ae1db2` 在 Windows（以及 Mac）上跑不起来：`scripts/run_cases.py`
按裸 `param_id` 取台账，而台账已在 v1.8.1 迁移为 `<machine>.<id>`，启动即报
`CONTRACT ERROR: 台账缺行：geom.wheel_radius_m`。补一个只读的机型前缀兼容层（提交 `5380699`，不改契约、不改台账）后，
Windows 在 Python 3.13.1 / MuJoCo 4.0.1 上跑通两条基线工况，判定与 Mac 同提交结果一致。

## 1. 分支、提交与推送状态

| 项 | 值 |
| --- | --- |
| main 基线 | `0ae1db2d0e93833a6b1cb7c3c49b51efd8d063ee`（本次验证时 `origin/main` 最新） |
| 验证提交 | `53806998a1d12bfef22f0df77213b396fa6fede2` |
| 分支 | `feat/g2-pipeline-winverify`（已推送） |
| PR | https://github.com/keylliucong/mujoco-robot-vacuum/pull/36 （open，未合并） |
| 冻结约束 | 契约未改；`docs/参数溯源.csv` 未改；Windows 只检出已推送提交 |

`feat/g2-pipeline` 远端仍停在 `dc7d14c`（比 main 少 20 个文档文件，且 `docs/项目状态/PR收敛计划.md` 为旧版）。
为不覆盖他人分支、不做强推，本次修复与新证据放在从 `origin/main` 拉出的 `feat/g2-pipeline-winverify` 上。

### 1.1 Windows 上的检出与工作区

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git checkout 5380699
git rev-parse HEAD
git status --porcelain
```

结果：`HEAD=53806998a1d12bfef22f0df77213b396fa6fede2`，`git status --porcelain` 仅有未跟踪的
`?? build/`（PR #13 遗留的 `build/models/oomwoo_public_v1.*`，非本次源码改动）。

为让 `run.json.git.dirty` 准确为 `false`，运行时把该目录临时移到 `.tools\build-offline-2026-11-22`，
跑完原样移回。两次运行记录均为 `dirty=false`；Python、MuJoCo 与项目源码均来自 `5380699`。

## 2. 环境

| 项 | Windows | Mac（对照） |
| --- | --- | --- |
| 主机 | `DESKTOP-RGG6DMC` | `liucongdeMac-mini.local` |
| OS | Windows 11 `10.0.26200`（`Windows-11-10.0.26200-SP0`） | macOS 27.2.1 arm64 |
| Python | `3.13.1`（`E:\mujoco-robot-vacuum\.venv\Scripts\python.exe`） | `3.13.18`（`/Users/liucong/orca/workspaces/mujoco_/dryrun-oomwoo/.venv/bin/python`） |
| MuJoCo | `4.0.1` | `4.0.1` |
| NumPy | `2.5.5` | `2.5.5` |

原始记录：`docs/试跑/证据-windows/env.txt`。数值设置两端一致：`timestep_s=0.002`、`integrator=implicitfast`、
`solver=Newton`、`cone=pyramidal`、`iterations=100`。

## 3. 首次失败（main `0ae1db2`，Windows）

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git checkout 0ae1db2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\flat.json --out outputs\win_verify_0ae1db2_flat --repeat 2
```

输出（原文）：

```text
CONTRACT ERROR: 台账缺行：geom.wheel_radius_m
```

原因：`scripts/run_cases.py` 的 `load_ledger_rows()` 与 `model_checks` 仍按裸 id（`geom.wheel_radius_m`、
`susp.travel_limit_m`、`mass.assembly` 等）取行；台账在 `1a58707`（v1.8.1）已改为
`prototype.geom.wheel_radius_m`、`prototype.mass.assembly` 等机型前缀。Mac 上同提交同样报错。

### 3.1 最小修复（`5380699`）

`scripts/run_cases.py`：按模型头 `machine=prototype` 为当前机型补裸 id 别名（只对当前机型生效，其他机型行不参与），
结论等级统计仍用原始行，避免别名重复计数。`scripts/view.py` 同步传入 `machine`。
台账文件与契约均未修改。修复提交：`53806998a1d12bfef22f0df77213b396fa6fede2`。

## 4. 运行命令（原文）

`main` 的入口是**单 case** 参数（`--config`），没有任务描述里的 `--cases a b` 形式，因此拆成两条批次命令。

Windows（PowerShell，`E:\mujoco-robot-vacuum`，`.venv`）：

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git checkout 5380699

.venv\Scripts\python.exe scripts\run_cases.py --config cases\flat.json --out outputs\win_verify_5380699_flat --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\step_forward_20mm_low_torque.json --out outputs\win_verify_5380699_step --repeat 2

.venv\Scripts\python.exe judge.py
```

Mac 对照（同一提交、同一命令参数）：

```bash
cd /Users/liucong/orca/workspaces/mujoco_/win-verify
/Users/liucong/orca/workspaces/mujoco_/dryrun-oomwoo/.venv/bin/python scripts/run_cases.py --config cases/flat.json --out outputs/mac_verify_5380699_flat --repeat 2
/Users/liucong/orca/workspaces/mujoco_/dryrun-oomwoo/.venv/bin/python scripts/run_cases.py --config cases/step_forward_20mm_low_torque.json --out outputs/mac_verify_5380699_step --repeat 2
```

### 4.1 关于 `python judge.py`

`judge.py` 只是判定模块，**没有 CLI**：直接运行退出码 0、无输出（记录为 `judge_exit=0`）。
仓库实际判定入口在 `scripts/run_cases.py` 内调用 `judge.judge_case(...)`，结果写入 `run.json` / `summary.csv`，
且 `judge.py` 不 import MuJoCo（S04/S09）。

为在 Windows 上独立验证判定输入可用，另跑了一次只读烟测（原文）：

```powershell
.venv\Scripts\python.exe -c "import csv,glob,judge; [print(p, len(list(csv.DictReader(open(p,newline='',encoding='utf-8')))), 'columns_complete=', judge.timeseries_columns_complete({k:[r[k] for r in csv.DictReader(open(p,newline='',encoding='utf-8'))] for k in csv.DictReader(open(p,newline='',encoding='utf-8')).fieldnames})) for p in sorted(glob.glob('outputs/win_verify_5380699_*/**/timeseries.csv', recursive=True))]"
```

结果：4 个 `timeseries.csv`（flat 4001 行 ×2，step 6395 行 ×2）全部 `columns_complete=True`。

## 5. 输出位置与证据

Windows 输出（全部在 `E:\mujoco-robot-vacuum\outputs\`）：

| 批次 | 文件 | 大小 | sha256 |
| --- | --- | --- | --- |
| `win_verify_5380699_flat` | `run.json` | 55 814 B | `813577220dd8334d3c014de585267e45fba92415b556dd3253ea1e93a5d2f6e3` |
| | `summary.csv` | 1 164 B | `bb47895f784416f748c3d6096e8edacd8ad846e33b969ae04841f27c26e2320d` |
| | `flat_forward_r1/timeseries.csv` | 1 281 894 B | `b0f413f232ba592905aee3e40590634df1eea96e2891f39134a47361f55fcefb` |
| | `flat_forward_r2/timeseries.csv` | 1 281 894 B | `b0f413f232ba592905aee3e40590634df1eea96e2891f39134a47361f55fcefb` |
| `win_verify_5380699_step` | `run.json` | 57 791 B | `30dfb64d63b09bbb8612507308bb63d5488159cc329f586045a2cfc822262762` |
| | `summary.csv` | 1 270 B | `587d47c39b54c5a1e8e448e7f08abafeefc4b37113bd096b1c8344951b750096` |
| | `step_forward_20mm_low_torque_r1/timeseries.csv` | 2 342 806 B | `95133487697bb27eb974c52dafe453921012c931f9b9f5c19b5cb1a121c65845` |
| | `step_forward_20mm_low_torque_r2/timeseries.csv` | 2 342 806 B | `95133487697bb27eb974c52dafe453921012c931f9b9f5c19b5cb1a121c65845` |

`run.json` 自证：`git.commit=5380699…`、`git.dirty=false`、`git.branch=HEAD`（detached）、
`model.sha256=153b76975830102fbb19e2bf5f810ece9093aa4ae511d586061f65ce68591d01`、
`rendered_sha256=591793f9…`、`scenario_xml_sha256` 与 Mac 完全一致（flat `468ebe1a…`，step `b6eea901…`）。
同一批次内 `repeat.consistent=true`、`key_metrics_tol=0.0`，r1/r2 的 `timeseries.csv` sha256 相同。

可入库文本证据（已复制进仓库）：

- `docs/试跑/证据-windows/Windows_flat_run.json`、`Windows_flat_summary.csv`、`Windows_flat_stdout.log`
- `docs/试跑/证据-windows/Windows_step_run.json`、`Windows_step_summary.csv`、`Windows_step_stdout.log`
- `docs/试跑/证据-windows/summary-diff-vs-mac.csv`（逐列差值）
- `docs/试跑/证据-windows/timeseries-diff-vs-mac.csv`（逐列最大差与首个分歧行）
- `docs/试跑/证据-windows/env.txt`

完整 `timeseries.csv`（每份 1.2–2.3 MB）按项目规则不入库，保留在上表 Windows 路径，按 sha256 核对。

## 6. 判定结果（Windows，`5380699`）

| 工况 | status | passed | primary | flags | advance_m | t_trigger_s | t_recover_s | pitch_max/roll_max | 轮端扭矩 max | contact_normal_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 平地对照 `flat.json` | ok | 1 | — | slip | 1.117132953 | 0.002 | 0.812 | 0.0556° / 0.0000° | 0.0918 N·m | 13.923618423 N |
| 正向 20 mm 限扭 `step_forward_20mm_low_torque.json` | ok | 0 | retreat | retreat;stall;torque_limit;slip;timeout | −0.000011318 | 4.790 | — | 0.0376° / 0.0004° | 0.0500 N·m | 22.008084473 N |

限扭算例的 `regression_expect={passed:false, failure_primary:retreat}` 与实际一致：
`run.json.cases[0].regression.matched=true`。静置蠕滑基线两工况均未触发红线（漂移/残余速度在记录中为
0.0000，仅 base tier，无降档）。

## 7. 与 Mac 的跨平台差值

同一提交 `5380699`、同样 `--repeat 2`、同样数值设置。**允许不逐位一致**，差值如下。

### 7.1 判定层

| 项 | Windows | Mac | 是否一致 |
| --- | --- | --- | --- |
| flat passed / primary / flags | 1 / — / slip | 1 / — / slip | 一致 |
| step passed / primary / flags | 0 / retreat / retreat;stall;torque_limit;slip;timeout | 0 / retreat / 同名 flags | 一致 |
| step `regression.matched` | true | true | 一致 |
| flat `summary.csv` | 除 `output_dir` 外逐列相同 | — | 一致 |
| 重复性（r1 vs r2） | 各自逐位一致 | 各自逐位一致 | 一致 |

### 7.2 时程层（flat）

33 列中 **27 列逐位相同**，包括 `pos_x_m`、`pos_y_m`、`pos_z_m`、`pitch_rad`、`roll_rad`、`yaw_rad`、
`vel_x_mps`、`vel_z_mps`、轮端扭矩、悬挂行程、`chassis_min_z_m`。有差别的仅接触力/轮速的 float 末位：

| 列 | 最大绝对差 | 出现行 |
| --- | --- | --- |
| `contact_wheel_L--floor_normal_n` | 4.7e-08 N | 1980 |
| `contact_wheel_R--floor_normal_n` | 4.6e-08 N | 2281 |
| `contact_wheel_L/R--floor_tangent_n` | 3.0e-09 N | 1876 |
| `wheel_L_speed_radps` | 1.0e-09 rad/s | 1793 |
| `wheel_R_speed_radps` | 2.0e-09 rad/s | 1945 |

判定量与整机运动量在 8 位小数量级上完全一致。

### 7.3 时程层（step，限扭）

45 列中 **19 列逐位相同**，包括 `pos_x_m`、`pos_z_m`、`pitch_rad`、`vel_x_mps`、`vel_z_mps`、轮端扭矩。
分歧从第 1378 行（`t≈2.756 s`）开始，先是 1e-9 N 级接触力末位差；到第 ~2402 行（`t≈4.804 s`）
左右轮谁先压上台阶/地面的接触计数发生互换，随后左右对称量整体反号：

| 列 | 最大绝对差 | 说明 |
| --- | --- | --- |
| `slip_max_L` / `slip_max_R` | ±0.0150588（2.36%，左右互换） | Mac 0.637269360 / 0.622210526；Win 0.622210526 / 0.637269360 |
| `susp_travel_max_L_m` / `_R_m` | ±4.565e-06 m（左右互换） | 4.567495 / 4.562930 mm 对调 |
| `roll_rad` | 8.0e-04 rad | 峰值 0.0004 rad 的符号相反 |
| `yaw_rad` | 8.6e-04 rad | 同上 |
| `vel_y_mps` | 5.3e-03 m/s | 同上 |
| `pos_y_m` | 7.6e-05 m | 同上 |
| `wheel_L/R_speed_radps` | 1.105 rad/s | 分歧时刻左右轮速互换 |
| `contact_*_step_normal_n` / `_floor_normal_n` | 4.9–11.8 N | 接触在左/右轮之间换了先后 |

这是**对称工况的左右镜像翻转**，不是量级失控：整机前进量、`pos_z`、pitch、`vel_x` 与判定全部不变。
根因是跨平台浮点末位差在台阶接触事件排序上被对称分支放大；两侧均在 `2 ms` 单一步长下逐位可复现，
但跨平台不能要求逐位一致。逐列明细见 `docs/试跑/证据-windows/timeseries-diff-vs-mac.csv`。

## 8. 复跑步骤（复核用）

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git checkout 5380699
.venv\Scripts\python.exe scripts\run_cases.py --config cases\flat.json --out outputs\recheck_flat --repeat 2
.venv\Scripts\python.exe scripts\run_cases.py --config cases\step_forward_20mm_low_torque.json --out outputs\recheck_step --repeat 2
```

`--out` 目录必须不存在（S12）；重复跑请换目录名。核对 `run.json.git.commit`、
`git.dirty=false`、`scenario_xml_sha256` 与本报告一致。

## 9. 未覆盖与卡点

1. **`scripts/verify_structure.py` 仍不可跑**：同一前缀迁移问题在 S16 报
   `ModelCheckError: 台账缺行：mass.assembly`（Mac/Windows 同）。本任务只要求基线 + 判定，未纳入修复；
   需单独修 `verify_structure.py` 的台账取用后再声称“结构自查 27 项全过”。
2. **`feat/g2-pipeline` 未更新**：远端仍是 `dc7d14c`。本次修复/证据在 `feat/g2-pipeline-winverify`（PR #36），
   需由维护者决定 cherry-pick 或合并，未做强推。
3. Windows 工作区原有未跟踪 `build/` 未纳入版本管理；运行记录通过临时移开该目录取得 `dirty=false`，
   跑完已恢复。仓库若长期保留它，建议加入忽略规则或清理。
4. 只验证了两条工况（平地、限扭 20 mm）。斜向 ±30°、baseline 0.8 N·m 正向 20 mm 未在 Windows 重跑。
5. 结论等级仍是 `mechanism`（`z_cg` 缺失）；本报告只证明“可复跑”，不改变参数等级或物理结论。
