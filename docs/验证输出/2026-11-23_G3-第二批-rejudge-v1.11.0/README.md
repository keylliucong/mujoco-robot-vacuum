# G3 第二批 v1.11.0 重判证据（后缘口径）

- 判据：契约 **v1.11.0**（main `87bacfb`）；`crossed ⇔ s_rear ≥ step_front_m`。
- 输入：既有 `E:\mujoco-robot-vacuum\.tools\preserve\outputs-pre-v111-20261123\g3-b2\<维>\<批>` 下的 `timeseries.csv`；**未重跑仿真**。
- 台账：每批使用输出目录内的 `derived_ledger.csv`（`--ledger-from-batch`），保证摩擦维 μ=0.5 与原件一致。
- 左列（v1.10.x）：各批原生 `summary.csv` 的 v1.10.1 判定，逐字沿用。
- 覆盖：7 批 / 14 格（每批 `repeat 2`）。环境：Windows 11 `DESKTOP-RGG6DMC`，Python 3.13.0 / MuJoCo 4.0.1；`--wrapper oomwoo`。
- 结果：outcome 翻转 0 格；cleared 2、blocked 12，两列逐格一致；`cross_fail_reasons` 无差异。

```powershell
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --root E:\mujoco-robot-vacuum\.tools\preserve\outputs-pre-v111-20261123\g3-b2 `
  --out outputs\rejudge-v111\g3b2-v111 `
  --summary-csv outputs\rejudge-v111\g3b2-v111\summary.csv `
  --wrapper oomwoo --ledger-from-batch derived_ledger.csv --legacy-native
```

文件：`summary.csv`（14 行）+ 7 个批次 JSON。
