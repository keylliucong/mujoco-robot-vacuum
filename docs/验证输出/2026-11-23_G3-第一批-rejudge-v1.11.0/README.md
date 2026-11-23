# G3 第一批 v1.11.0 重判证据（后缘口径）

- 判据：契约 **v1.11.0**（main `87bacfb`）；`crossed ⇔ s_rear ≥ step_front_m`。
- 输入：既有 `E:\mujoco-robot-vacuum\.tools\preserve\outputs-pre-v111-20261123\g3-b1` 下的 `timeseries.csv`；**未重跑仿真**。
- 左列（v1.10.x）：`docs/验证输出/2026-11-23_G3-第一批-v1.10.1/rejudge_summary.csv`，逐字沿用。
- 覆盖：22 批 / 26 格。环境：Windows 11 `DESKTOP-RGG6DMC`，Python 3.13.0 / MuJoCo 4.0.1；`--wrapper baseline`。
- 结果：outcome 翻转 0 格；cleared 20、invalid 6，两列逐格一致。
- 判据层变化：`bis_p15_h15p0` / `bis_m15_h15p0` 后缘余量 **−0.0106 m**，新增 `front_edge_not_passed`；因横向 `invalid` 先判，outcome 不翻。

```powershell
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --root E:\mujoco-robot-vacuum\.tools\preserve\outputs-pre-v111-20261123\g3-b1 `
  --out outputs\rejudge-v111\g3b1-v111 `
  --summary-csv outputs\rejudge-v111\g3b1-v111\summary.csv `
  --legacy-summary docs\验证输出\2026-11-23_G3-第一批-v1.10.1\rejudge_summary.csv
```

文件：`summary.csv`（26 行）+ 22 个批次 JSON。
