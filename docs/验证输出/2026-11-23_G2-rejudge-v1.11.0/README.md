# G2 步进批次 v1.11.0 重判证据（后缘口径）

- 判据：契约 **v1.11.0**（main `87bacfb`，`judge.CONTRACT_VERSION=1.11.0`）；`crossed ⇔ s_rear ≥ step_front_m`，`s_rear = s − L_rear`。
- 重判代码：`docs/rejudge-v111` 的 `scripts/rejudge_cases.py`（只扩展重判工具；`judge.py` / `run_cases.py` 未改）。
- 输入：`E:\mujoco-robot-vacuum\.tools\preserve\outputs-pre-v111-20261123\g2_*` 下既有 `timeseries.csv`；**未重跑仿真**。
- 左列（v1.10.x）：同一批时程在 `E:\mujoco-robot-vacuum-wt-rejudge-v110`（detached `d84d411`）按 v1.10.1 judge 重判，输出 `outputs\rejudge-v111\g2-legacy-v1101`，用于隔离「质心→后缘」这一项变更。
- 覆盖：17 批 / 33 格（v1.9.0、浮点容差、返工三项、返工二轮）。
- 环境：Windows 11 `DESKTOP-RGG6DMC`，Python 3.13.0 / MuJoCo 4.0.1。
- 结果：outcome 翻转 0 格；cleared 6、blocked 10、invalid 17，两列逐格一致。

```powershell
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --out outputs\rejudge-v111\g2-v111 `
  --summary-csv outputs\rejudge-v111\g2-v111\summary.csv `
  --legacy-summary E:\mujoco-robot-vacuum-wt-rejudge-v110\outputs\rejudge-v111\g2-legacy-v1101\summary.csv `
  --root <17 个 g2_* 批目录>
```

文件：`summary.csv`（33 行，含 `end_progress_m` / `com_progress_m` / `L_rear_m` / `s_rear_m` / 新旧余量 / 旧判定列）+ 17 个批次 JSON（judge 全量 verdict）。原始 `timeseries.csv` 仍留在 Windows，按 `.gitignore` 不入库。
