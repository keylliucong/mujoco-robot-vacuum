# 12.5 mm × 2 ms 控制周期 repeat 3 复核证据

- run SHA：`aeae6d2557055b896981087918c2bfcb249d1015`（tag `g3-run-aeae6d2`，契约 v1.9.0，与 G3 时步报告同一口径）
- case：`cases/oomwoo_step12p5_dt2ms.json`（12.5 mm，物理时步 2 ms）
- 命令：`scripts/run_oomwoo.py --config cases\oomwoo_step12p5_dt2ms.json --out outputs\g3-timestep\repeat3-12p5 --repeat 3 --control-period-s 0.002`
- 输出根（Windows）：`E:\mujoco-robot-vacuum\.tools\worktrees\g3-timestep\outputs\g3-timestep\repeat3-12p5\`
- 未加 0.5 ms 档（超出声明适用范围）。

`repeat3_metrics.csv` 的计算口径：

- 判定窗口：`t_trigger=3.976 s` 到 `t_trigger + window_s(8 s)=11.976 s`，共 4001 帧。
- `chassis_step_active_frames`：`contact_chassis--step_active=1` 的帧数；`count` 为该接触对逐帧接触点数合计 / 最大值。
- `wheel_step_touched`：`contact_wheel_L--step_active` 或 `contact_wheel_R--step_active` 在窗口内任一顿为 1。
- `torque_sat_fraction`：`max(|wheel_L_torque_nm|, |wheel_R_torque_nm|) >= 0.5 × (1 - 1e-6) N·m` 的帧数 / 窗口帧数。
- 3 次 `failure_primary=stall`、均带 `bottom_out`；按专家写死规则写「驱动受限为主，几何接触并存」，边界仍是几何上界。
