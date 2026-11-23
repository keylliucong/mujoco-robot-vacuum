# G3 时步批次 v1.11.0 重判证据（后缘口径）

- 判据：契约 **v1.11.0**（main `87bacfb`）；`crossed ⇔ s_rear ≥ step_front_m`，`cross_index` 也用 `s_rear`。
- 输入：`E:\mujoco-robot-vacuum\.tools\worktrees\g3-timestep\outputs\g3-timestep\` 下既有 `timeseries.csv`；**未重跑仿真**。
- 左列（v1.10.x）：`docs/验证输出/2026-11-22_G3-时步-v1.10.0/rejudge_summary.csv`，按 `control_period_ms` 拆成 `legacy-2.csv`（21 行）/ `legacy-20.csv`（18 行）/ `legacy-5.csv`（6 行），逐字沿用。
- 覆盖：45 格 = 2 ms 控制周期 21 格（9 批 × 2 repeat + `repeat3-12p5` 3 repeat）、20 ms 18 格、5 ms 6 格；剔除 `_probe_ctrl20ms` / `probe`。
- 环境：Windows 11 `DESKTOP-RGG6DMC`，Python 3.13.0 / MuJoCo 4.0.1；`--wrapper oomwoo`。
- 结果：outcome 翻转 0 格；cleared 8、blocked 35、invalid 2，两列逐格一致。

```powershell
# 2 ms 控制周期（719b744 + repeat3-12p5）
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --root ...\g3-timestep\719b744 --root ...\g3-timestep\repeat3-12p5 `
  --exclude "_probe*" --exclude "probe" `
  --out outputs\rejudge-v111\g3ts-2ms-v111 `
  --summary-csv outputs\rejudge-v111\g3ts-2ms-v111\summary.csv `
  --wrapper oomwoo --legacy-summary outputs\rejudge-v111\g3ts-v111\legacy-2.csv
# 20 ms / 5 ms 同理，分别用 ctrl20ms + legacy-20.csv、ctrl5ms + legacy-5.csv
```

文件：`2ms/`、`20ms/`、`5ms/` 各含 `summary.csv` + 批次 JSON；根目录 `legacy-*.csv` 为旧判定输入。
