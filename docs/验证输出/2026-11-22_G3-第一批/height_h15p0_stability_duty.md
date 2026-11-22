# 15 mm 两档稳定性占空比计算说明

- 输入：`outputs/g3-b1/height_h15p0_stability/g3_b1_height_h15p0_r{1,2}/{timeseries.csv,tier_1ms/timeseries.csv}`（Windows，提交 `6b5566e`）。
- 占空比窗口：每条 `timeseries.csv` 的末 50 ms（`t >= t_end - 0.050 s`；2 ms 档 26 帧，1 ms 档 51 帧）。
- `both_wheels_on_top`：与 `judge.py` 的 `both_wheels_on_top` 同义，即 `contact_wheel_L--step_active=1` **且** `contact_wheel_R--step_active=1`。
- `contact_gap_max_s`：取自同批次 `run.json.cases[0].repeats[].tiers[].verdict.metrics.crossing.contact_gap_max_s`。
- `contact_normal_max_n`：该档全部时程、全部接触对的 `*_normal_n` 列最大值（`mj_contactForce` 法向分量）。
- 静态轮载：`m*g/2`，`m=2.23 kg`（台账 `prototype.proto_v1.mass.assembly`），`g=9.81 m/s²` → `10.94 N/驱动轮`。按两驱动轮均分整机重量，未扣万向轮分载；工程假设。
- `static_load_multiple = contact_normal_max_n / 10.94`。本批两档均 >5×，按专家口径标「数值冲击区间」，不得当物理力。
- `report_outcome`：按专家口径的报告层标签，**不是** `judge.py` 的枚举；`judge_outcome` 保留 `summary.csv` 的 `passed` 原值（blocked = `passed=0`，cleared = `passed=1`）。
