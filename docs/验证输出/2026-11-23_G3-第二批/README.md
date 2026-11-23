# G3 第二批（摩擦/限扭/速度敏感性）证据

- 判据：契约 **v1.10.1**（`judge.CONTRACT_VERSION=1.10.1`、`run_cases.CONTRACT_VERSION=1.10.1`）
- 分支：`trial/g3-sweep`，base = main `c159a74`；运行提交 `a691bed`（`git.dirty=false`）
- 机型：`models/oomwoo.xml`，sha256 `0bb889f505f4ed73cb573ff8a88ea119c5f9e6138a4ed6e6cfacf17cdf9b0c8e`
- 参数集：`params/oomwoo_g25.json`，`config_id=oomwoo_g25`，`machine=oomwoo`；台账含 `oomwoo.oomwoo_g25.com.chassis.z`【缺失】，runner 自动等级为 `mechanism`
- 平台：Windows 11 `DESKTOP-RGG6DMC`，独立 worktree `E:\mj-g3b2`；解释器 `E:\mujoco-robot-vacuum\.venv\Scripts\python.exe`
- 环境：Python 3.13.0 / MuJoCo 4.0.1 / numpy 2.5.5
- 数值：物理步 2 ms、版本内控制周期 2 ms（`cases/_runner.json` 的 `drive.update_period_s=0.002`，未用 CLI 覆盖）；`implicitfast` / `Newton` / `pyramidal` / `iterations=100`
- 重复：每批 `--repeat 2`；7 批全部 `repeat.consistent=true`（逐位一致）

## 运行命令（worktree 内）

```powershell
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\run_g3b2.py `
  --config cases\g3-b2\<case>.json `
  --out outputs\g3-b2\<dim>\<batch> --repeat 2
```

`scripts/run_g3b2.py` 只做一件事：把 case 的 `environment.pairs[*].friction[0]`
写进派生台账的 `contact.<pair>_friction_s` 行，交给未修改的 `run_oomwoo.py` /
`run_cases.py`。限扭/速度维的派生台账与基准台账内容相同（仅 CSV 写入器的
CRLF 换行差异）；摩擦维只改 `contact.wheel_floor_friction_s` 与
`contact.wheel_step_friction_s` 两行。
每批目录下的 `derived_ledger.csv` 是实际使用台账。

## 批次与 config sha256

| 维 | 批 | case | case 引入提交 | config sha256 |
| --- | --- | --- | --- | --- |
| 摩擦 | `friction/mu0p5_h10p0` | `g3_b2_friction_mu0p5_h10p0` | `282f785` | `d801dc2e8dd4f2905968a6ec9c57fd00f67834399b5298574525ec03431b2b19` |
| 摩擦 | `friction/mu0p5_h12p5` | `g3_b2_friction_mu0p5_h12p5` | `75f3df0` | `3f45a9aaf80718f1591a413de3ebcfe6c81bb16239ff6910e3dd32789147c33e` |
| 摩擦 | `friction/mu0p5_h15p0` | `g3_b2_friction_mu0p5_h15p0` | `ffbd4bc` | `8a8bdaec6eae579bbf33893895859c47b2ead756342d0957aa70ad8df0fd057c` |
| 限扭 | `torque/tq0p09_h12p5` | `g3_b2_torque_0p09_h12p5` | `ebef338` | `f7acc81408c936565e3310423f6ada8d9d0860f3eb39f4dd5be870e23721534b` |
| 限扭 | `torque/tq0p09_h15p0` | `g3_b2_torque_0p09_h15p0` | `0920afc` | `4da2c5cbf5e82d4d97c06ea043f98366a5e5b7c58b8fbf8387a95f0413b19e79` |
| 速度 | `speed/v0p25_h15p0` | `g3_b2_speed_0p25_h15p0` | `d838f40` | `6c141ef38e456aab8918c2e027834fa249104c6faf054892cf208d5b4797e174` |
| 速度 | `speed/v0p25_h20p0` | `g3_b2_speed_0p25_h20p0` | `69fd825` | `617b7f0bea3ec5cbdf34ff9b7e7f1378c160847b3ee9f907c7adc76c5b3f1aff` |

## 文件

每个批目录含 `run.json` / `summary.csv` / `stdout.log` / `derived_ledger.csv` / `case.json`；
根目录 `summary_all.csv` 汇总 7 批的首个 repeat 判定字段。

Windows 原始输出已迁到主工作区 `E:\mujoco-robot-vacuum\outputs\g3-b2\<dim>\<batch>\`
（含每批 `timeseries.csv`）；`E:\mj-g3b2` worktree 跑完后已用
`git worktree remove --force` 移除。
