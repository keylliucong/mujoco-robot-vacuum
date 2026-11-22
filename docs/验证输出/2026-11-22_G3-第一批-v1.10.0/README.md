# G3 第一批 v1.10.0 重判证据

- 重判提交：`d5ce398`（`trial/g3-sweep`，脚本 `scripts/rejudge_cases.py`）
- 判据：契约 **v1.10.0**（main `b4ceaae`，`judge.CONTRACT_VERSION=1.10.0`）
- 输入：v1.9.x 已跑出的 `outputs/g3-b1/<batch>/.../timeseries.csv`（**未重跑仿真**）
- 输出：`rejudge_summary.csv`（26 个 tier 行）+ `<batch>.json`（22 个批次，含 judge 全量 verdict、`crossing.end_duty` 与前置横向校验）
- 命令（Windows）：

```powershell
.venv\Scripts\python.exe scripts\rejudge_cases.py `
  --root outputs\g3-b1 `
  --out outputs\g3-b1-rejudge-v1100 `
  --summary-csv docs\验证输出\2026-11-22_G3-第一批-v1.10.0\rejudge_summary.csv
```

说明：

- `report_outcome` 是报告层派生标签（`cleared` / `invalid:<reason>`），不是 `failure_primary`。
- v1.10.0 的 `invalid` 不是失败类别，不写 `failure_primary` / `failure_flags`，不进分母、不参与等级。
- 本批 26 行：cleared 20、invalid 6（全部 `lateral_exit_step_width`）、blocked 0；无 `end_state_ambiguous`、无 `step_too_narrow_for_heading`、无 `data_invalid`。
- `end_duty` 由既有 `contact_*_active` 列按 v1.10.0 的末 `end_hold_s=0.05 s` 窗口重算；`end_frames` 为窗口内帧数。
