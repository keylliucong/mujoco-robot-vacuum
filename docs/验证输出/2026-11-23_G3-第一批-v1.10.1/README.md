# G3 第一批 v1.10.1 ±15° 复核证据

- 判据：契约 **v1.10.1**（main `d84d411`，`judge.CONTRACT_VERSION=1.10.1`）
- 分支：`docs/g3-v1101`（从 main `d84d411` 起）
- 输入：v1.9.x 已跑出的 `E:\mujoco-robot-vacuum\outputs\g3-b1\<batch>\...\timeseries.csv`（**未重跑仿真**）
- 输出：`outputs\g3-b1-rejudge-v1101\`（22 个批次 JSON，含 judge 全量 verdict、`crossing.lateral_drift_excess_m` / `lateral_drift_ratio` / `lateral_drift_untrusted`）；本目录 `rejudge_summary.csv`（26 个 tier 行）
- 执行位置：Windows 11 `DESKTOP-RGG6DMC`，隔离 worktree `E:\mujoco-robot-vacuum-wt-v1101`（detached `d84d411`），`outputs` 为指向主工作区 `outputs` 的目录联接
- 环境：Python 3.13.0 / MuJoCo 4.0.1（`.venv\Scripts\python.exe` 取自主工作区）
- 命令（PowerShell，worktree 内）：

```powershell
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --root outputs\g3-b1 `
  --out outputs\g3-b1-rejudge-v1101 `
  --summary-csv docs\验证输出\2026-11-23_G3-第一批-v1.10.1\rejudge_summary.csv
```

结果：

- 26 个 tier 行：cleared 20、invalid 6（全部 `lateral_exit_step_width`）、blocked 0。
- ±15° 的 6 个 invalid 格（14 / 15 / 20 mm × ±15°）`abs(end_lat)` 为 1.3891–3.6651 m，全部 >0.6 m，按 v1.10.1 仍先判 `invalid:lateral_exit_step_width`。
- 同 6 格 `lateral_drift_untrusted=true`（`drift_ratio` 0.9667–2.9262 ≥0.5），但 `judge.py` 的几何出界分支在前，最终 `invalid_reason` 仍是 `lateral_exit_step_width`。
- ±15° 的 10 / 12.5 / 13.5 mm `drift_ratio` 为 0.1268–0.2320 <0.5，仍 cleared，未被新口径误判。
- 其余维度（heading=0、0° 二分点）的 v1.10.1 结果与 v1.10.0 逐行一致。
