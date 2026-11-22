# OOMWOO One 全流程试跑报告

- 日期：2026-11-22
- 任务分支：`dryrun/oomwoo-step`
- 基线提交（Windows 实跑）：`24f73251d02e79363dbafb8b6c34c56cd09a7538`
- 本报告随后续文档提交更新；所有仿真数字对应上面的提交，不是报告自身的提交
- 输入：`makerspet/oomwoo-cad@266210a47cab931c5891a07c9a29d48388a54b0c`、`makerspet/oomwoo-one@a630d1c77255072d280a2a41a7a2bd1a1c98cadd`
- 结论口径：本轮**没有判定结论**。只记录 `outcome = cleared / blocked / invalid` 和失败模式，不写“通过高度”或“能过多高”。

## 0. 一句话结果

流程走到第 4 步（工况 → runner → judge）并在 Windows 跑完 4 个配置 + 1 个斜面观测，重复两次逐位一致；第 1 步在**整机质量属性**上卡住：`oomwoo-cad` 没有 `designs/one/stock/`，唯一“整机 STEP”是作者声明有已知设计错误的 `agentic/july-2026/device_full.step`，本轮没有用它。可信 `lib/` STEP 的部件级 B-rep 质量属性已经跑通，但整机 CoM/z_cg、惯量和装甲壳体几何仍只能假设；因此所有批次的 `conclusion_level = mechanism`。

| 步骤 | 状态 | 产物 | 卡点 |
| --- | --- | --- | --- |
| 1 STEP → 质量属性 | 部件级完成，整机级卡住 | `docs/试跑/step-质量属性-oomwoo.csv` | 无 stock 整机 STEP；z_cg 无实测 |
| 2 STEP → 几何 | 部件级 + 公开尺寸链完成 | 本报告 §3 | 整机 CAD 全局系不存在 |
| 3 几何 → MJCF | 完成（含 3 处试跑补丁） | `models/oomwoo.xml`、`params/oomwoo.json` | `model_checks` 只认 box；无悬挂 |
| 4 工况 → runner → judge | 完成 4 配置 + 斜面观测 | Windows `outputs/oomwoo-*-win/` | 契约无 slope 工况；台阶注入降高 |
| 5 双机执行 | 完成 | Windows worktree，SHA `24f7325` | 无 |
| 6 一致性 | 完成 | 同机重复逐位一致 | 跨 Mac/Windows 非逐位一致（记录） |
| 7 报告 | 本文件 | `docs/试跑/` | — |

## 1. 执行位置、环境与命令落点

| 项 | Mac（只编辑/推导/提交） | Windows（只跑已推送提交） |
| --- | --- | --- |
| 位置 | `/Users/liucong/orca/workspaces/mujoco_/oomwoo-step`（git worktree） | `E:\mujoco-robot-vacuum\.tools\worktrees\oomwoo-step`（git worktree） |
| 提交 | `24f7325` + 后续文档提交 | `24f73251d02e79363dbafb8b6c34c56cd09a7538`（detached） |
| Python | 3.13.18（CAD venv） | 3.13.1（项目 `.venv`） |
| MuJoCo | 4.0.1（仅本地预检） | 4.0.1 |
| NumPy | 2.5.5 | 2.5.5 |
| CAD 内核 | `cadquery-ocp 7.9.3.1.1`（OCCT 7.9.3）+ `vtk 9.6.2` | 未安装，不跑 CAD |
| 平台 | macOS 27.2.1 arm64 | Windows 11（`platform` 见 `run.json`） |

Windows 使用独立 worktree，避免与其他 worker 共用 `E:\mujoco-robot-vacuum` 工作区；Python 仍调用主目录 `.venv`。每次 `run.json` 记录 `git.commit=24f7325…`、`git.branch=HEAD`、`git.dirty=false`。

## 2. 输入与来源可信度分级

### 2.1 三个仓库分档

| 档 | 来源 | 能提供什么 | 本轮用法 | 结论 |
| --- | --- | --- | --- | --- |
| A 文档/BOM | `makerspet/oomwoo` 的 `BOM.md`、`docs/SPEC.md`、`oomwoo-one/urdf/params.xacro` | 采购件型号、作者标注的实测尺寸/质量/堵转扭矩 | 只作【公开参考】 | 可直接引用，但不能当本机实测 |
| B 几何数据（可用） | `oomwoo-cad` 的 `lib/`（轮组件、万向轮、风机、电池、齿轮箱等 STEP）与 `designs/one/stock/`（本轮**不存在**） | 可从 STEP 自己推的几何/体积/质心/惯量 | `lib/` 部件做【图纸推算】；`stock/` 为空，整机不可推 | 部件级可信；整机级缺失 |
| C 实验件（不可用） | `oomwoo-cad/designs/one/agentic/july-2026/`：`device_full.step`、`OOMWOO_Device_RV02_Report.pdf` | 看起来像整机几何 | **一律不用**，不引用任何数值 | 作者原文：不是 OOMWOO One 设计，RV02 管线输出，有已知设计错误 |

### 2.2 为什么 C 档不能混进 B 档

`designs/one/agentic/july-2026/README.md` 原文写明：“This is **not** the OOMWOO One design… has **known design errors**”，并列出万向轮倒装、侧刷装反、风机与主刷分处两侧、保险杠装在筒身外、电池仓门小于电池等。万向轮倒装改变支撑多边形，风机位置改变质心，保险杠位置改变台阶接触几何——这些错误**不会让模型看起来坏掉**，只会让质量属性、CoM 和越障接触“错得很像对的”。所以：

- 该目录下的 STEP/PDF 不作为任何质量、几何、接触参数的来源；
- 本报告不给出 RV02 的包围盒、质心、惯量或任何“整机”数字；
- 如果别处已经从它算过数，按本节视为作废。

### 2.3 `stock/` 实际不存在（本轮第一个硬卡点）

在 pin 的提交上核对树：

```text
$ git ls-tree HEAD designs/one/
100644 blob … designs/one/README.md
040000 tree … designs/one/agentic
040000 tree … designs/one/fusion360
```

`designs/README.md` 和 `designs/one/README.md` 都指向 `stock/`，但该提交没有这个目录。`fusion360/Top_Assembly_110926.f3z`（93 MB）是 Fusion 归档，需要 Fusion 360 才能导出 STEP；本轮没有可用整机 STEP。于是“STEP → 整机质量属性”只能做到部件级。

## 3. 第 1 步：STEP → 质量属性

### 3.1 做了什么

新增 `scripts/step_mass_properties.py`：用 OCCT `BRepGProp.VolumeProperties` 对每个实体做 **B-rep 精确体积积分**，不做三角化；逐实体求体积、质心、关于质心的惯量张量，再按体积加权合并。单位从 STEP 的 mm 换算到 SI。密度不是 CAD 数据，按部件单列。

命令原文（Mac，CAD venv；`CAD` 为 `oomwoo-cad` 检出目录）：

```bash
/Users/liucong/cad-scratch/venv/bin/python scripts/step_mass_properties.py \
  --part "drive_wheel=$CAD/lib/roborock/OOM-W01-drive-wheel-assembly.stp=1200" \
  --part "caster=$CAD/lib/casters/irobot_caster.step=1100" \
  --part "suction_fan=$CAD/lib/roborock/OOM-F02-fan-BL24131616.stp=1800" \
  --part "battery=$CAD/lib/roborock/OOM-E01-battery.stp=1900" \
  --part "motor_gearbox=$CAD/designs/one/fusion360/STEP/03-01 Motor_Gearbox.step=2700" \
  --part "main_brush_gearbox=$CAD/lib/roborock/OOM-M01-main-brush-gearbox.step=2700" \
  --out docs/试跑/step-质量属性-oomwoo.csv \
  --solid-out docs/试跑/step-质量属性-逐实体-oomwoo.csv
```

方法与版本写在输出表头：`method=occt-gprop-brep-exact; tessellation=none; ocp=7.9.3.1; python=3.13.18`，每个输入带文件 sha256。脚本提交 `e2952e9`，表提交 `dbdd34b`。

### 3.2 结果（部件级）

| 部件 | 实体数 | 体积 cm³ | 质量 g（密度 kg/m³） | 包围盒 mm | 主惯性矩 kg·m² |
| --- | ---: | ---: | ---: | --- | --- |
| 驱动轮组件 `OOM-W01` | 3 | 131.920 | 158.30（1200） | 72.8 × 111.3 × 60.4 | 5.178e-05 / 1.456e-04 / 1.583e-04 |
| 万向轮 `irobot_caster` | 2 | 16.954 | 18.65（1100） | 49.0 × 67.7 × 57.1 | 2.448e-06 / 2.867e-06 / 3.462e-06 |
| 风机 `OOM-F02` | 18 | 29.036 | 52.26（1800） | 74.8 × 76.5 × 32.6 | 1.409e-05 / 1.552e-05 / 2.230e-05 |
| 电池 `OOM-E01` | 1 | 259.562 | 493.17（1900） | 45.3 × 142.9 × 45.4 | 1.524e-04 / 8.589e-04 / 8.618e-04 |
| 驱动齿轮箱 `03-01` | 25 | 37.008 | 99.92（2700） | 65.5 × 50.9 × 63.0 | 1.802e-05 / 4.981e-05 / 5.310e-05 |
| 主刷齿轮箱 `OOM-M01` | 1 | 47.766 | 128.97（2700） | 62.3 × 49.5 × 66.4 | 2.269e-05 / 6.484e-05 / 7.462e-05 |

驱动轮组件里最大的实体就是轮胎：体积 56.606 cm³，包围盒 **71.610 × 71.610 × 15.760 mm**，质心在组件原点附近（x≈0、y≈0），说明组件原点就是轮轴。滚阻/轮毂形状在 STEP 里，所以轮半径直接用这个实体，而不是按公开 68 mm。

密度只用来把体积换成“如果均匀”的质量；它不是 CAD 数据，也不是实测。表中质量与公开分项（轮 100 g、万向轮 50 g）不一致，原因是组件包含轮臂/电机、密度均匀假设不成立；模型里质量用公开实测分项，惯量用 STEP 形状按实测质量缩放，这两件事在台账里分开标。

### 3.3 整机质量属性（组合结果）

没有整机 STEP，整机值只能由“公开分项质量 + 柱体/球体假设 + 前置 LiDAR 位置”组合。模型里的分配是：

- `chassis`（壳体 2.500 + LiDAR 0.150 = 2.650 kg）
- 左右驱动轮各 0.100 kg
- 车头从动轮 0.050 kg
- 两个 0.001 kg 的无碰撞占位标记体（只为满足 `susp_L/R` 名称表）

| 量 | 值 | 参数等级 | 结论等级 |
| --- | --- | --- | --- |
| 整机质量 | **2.902 kg** | 公开参考分项 + 加和 | mechanism |
| CoM x（B 系） | **+6.340 mm** | 工程假设 | mechanism |
| CoM y | **0**（左右对称设 0） | 工程假设 | mechanism |
| CoM z | **46.669 mm（占位）** | **缺失** | mechanism |
| 关于 CoM 的惯量张量 | `Ixx=0.023217, Iyy=0.022246, Izz=0.042807, Ixy≈0, Ixz=-0.000215, Iyz≈0` kg·m² | 工程假设 | mechanism |
| 三个主惯性矩 | **0.022246 / 0.023215 / 0.042809 kg·m²** | 工程假设 | mechanism |
| 关于 B 原点 | `Ixx=0.029538, Iyy=0.028684, Izz=0.042924, Ixz=-0.001074` kg·m² | 工程假设 | mechanism |

读法：`参数等级` 回答“这些数从哪来”；`结论等级` 回答“拿这些数能说到多远”。z_cg 标【缺失】、CAD 全局系标【缺失】，所以整机结论只能是 `mechanism`。这与“质量分项是公开实测”不矛盾：来源硬，但缺口和容差刻度不到定量。

### 3.4 卡在哪 / 下一步

**卡点**：没有 `stock/` 整机 STEP；`Top_Assembly_110926.f3z` 需要 Fusion 导出；z_cg 没有称重或倾斜法数据。于是整机 CoM z、惯量张量只能由均匀柱体假设给出，不能称【图纸推算】。

三步内可修：

1. 用 Fusion 360 打开 `Top_Assembly_110926.f3z`，导出整机 STEP（记录 sha256，文件不入库，凭 sha 向持有人索取）；或者请维护者补 `designs/one/stock/` 的 STEP。
2. 用同一 `scripts/step_mass_properties.py` 跑整机 STEP，输出逐实体表；把 `chassis` 的柱体假设换成 B-rep 结果。
3. 用三点称重/倾斜法测 z_cg（目标 2 mm），把 `com.chassis.z` 从【缺失】升到【本机实测】；在此之前所有结论保持 `mechanism`。

## 4. 第 2 步：STEP → 几何

### 4.1 机体系 B

原点 O = 左右驱动轮轴心连线中点在地面的投影；+x 前、+y 左、+z 上。`chassis` 在 world 的 `pos=0 0 0`、`quat=1 0 0 0`，与 B 在 t=0 重合。台阶、位姿、接触力都在 B 系。

### 4.2 几何表

| 量 | 值 | 参数等级 | 依据 / 冲突 |
| --- | --- | --- | --- |
| 整机外形包围盒 | **0.349 × 0.349 × 0.097 m** | 公开参考 | `base_diameter=0.349`、壳体顶 0.079 + LiDAR 0.018；无整机 STEP 可复核 |
| 壳体离地间隙 | **0.0125 m** | 公开参考 | `floor_clearance` |
| 驱动轮直径 | **0.071610 m** | 图纸推算 | STEP 轮胎实体；与公开 `wheel_diameter=0.068` 冲突，按 STEP 取 0.07161 |
| 驱动轮宽 | **0.015760 m** | 图纸推算 | STEP 轮胎实体；与公开 0.012 冲突，按 STEP |
| 轮距 | **0.235 m** | 公开参考 | `wheel_base`；无整机 STEP |
| 轮心高度 | **0.035805 m** | 图纸推算 | = 轮半径（A4 约束） |
| 轴距（轮轴→从动轮） | **0.1445 m** | 公开参考 | `base_diameter/2 - caster_inset`；从动轮在车头 +x |
| 从动轮半径 | **0.0125 m** | 公开参考 | `caster_diameter=0.025` |
| 壳体柱体 | R=0.1745、h=0.0665、中心 z=0.04575 m | 公开参考 | 无壳体 STEP，用柱体近似 |
| CAD 全局系 → B | **未定义** | 缺失 | 没有整机 CAD 装配，谈不上 yaw/origin |

几何冲突的处理按任务要求：**从 STEP 自己算的以 STEP 为准**。轮径/轮宽与公开值不一致，是因为公开值是 URDF 里的名义值，STEP 是 Roborock 轮的三维扫描件；两者都保留在台账里，模型用 STEP 值并标注冲突。

## 5. 第 3 步：几何 → MJCF

### 5.1 模型与参数注入

`models/oomwoo.xml` 头部：

```text
model=oomwoo-step-dryrun; machine=oomwoo; parameter_source=params/oomwoo.json
source=makerspet/oomwoo-cad@266210a… + makerspet/oomwoo-one@a630d1c…
method=B-rep STEP（轮实体）+ 公开尺寸链；整机壳体柱体近似
```

XML 里没有写死物理常数：质量、CoM、惯量、几何、摩擦、接触求解器、重力、扭矩上限全部是 `${id}`，由 `params/oomwoo.json` 渲染。台阶不在 XML 里，由 runner 注入。

模型结构：

- `chassis`：freejoint，圆柱壳体 `chassis_shell`（R=0.1745、半高 0.03325、中心 z=0.04575）。
- `caster_front`：车头 +x=0.1445，绕 +y 的 `caster_roll` 铰，胶囊轮胎 r=0.0125。
- `wheel_L/R`：轮心 `y=±0.1175, z=0.035805`，`wheel_*_spin` 绕 +y，胶囊轮胎 r=0.035805、半宽 0.00788。
- `susp_L/R`：OOMWOO 无被动悬挂，车轮与 chassis 刚性固连。为满足契约名称表，在车轮下挂一个无碰撞小标记体，`susp_*` 是无 range 的阻尼占位滑移（damping=1000），**不承载、不参与物理**；判定用的 `susp_range_m` 在包装层置 1 m，避免把 0 行程误报成悬挂触底。
- 执行器：`wheel_L/R` 力矩电机，`gear=1`，`forcerange=±0.5 N·m`（公开值）。

### 5.2 自检 A1–A5

Windows 每次运行前由 `run_cases` 调 `model_checks.run_checks`，本地复核输出：

```text
A1 True 质量 2.902000 vs 台账 2.902000，相对偏差 1.53e-16
A2 True CoM [0.00634 0 0.046669] vs 台账，范数差 0.000 mm
A3 True xx/yy/zz 相对偏差 1e-11 量级
A4 True 两轮心对称、轴心 x≈0、z=R，均 0.000 mm
A5 True XML 与 t=0 位姿均为单位位姿
```

模型 sha256：`a74f6da2f9e80c2f5430ef9d52fb9a192cd2b1aa43d131667aee4db5c6e99ee8`。

### 5.3 卡在哪 / 下一步

三处试跑补丁（都写在 `scripts/run_oomwoo.py`，没有改上游 `model_checks.py`）：

1. `body_length()` 只认 `chassis_*` 的 **box** 几何，圆形壳体没有 box；包装层按 cylinder 直径求车身长。
2. `chassis_min_z()` 用包围球下界，对圆柱会给出远低于真实底面的值；包装层按 cylinder 底面求。
3. `susp_L/R` 的“0 行程固定铰”在 MuJoCo 里不能写 `range="0 0"`（要求下界 < 上界），而且限位是软约束，实测冲击下可穿透 3–6 mm；本轮改成无 range 的阻尼占位体，并在判定参数里把行程置 1 m。

三步内可修：

1. `model_checks.body_length`/`chassis_min_z` 按 geom 类型分支（cylinder→2r / z−halfheight），删掉包装层补丁。
2. 契约允许“无悬挂机型”不建 `susp_*`，或给出 `rigid: true` 与名称表的条件分支；不要让用户为了过名称检查去造一个假铰。
3. 若后续拿到悬挂力–位移曲线，再把占位体换成真实 spring/damper，并重跑 A4 与台阶工况。

## 6. 第 4 步：工况 → runner → judge

### 6.1 工况配置

| case_id | 场景 | 高度 | 限扭 | 配置 sha256 | scenario_xml_sha256 |
| --- | --- | ---: | ---: | --- | --- |
| `oomwoo_flat` | 平地直行 | — | 0.5 N·m | `cd037cbd…47f4` | `436d2ba7…174e` |
| `oomwoo_step10` | 正向台阶 | 10 mm | 0.5 N·m | `a6851b82…dfdb` | `32a11103…e717` |
| `oomwoo_step10_lowtorque` | 正向台阶（预期失败） | 10 mm | 0.15 N·m | `e71462d8…2972` | `32a11103…e717` |
| `oomwoo_step20_casterblock` | 正向台阶（几何门） | 20 mm | 0.5 N·m | `0916fb11…1cd318` | `e2bf52c7…487a` |

台阶由 `run_cases.build_scenario_xml` 注入，注入后的 XML hash 记在 `run.json.scenario_xml_sha256`。所有 step 案例用 `edge_radius_m=0`：见 §7 的“台阶注入降高”缺陷，带 R3 时实际平台只有 7 mm，会把 10 mm 工况偷偷改成 7 mm。

### 6.2 Windows 结果（SHA 24f7325，`--repeat 2`）

| case_id | status | passed | failure_primary | failure_flags | t_trigger s | t_climb s | advance m | torque_max N·m | contact_max N |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `oomwoo_flat` | ok | 1 | — | — | 0.002 | — | 1.119325 | 0.012055 | 18.93 |
| `oomwoo_step10` | ok | 1 | — | bottom_out; torque_limit; slip | 4.906 | 0.288 | 1.169351 | 0.500000 | 230.38 |
| `oomwoo_step10_lowtorque` | ok | 0 | stall | bottom_out; stall; torque_limit; slip; timeout | 4.952 | — | 0.000114 | 0.150000 | 39.51 |
| `oomwoo_step20_casterblock` | invalid | — | — | no_contact | — | — | — | — | — |

观测解读（只写观测，不写判据结论）：

- **平地直行**：`outcome = cleared`。左右轮速与车身速度同源，8 s 前进 1.119 m，pitch/roll 峰值为 0.0002°/0.0000°，无打滑/无托底标记。轮端扭矩 0.012 N·m，说明该配置下平地阻力很小。
- **10 mm 台阶**：`outcome = cleared`（仅此模型/此配置）。爬升耗时 0.288 s，恢复前进 0.168 s；轮端扭矩到 0.5 N·m 上限（`torque_limit`），前缘法向力峰值 230 N，出现 `bottom_out` 与 `slip` 诊断。没有把它写成“能过 10 mm”的结论。
- **10 mm + 0.15 N·m**：`outcome = blocked`，`failure_mode = stall`。轮子接触台阶后 0.0001 m 内停住，扭矩长期贴 0.15 N·m 上限，8 s 窗口超时；这是预期失败算例，失败分类命中 `stall`。
- **20 mm 台阶**：`outcome = invalid`，`failure_reason = no_contact`。车头从动轮（r=12.5 mm，定高）和刚性壳体先于驱动轮接触台阶立面，驱动轮始终没有 `wheel--step` 接触，judge 不给判定。这不是“过不去”的结论，是**模型缺少从动轮抬升/保险杠柔性**导致的无效工况。
- **30° 斜面静置**：见 §6.3，两个变体都 `invalid`。

### 6.3 30° 斜面（runner 不支持，单独观测）

契约 `scenario.kind` 只有 `flat`/`step`，runner 没有斜面注入；judge 的平地段还要求车身速度贴近指令速度，静置斜面必然 `invalid:not_settled`。因此新增 `scripts/slope_hold.py`：不改几何，把重力绕 +y 转 30°（`g=(g·sin30, 0, −g·cos30)`），机器人仍站水平面；对刚体静力学这与 30° 斜面等价。无驱动，10 s，跑两个变体：

| 变体 | 做什么 | drift | 残余速度 | outcome | invalid_reason |
| --- | --- | ---: | ---: | --- | --- |
| `free` | 按模型原样，无驱动、无驻车 | **89.516 m** | 12.116 m/s | invalid | `no_drivetrain_holding_model` |
| `locked` | equality 锁住左右轮 + 从动轮转角，代表理想驻车 | **0.023014 m** | 0.002092 m/s | invalid | `creep_baseline_exceeded` |

观测：

- `free` 直接滚下坡，10 s 走 89.5 m。模型里只有轮轴 `damping=0.0005 N·m·s` 和 `armature=5e-5`，**没有减速箱静摩擦/自锁/驻车**；这不是“斜面站不住”的物理结论，是缺物理。
- `locked` 锁轮后仍在 10 s 内漂 23 mm、残余 2.09 mm/s，超过“无驱动 10 s 漂移 0.5 mm / 残余 1 mm/s”红线。轮速为 0，说明不是滚动，而是软接触/摩擦锥在持续切向载荷下的蠕滑。**结论：30° 静置在当前接触参数下不可判**；需要按斜面载荷重新做蠕滑基线，或收紧 `solref`/改用椭圆锥后重跑。
- 这两个变体同机重复 2 次，`timeseries.csv` 的 sha256 逐位一致。

### 6.4 蠕滑基线（每批次先跑）

runner 在每个 case 前做 1 s 稳定 + 10 s 无驱动静置，记 `drift_m` 与末 0.5 s 残余速度。Windows 四个配置的结果一致：

```text
drift = 0.0054156 mm (5.4156e-06 m)
residual = 0.0000 mm/s
redline = False
```

远低于 1 mm/s 与 0.5 mm 红线，因此**没有**触发 1 ms/0.5 ms 降档，不产生双档同报。斜面工况的 `locked` 变体则是 23 mm/2.09 mm/s，按同一红线判 `invalid`，见 §6.3。

### 6.5 一致性

| 配置 | r1 timeseries sha256 | r2 timeseries sha256 | 逐位一致 |
| --- | --- | --- | --- |
| `oomwoo_flat` | `66FA8CAE…7370` | `66FA8CAE…7370` | 是 |
| `oomwoo_step10` | `C402014F…4463` | `C402014F…4463` | 是 |
| `oomwoo_step10_lowtorque` | `E64461B9…06F3` | `E64461B9…06F3` | 是 |
| `oomwoo_step20_casterblock` | `9301AADF…D122` | `9301AADF…D122` | 是 |
| `slope free` | `6F1B77A8…5360` | `6F1B77A8…5360` | 是 |
| `slope locked` | `C5DC4071…8651` | `C5DC4071…8651` | 是 |

`run.json.repeat.consistent` 全部为 `true`。同配置重复两次逐位一致，符合任务要求。

跨机器对照：Mac 与 Windows 用同一模型/配置跑 `oomwoo_flat`，timeseries sha256 不同（Mac `d5a666da…8d7b`，Windows `66FA8CAE…7370`），但关键指标差 1.2e-5 m（advance 1.119338581 vs 1.119325082）。这是不同 CPU/SIMD 路径的浮点差异，不是配置错误。**跨平台不能声称逐位一致**；同机重复的逐位一致成立。

## 7. 卡点清单与三步内修法

按“影响结论的程度”排序。

### A. 无 stock 整机 STEP → 整机质量属性不可推（最高）

1. 从 `Top_Assembly_110926.f3z` 用 Fusion 360 导出 STEP，或请维护者补 `designs/one/stock/`；记录文件 sha256。
2. 用 `scripts/step_mass_properties.py` 跑整机，替换 `chassis` 柱体假设与 `com.chassis.*`/`inertia.chassis.*`。
3. 补 z_cg 实测（三点称重/倾斜法），把整机结论从 `mechanism` 逐行放行。

### B. 单张台账不能装两个机型

`model_checks.check_ledger_against_xml` 只解析 xpath 的 `:` 后半段，**不校验文件名**；同一张 `docs/参数溯源.csv` 里 prototype 与 oomwoo 的同名 `param_id` 会互相覆盖/比对失败，而且 prototype 行会被拿去和 oomwoo.xml 的数值比。本轮用独立台账 `docs/试跑/参数溯源-oomwoo.csv` + 包装层注入绕开，代价是“唯一台账”契约被破坏。

三步内修：

1. 给 `run_cases.py` 加 `--ledger` 参数，默认仍是 `docs/参数溯源.csv`。
2. 台账增加 `model` 列，或 `check_ledger_against_xml` 解析 `:` 前的文件名并只比同模型的行。
3. 合并两套行后重跑 A1–A5 与四个工况。

### C. `model_checks` 假设“车身是 box、悬挂有行程”

现状：`body_length()` 只认 box，圆壳机型直接抛错；`chassis_min_z()` 用包围球，圆柱底盘给出远低于真实底面的值；`susp_*` 的 0 行程在 MuJoCo 里不可表达（`range` 必须下界<上界，限位是软约束）。本轮三个 wrapper 补丁绕开。

三步内修：

1. `body_length`/`chassis_min_z` 按 geom 类型分支（cylinder/box/sphere/capsule）。
2. 名称表允许“无悬挂机型”省略 `susp_*`，或在契约里加 `suspension: none|passive` 枚举。
3. 删掉 `scripts/run_oomwoo.py` 的补丁，直接跑上游 `run_cases.py` 验证。

### D. 台阶注入把平台降低了 `edge_radius`

`build_scenario_xml` 对 box 取 `box_h = height − radius`，再把一个半径 R 的整根圆柱横放在顶面。结果是顶面平台高度变成 `height − radius`（R3 时 10 mm 变 7 mm），不是“平顶 + 圆前缘”。本轮把 `edge_radius_m` 设为 0 绕开；这会改变棱边几何，必须在报告里标明。

三步内修：

1. box 高度取 `height`，顶面在 `height`；圆角只加在前缘（半圆柱/胶囊或一段圆弧），不要横贯整个顶面。
2. 加单元断言：注入后平台顶面 z 必须等于 `height`，且 `top_width` 段是平面。
3. 用 10/20 mm 两个工况核对 `t_climb` 与平台高度，再恢复 R3 供接触敏感性对照。

### E. 车头从动轮/刚性保险杠先于驱动轮接触

OOMWOO 的从动轮在车头 +0.1445 m，r=12.5 mm，定高铰；壳体离地 12.5 mm。任何 >12.5 mm 的台阶都会先撞从动轮/壳体，驱动轮根本接触不到台阶（20 mm 工况 `no_contact`）。真实机器靠从动轮抬升/保险杠柔性/壳体前倾越过，本模型都没有。

三步内补：

1. 给从动轮加竖向滑移 + 弹簧（行程/刚度【缺失】，先用假设值并标 工程假设），允许它被台阶抬起。
2. 保险杠做成独立柔性体（弹簧+阻尼）或至少把前缘碰撞几何放到轮心高度以下，别让刚性圆柱直接挡在 20 mm 立面上。
3. 重跑 10/20 mm，确认 `wheel--step` 先接触，再谈 `bottom_out`/`stall` 分类。

### F. 契约没有斜面/静置工况

`scenario.kind` 只有 `flat|step`；runner 永远给驱动；judge 平地段要求速度贴近指令。静置斜面只能另写脚本观测，不能走判定。

三步内补：

1. 契约加 `scenario.kind="slope"`（角度、静置/驱动模式）或加 `drive.mode="none"`。
2. judge 加 `hold` 判据：漂移/残余速度/法向力分布，不套用平地 settle 检查。
3. 用 30° 的 free/locked 两个变体做回归，并补斜面载荷下的蠕滑基线。

### G. `slip_ratio` 分母只用轮速，近零轮速时数值爆炸

`judge._slip_max` 用 `|v_wheel − v_body| / max(|v_wheel|, ε)`。台阶接触瞬间轮速接近 0、车身还在动，比值可以到 78–273（本轮 step10 曾出现 78），既不能当物理打滑，也会把诊断列污染。

三步内修：

1. 分母改成 `max(|v_wheel|, |v_body|, ε)`，或改用绝对滑移速度 `|v_wheel − v_body|`。
2. 同时输出相对/绝对两个量，阈值分别给。
3. 用 step10 的时程重算，确认峰值落在 0–1 的物理区间。

### H. 跨平台不是逐位一致

同机 `--repeat 2` 逐位一致；Mac vs Windows 的 timeseries hash 不同，指标差 1.2e-5 m。若项目要求“跨机逐位”，需要固定 CPU/编译选项或改用语差比较；当前契约只要求同配置重复两次，本轮满足。

## 8. 双机执行记录（命令原文）

### 8.1 Windows（只跑已推送提交）

```powershell
Set-Location E:\mujoco-robot-vacuum
git fetch origin dryrun/oomwoo-step
git worktree add --detach .tools\worktrees\oomwoo-step 24f73251d02e79363dbafb8b6c34c56cd09a7538
Set-Location .tools\worktrees\oomwoo-step
git rev-parse HEAD    # 24f73251d02e79363dbafb8b6c34c56cd09a7538
git status --short    # 空
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe -V   # Python 3.13.1
E:\mujoco-robot-vacuum\.venv\Scripts\python.exe -c "import mujoco,numpy;print(mujoco.__version__, numpy.__version__)"  # 4.0.1 2.5.5
```

```powershell
& E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\run_oomwoo.py --config cases\oomwoo_flat.json --out outputs\oomwoo-flat-win --repeat 2
& E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\run_oomwoo.py --config cases\oomwoo_step10.json --out outputs\oomwoo-step10-win --repeat 2
& E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\run_oomwoo.py --config cases\oomwoo_step10_lowtorque.json --out outputs\oomwoo-step10lt-win --repeat 2
& E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\run_oomwoo.py --config cases\oomwoo_step20_casterblock.json --out outputs\oomwoo-step20cb-win --repeat 2
& E:\mujoco-robot-vacuum\.venv\Scripts\python.exe scripts\slope_hold.py --model models\oomwoo.xml --out outputs\oomwoo-slope30-win --repeat 2
```

输出路径（Windows，gitignored）：

- `outputs\oomwoo-flat-win\{run.json, summary.csv, stdout.log, oomwoo_flat[_r2]\timeseries.csv}`
- `outputs\oomwoo-step10-win\…`
- `outputs\oomwoo-step10lt-win\…`
- `outputs\oomwoo-step20cb-win\…`
- `outputs\oomwoo-slope30-win\{slope.json, free_r1|free_r2|locked_r1|locked_r2\timeseries.csv}`

### 8.2 Mac（编辑、STEP 推导、提交）

```bash
cd /Users/liucong/orca/workspaces/mujoco_/oomwoo-step
/Users/liucong/cad-scratch/venv/bin/python scripts/step_mass_properties.py …  # 见 §3.1
git add … && git push origin dryrun/oomwoo-step
```

Mac 只做编辑、STEP 质量属性、模型/台账生成与提交；MuJoCo 本地预检用同一份 4.0.1，但报告数字以 Windows `24f7325` 为准。

## 9. 产物清单

| 路径 | 说明 |
| --- | --- |
| `models/oomwoo.xml` | OOMWOO MJCF 模板，`${}` 参数注入，头部含 machine/method/source |
| `params/oomwoo.json` | 参数集（`config_id=oomwoo`），每个值带六值标签与 ref |
| `cases/oomwoo_flat.json` | 平地直行 |
| `cases/oomwoo_step10.json` | 10 mm 台阶 |
| `cases/oomwoo_step10_lowtorque.json` | 10 mm + 0.15 N·m 预期失败 |
| `cases/oomwoo_step20_casterblock.json` | 20 mm 几何门（预期 no_contact） |
| `cases/_runner_oomwoo.json` | 试跑 runner 常量（只放宽悬挂触底诊断） |
| `scripts/step_mass_properties.py` | STEP B-rep 质量属性 |
| `scripts/run_oomwoo.py` | 复用 `run_cases.py`，注入 oomwoo 台账与几何补丁 |
| `scripts/slope_hold.py` | 30° 等效斜面静置观测 |
| `docs/试跑/step-质量属性-oomwoo.csv` | 部件级汇总（带 generated_by/input_sha256） |
| `docs/试跑/step-质量属性-逐实体-oomwoo.csv` | 逐实体明细（轮实体 71.61×15.76 mm） |
| `docs/试跑/参数溯源-oomwoo.csv` | 本机型 9 列台账；因 §7-B 单独存放 |

## 10. 未覆盖 / 不得引用

- 不给出“通过高度”“最大可越障高度”或任何判据结论；`cleared` 只对应列出的配置。
- 没有本机实测：质量分项来自作者标注，轮径/轮宽来自第三方扫描件；z_cg、摩擦、接触刚度、减速箱静摩擦、悬挂（无）、保险杠柔性都缺。
- `condim=3`，未建模滚阻/扭转摩擦；`solref/solimp` 待标定。
- 没有整机 stock STEP，`chassis` 仍是均匀柱体，惯量偏保守/偏大未知。
- 20 mm 工况 `invalid` 是模型几何门造成的无效数据，不是“过不去”的结论。
- 30° 斜面 `invalid` 是缺传动系保持 + 软接触蠕滑，不是“斜面站不住”的结论。
- 跨 Mac/Windows 非逐位一致；定量对比要用容差，不能拿单次 hash 当复现证据。
