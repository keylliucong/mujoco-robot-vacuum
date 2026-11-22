# G3 时步批次 v1.10.0 重判证据

- 重判代码：`8598b41`（`feat/g3-timestep`，`scripts/rejudge_cases.py --wrapper oomwoo`）
- 判据：契约 **v1.10.0**（main `b4ceaae`）；重判 JSON 的 `contract_version = 1.10.0`
- 原始 run（均为契约 **1.9.0**）：`719b744`（2 ms 控制周期，9 组）、`ctrl20ms`（20 ms 控制周期，9 组）、`ctrl5ms`（5 ms 控制周期，3 组）、`repeat3-12p5`（2 ms 控制周期，repeat 3）
- 输入：上述批次已跑出的 `timeseries.csv`；**未重跑仿真**
- 文件：
  - `rejudge_summary.csv`：45 行，4 轮合并（已剔除 `_probe_ctrl20ms` / `probe` 两个侧实验），带 `control_period_ms`
  - `rejudge_2ms_control.csv` / `rejudge_20ms_control.csv` / `rejudge_5ms_control.csv` / `rejudge_repeat3_12p5.csv`：分轮原始输出
  - `<round>/<batch>.json`：每个批次的 judge 全量 verdict、`crossing.end_duty` / `end_frames` / `end_state_ambiguous` / `lateral_exit` 与前置横向校验
- 关键结论：v1.10.0 下 **2 ms / 5 ms 控制周期**的边界仍是 (10, 12.5] mm；**20 ms 控制周期**的 10 mm 在 2 ms 时步为 `invalid:end_state_ambiguous`（`end_duty=0.68`），1 ms / 0.5 ms 时步为 `blocked`（`end_duty` 0.47 / 0.44，`failure_primary=cross_fail`），该控制周期没有 cleared 高度。v1.9.0 报告里的「2/5/20 ms 一致」不能作为 v1.10.0 结论。
