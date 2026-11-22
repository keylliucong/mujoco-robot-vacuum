# 启动 Viewer 看仿真

`scripts/view.py` 直接开 MuJoCo 的被动查看器窗口，实时看整机越障：四轮接触力、轮速、扭矩、位移、质心高度、离地间隙和判定状态都在终端 HUD 和窗口右上角面板里，叠加层画质心、接触法向箭头和前进方向。**不开截图、不导出图片，自己看**；模型文件不改，台阶仍由 `scripts/run_cases.py` 的注入函数在运行时加进去。

## ① 第一次跑：一条命令，先把环境装上

```bash
cd /path/to/mujoco-robot-vacuum
./scripts/view.sh
```

- 没有 `.venv/` 时脚本会自己建虚拟环境并 `pip install -r requirements.lock.txt`，**约 1–2 分钟**（需联网）；之后再跑就秒开。
- 不带参数 = 平地工况（`flat`）+ 实时播放。
- macOS 上 `mujoco.viewer.launch_passive` **必须**用 `mjpython` 启动，`view.sh` 会自动选 `.venv/bin/mjpython`。手动跑时要写：

  ```bash
  .venv/bin/mjpython scripts/view.py --case step_10mm
  ```

- 本页实测环境：macOS 27.2.1（arm64）、Python 3.13.18、MuJoCo 4.0.1、glfw 2.11.0、NumPy 2.5.5。

## ② 之后直接带参数跑

```bash
./scripts/view.sh --case step_20mm --config oomwoo --speed 0.25
```

可用工况（`--case`）：

| 预设 | 内容 | h 与 12.5 mm 壳体离地 |
| --- | --- | --- |
| `flat` | 平地直行，无台阶 | — |
| `step_10mm` | 正向台阶 10 mm | 低于离地间隙 |
| `step_20mm` | 正向台阶 20 mm（`oomwoo_step20_casterblock`） | **高于**离地间隙 |
| `step_30mm` | 正向台阶 30 mm（由 20 mm case 在内存里改高度注入） | **高于**离地间隙 |
| `step_10mm_lowtorque` | 10 mm + 限扭 0.15 N·m，预期失败 | 低于离地间隙 |
| `oblique_30deg` | 斜向 30° 接近 20 mm 台阶（原型机 `baseline.xml`，参数集 `proto_v1`） | 原型机离地 40 mm |
| `slope_30deg` | 30° 等效斜面静置观测（重力绕 +y 旋转，不驱动，`slope_hold.py` 口径） | — |

也可以直接给一个 case JSON 路径：`--case cases/oomwoo_step10.json`。

常用参数：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--config` | 跟随 case 声明的 `config_id`（OOMWOO 工况即 `oomwoo`） | 参数集 `params/<config_id>.json`；显式给了就必须与 case 一致，不一致直接报错 |
| `--mode` | `live` | `live` 实时 / `step` 按空格单步 |
| `--speed` | `1` | `live` 倍速：`0.25` 慢放看接触、`1` 实时、`4` 快进 |
| `--step-size-s` | 1 个时间步（2 ms） | `step` 模式每按一次空格推进的仿真秒数 |
| `--hud-interval` | `0.5` | 终端 HUD 刷新间隔（仿真秒） |
| `--fn-ref` | `20` | 法向箭头满量程（N） |
| `--max-sim-s` | runner 的 40 | 最长仿真时长 |
| `--slope-max-drift` | `1.0` | 斜面观测位移上限（m），超过就停；`0` = 不限 |
| `--no-creep` / `--skip-checks` | — | 跳过静置蠕滑基线 / 跳过 A1–A5 模型自检 |
| `--headless N` | — | 不开窗口跑 N 秒仿真然后退出（自检 HUD 与判定链路） |
| `--exit-after-s N` | `0` | 墙钟 N 秒后自动退出（录屏/自检用） |

## ③ 键盘与鼠标

| 操作 | 效果 |
| --- | --- |
| 左键拖拽 | 旋转视角 |
| 滚轮 | 缩放 |
| 右键拖拽 / Shift+左键 | 平移视角 |
| **空格** | `live`：暂停 / 继续；`step`：前进一帧（默认 2 ms） |
| `p` | 同空格（暂停 / 继续） |
| **Esc** | 退出，终端打印本轮摘要 |

退出（或判定窗口跑满、按 Esc）后终端会打印：时长、最终 `outcome`、最大 Fn（带接触对）、judge 的 `status/passed/flags`、是否触发蠕滑红线。判定窗口跑满时窗口不自动关，会先打一行 `运行结束：outcome=...`，按 Esc 出完整摘要。

## HUD 里每一行是什么

```
[step_10mm] t=  4.90 s  x= 0.7452 m  v=+0.148 m/s  h= 10.0 mm  mode=live  speed=1x
  驱动轮L: Fn= 13.610 N  Ft= 0.048 N  (n=2)  ω= +4.174 rad/s  τ=+0.004 N·m
  驱动轮R: ...
  从动轮  : Fn=  1.249 N  Ft= 0.096 N  (n=2)  ω=+11.948 rad/s
  底盘壳体: Fn=—        Ft=—     (n=0 无接触)
  z_cg=0.0466 m  离地间隙= 12.47 mm   pitch=-0.01°  roll=+0.00°
  接触 floor_plane→wheel_L_tire: Fn=+13.610 N  Ft=0.048 N  (n=2)  n=[+0.00 +0.00 +1.00]
  状态: cleared   判定窗口结束
```

- **Fn / Ft**：该 body 当帧所有接触点的法向力之和 / 切向力模长之和，`n` 是接触点个数。`—` 表示无接触，**不是**测到 0（缺失≠零）。
- **ω / τ**：驱动轮关节角速度（rad/s）与轮端扭矩（N·m，执行器力）。
- **z_cg**：整机质心高度（只统计 `chassis` 运动树，注入的台阶 body 不算）。
- **离地间隙**：`chassis_*` 几何最低点到地面的距离，实时值。
- **接触行**：`geom1→geom2`，`n=[x y z]` 是接触帧法向（世界系）。
- **状态**：`cleared` / `blocked` / `invalid`，由 `judge.judge_case` 判；另有两种特殊显示：`pending`（判定窗口还没跑满）、`未覆盖此机理`（见下）、`观测`（斜面工况 judge 不覆盖）。

### 接触力口径（与 G1 校验一致）

- 只用 `mujoco.mj_contactForce(model, data, i, res)` 读，`res[0]` 法向、`res[1:3]` 切向，单位 N；**不用 `efc_force`**。
- `res` 在接触帧内，世界分量按 `f_world = contact.frame.T @ res[0:3]` 旋转（`contact.frame` 三行是世界系法向与两个切向）。
- 正方向：力由 `geom1` 指向 `geom2`，**对 geom2 为正**；HUD 每行都带 geom1/geom2 名称。
- 叠加层里每个接触点的箭头沿接触帧法向 `frame[0]`，长度按 `Fn / --fn-ref` 归一化（上限 50 mm）。

### 台阶高于壳体离地间隙时

仅当模型**没有**参数化壳体前下缘（`chassis_front_lip`）时，`h > floor_clearance`
（OOMWOO 是 12.5 mm）会让 HUD 固定显示一行警示，并且 **outcome 显示「未覆盖此机理」而不是 cleared/blocked**：

```
⚠ h > 12.5 mm：本模型未覆盖壳体前下缘接触，结果不代表通过能力
```

原因：旧 OOMWOO 模型没有柔性保险杠/壳体前下缘接触，10 mm 以上先接触的是定高的车头从动轮和刚性壳体，`step_20mm`/`step_30mm` 会卡在台阶立面（`chassis_shell→step` 力很大、`wheel*--step` 从不接触）。这不是"没通过"，是这个模型没覆盖那段机理，不能当通过能力结论。

G2.5 起 `models/oomwoo.xml` 带参数化 `chassis_front_lip`（参数在 `params/oomwoo_g25.json`），
h > 12.5 mm 时前下缘接触已被建模：viewer 不再显示「未覆盖」，而是按 judge 给出
`blocked`（典型为 `belly_contact`）或 `cleared`。

## 两种模式怎么用

**实时看全过程**（推荐先跑这个）：

```bash
./scripts/view.sh --case flat --config oomwoo --speed 1
```

**单步看接触瞬间**（轮子刚碰到台阶棱边那一下）：

```bash
./scripts/view.sh --case step_10mm --config oomwoo --mode step
```

`step` 模式起跑就是暂停的，每按一次空格推进 1 个时间步（2 ms）。想快一点加 `--step-size-s 0.05`（每次 25 步）。

## Windows 上怎么看

Windows 机器不直接改代码：**Mac 上先提交并推到 GitHub，再到 Windows 拉取**。

```bash
# Mac：提交并推送
git push origin <分支名>
```

```powershell
# Windows（从 Mac 执行 ssh win 进入，或在 Windows 终端里）
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git fetch origin
git switch <分支名>
git pull --ff-only
git rev-parse HEAD

# 首次同样会自动建 .venv（Windows 用 py -3.13，不加 mjpython）
scripts\view.bat --case step_10mm --config oomwoo --speed 1
```

`view.bat` 与 `view.sh` 逻辑一致：没有 `.venv\Scripts\python.exe` 就先建环境装 `requirements.lock.txt`，然后 `python scripts\view.py`。参数完全相同；`chcp 65001` 已设好，中文 HUD 不会乱码。

`scripts\*.bat` 必须保持纯 ASCII：注释和 `echo` 提示一律用英文。Windows `cmd.exe` 按本地 ANSI/OEM 代码页解析批处理，UTF-8 中文注释会被拆成命令，报出一串“不是内部或外部命令”。中文说明只写在本文件里，批处理里最多用英文提示指向 `docs` 目录。

## 自检与常见问题

- **不开窗口先查链路**：`./scripts/view.sh --case flat --headless 5` 跑 5 s 仿真、打 HUD 和摘要，不开 GL 窗口。
- **窗口没出现 / 报 `requires mjpython`**：macOS 手动跑时必须用 `.venv/bin/mjpython`；`view.sh` 已自动处理。
- **黑屏或很卡**：`--speed 0.25` 降速；HD 屏可以缩小窗口。倍速只是目标值，实际受渲染帧率限制——本机实测（macOS 27.2.1 / M 系）`--speed 4` 大约只能跑到 1.5x，`0.25` 和 `1` 都能到位。
- **`--config` 报不一致**：case 的 `notes` 里写了 `config_id=`，不传 `--config` 时会自动用它；一旦显式传了就必须相同（S21 契约），例如 `--case oblique_30deg --config oomwoo` 会直接报错，去掉 `--config` 或写 `--config proto_v1` 才对。
- **首次建环境失败**：多半是网络或 Python 版本；`.venv/` 可整个删掉重来，仓库里不会残留其它文件。
- **判定的`passed`只看 `fail_on`**：`slip`、`torque_limit`、`bottom_out` 不在本 case 的 `fail_on` 里时会出现在 `flags` 但不改变 `passed`，这是契约行为，不是 viewer 的问题。
