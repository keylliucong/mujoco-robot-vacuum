# OOMWOO One 全流程试跑报告

- 日期：2026-11-22
- 任务分支：`dryrun/oomwoo-step`
- 基线提交（Windows 实跑）：`__RERUN_SHA__`
- 契约版本：`1.8.1`（v1.8.0 能力声明 + 本轮评审返工；判据集变更见 §0 对照表）
- 本报告随后续文档提交更新；所有仿真数字对应上面的提交，不是报告自身的提交
- 输入：`makerspet/oomwoo-cad@266210a47cab931c5891a07c9a29d48388a54b0c`、`makerspet/oomwoo-one@a630d1c77255072d280a2a41a7a2bd1a1c98cadd`
- 结论口径：本轮**没有判定结论**。只记录 `outcome = cleared / blocked / invalid` 和失败模式，不写“通过高度”或“能过多高”。

## 评审返工对照表（PR #17）

评审结论：**可作 G2 基线，但先返工 4 处**。本表逐条对照；改完后在同一分支 `dryrun/oomwoo-step` 更新 PR #17，未另开 PR。

| # | 评审意见 | 改了什么 | 改在哪个文件哪一行 | 重跑后的结果 |
| ---: | --- | --- | --- | --- |
| 1 | `invalid:never_contacted` 方向反了：驱动轮没碰到就判无效，但 20 mm 例是真实托底受阻 | `t_trigger` 改为任一机体-台阶首次接触；新增 `belly_contact` 失败枚举：窗口内机体已碰台阶、驱动轮始终未接触时判 `blocked`，不再判 `invalid`。`never_contacted` 只保留“全程无任何接触” | `judge.py:170-207`（触发与 `belly_contact`）、`judge.py:258-266`（判负标志）、`cases/oomwoo_step10*.json`/`oomwoo_step20_casterblock.json` 的 `judge.fail_on` 加 `belly_contact` | `oomwoo_step20_casterblock`: `status=ok, passed=0, failure_primary=belly_contact`（旧：`invalid/no_contact`）；`outcome=blocked` |
| 2 | `t_trigger` 以驱动轮接触为计时零点，先托底后爬升的工况窗口系统性偏晚 | `t_trigger` 改为任一机体 geom 与台阶首次接触；新增诊断量 `t_wheel_touch_s`，只记录驱动轮首次接触，不参与窗口起点 | `judge.py:170-196`（触发）、`judge.py:295-300`（metrics）、`scripts/run_cases.py:126-160`（summary 列）、`scripts/run_cases.py:785-814`（判参） | `oomwoo_step10`: `t_trigger=3.976 s`、`t_wheel_touch=4.906 s`、`t_climb=1.188 s`（旧 `t_trigger=4.906`、`t_climb=0.288`，托底延误 0.930 s 现计入窗口）；`step10_lowtorque`: `3.976 / 4.952` |
| 3 | 接触峰值 230 N 不得当物理量 | 保留 `contact_normal_max_n` 仅作同配置相对比较；报告与表注明确写“2 ms 步长尖棱接触的数值峰值，未标定，不具物理量含义”，不得用于核保险杠强度 | 报告 §6.2 表注 1；`scripts/run_cases.py:1258-1262` 的 `data_quality` 增补说明 | 新配置下 `oomwoo_step10` 数值峰值为 **246.39 N**（不是 230.38；改的是模型去掉占位体后的同一算法读数），仍只作相对比较 |
| 4 | 无悬挂机型被逼造 `susp_*` 假铰，且用 1 m 假行程掩盖“没有这个自由度” | 按契约 v1.8.0/ADR-013：模型加 `<custom><numeric name="has_suspension" data="0"/>`，删除 `susp_L/R` 与占位标记体；`susp_*_travel_m` 整列为空、`run.json.columns[...].missing=true`，不进 `failure_flags`；判定侧 `has_suspension=0` 时跳过 `suspension_bottom` | `models/oomwoo.xml:27-29`（能力声明）、`models/oomwoo.xml:74-94`（删假铰）、`scripts/model_checks.py:123-163`（S22 两端一致）、`scripts/run_cases.py:520-530`、`scripts/run_cases.py:590-605`、`scripts/run_cases.py:773-780`、`scripts/run_cases.py:791-814`、`scripts/run_oomwoo.py:87-91`（删 1 m 覆盖） | 四个工况 `susp_travel_max_*` 均空；`failure_flags` 无 `suspension_bottom`；**悬挂判据 A2 对 oomwoo 不可判（无此自由度），不是通过也不是失败**；A1/A3 随占位体删除重算并全过 |


### 评审新增口径（必须写进报告）

| 项 | 写法 |
| --- | --- |
| A. 适用范围硬上限 | `floor_clearance = 12.5 mm`。**h ≲ 12.5 mm：轮主导，本模型成立；h ≳ 12.5 mm：最先碰台阶的是壳体前下缘，本模型没有该处几何（直角圆柱边缘、无倒角、无保险杠柔性），结果只能当“未覆盖此机理”的证据，不能当通过/不通过。** 见 §4.3、§6.2 表注。独立模型 PR #8 的 20/30 mm 终点停在壳体半径处，是同一病的另一种表现。 |
| B. 轮径冲突 | 取 STEP 值 **0.07161 m**（`params.xacro` 0.068 m，差 **5.3%**；轮径对通过高度是一阶）。裁决理由：STEP 是实物轮扫描件且已过 S17 准入四项；`params.xacro` 同文件注释自述轮距才是实测。**冲突不消除**，等试验标定轮径实测（目标 0.2 mm）再裁；该项等级只到 `sensitivity`。见 §4.2。 |
| C. 质心 x 两套归属 | 上游 +2.2 mm、本报告 **+6.345 mm**，差 4.1 mm。差在分件归属：本报告把从动轮 0.05 kg 单独挂在 x=+0.1445 m。**两套分件归属不同，不可比**：本报告不拿 +2.2 mm 作校核，也不把 4.1 mm 当误差；要可比须两边照同一张分件归属表重算。本报告的口径与算式见 §3.3。 |


## 0. 一句话结果

流程走到第 4 步（工况 → runner → judge）并在 Windows 跑完 4 个配置 + 1 个斜面观测，`--repeat 2` 同机逐位一致；第 1 步在**整机质量属性**上卡住：`oomwoo-cad` 没有 `designs/one/stock/`，唯一“整机 STEP”是作者声明有已知设计错误的 `agentic/july-2026/device_full.step`，本轮没有用它。可信 `lib/` STEP 的部件级 B-rep 质量属性已经跑通，但整机 CoM/z_cg、惯量和装甲壳体几何仍只能假设；因此所有批次的 `conclusion_level = mechanism`。评审返工后，20 mm 例由 `invalid/no_contact` 改为 `blocked/belly_contact`（本模型无保险杠柔性/前下缘倒角，该 `blocked` 是下界）；该工况 `h > 12.5 mm`，已超出本模型适用范围，只作“未覆盖此机理”的证据。

| 步骤 | 状态 | 产物 | 卡点 |
| --- | --- | --- | --- |
| 1 STEP → 质量属性 | 部件级完成，整机级卡住 | `docs/试跑/step-质量属性-oomwoo.csv` | 无 stock 整机 STEP；z_cg 无实测 |
| 2 STEP → 几何 | 部件级 + 公开尺寸链完成 | 本报告 §3 | 整机 CAD 全局系不存在 |
| 3 几何 → MJCF | 完成（2 处试跑补丁 + 能力声明） | `models/oomwoo.xml`、`params/oomwoo.json` | `model_checks` 只认 box；无悬挂按 v1.8.0 声明 |
| 4 工况 → runner → judge | 完成 4 配置 + 斜面观测 | Windows `outputs/oomwoo-*-win/` | 契约无 slope 工况；台阶注入降高 |
| 5 双机执行 | 完成 | Windows worktree，SHA `__RERUN_SHA__` | 无 |
| 6 一致性 | 完成 | 同机重复逐位一致 | 跨 Mac/Windows 非逐位一致（记录） |
| 7 报告 | 本文件 | `docs/试跑/` | — |

## 1. 执行位置、环境与命令落点

| 项 | Mac（只编辑/推导/提交） | Windows（只跑已推送提交） |
| --- | --- | --- |
| 位置 | `/Users/liucong/orca/workspaces/mujoco_/pilot-rework`（git worktree） | `E:\mujoco-robot-vacuum\.tools\worktrees\pr17-rework`（git worktree） |
| 提交 | `__RERUN_SHA__`（评审返工提交） | `__RERUN_SHA__`（detached） |
| Python | 3.13.18（CAD venv） | 3.13.1（项目 `.venv`） |
| MuJoCo | 4.0.1（仅本地预检） | 4.0.1 |
| NumPy | 2.5.5 | 2.5.5 |
| CAD 内核 | `cadquery-ocp 7.9.3.1.1`（OCCT 7.9.3）+ `vtk 9.6.2` | 未安装，不跑 CAD |
| 平台 | macOS 27.2.1 arm64 | Windows 11（`platform` 见 `run.json`） |

Windows 使用独立 worktree，避免与其他 worker 共用 `E:\mujoco-robot-vacuum` 工作区；Python 仍调用主目录 `.venv`。每次 `run.json` 记录 `git.commit=__RERUN_SHA__`、`git.branch=HEAD`、`git.dirty=false`。

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

| 量 | 值 | 参数等级 | 结论等级 |
| --- | --- | --- | --- |
| 整机质量 | **2.900 kg** | 公开参考分项 + 加和 | mechanism |
| CoM x（B 系） | **+6.3448 mm** | 工程假设 | mechanism |
| CoM y | **0**（左右对称设 0） | 工程假设 | mechanism |
| CoM z | **46.6767 mm（占位）** | **缺失** | mechanism |
| 关于 CoM 的惯量张量 | `Ixx=0.0231895, Iyy=0.0222461, Izz=0.0427792, Ixy≈0, Ixz=-0.00021485, Iyz≈0` kg·m² | 工程假设 | mechanism |
| 三个主惯性矩 | **0.0222461 / 0.0231872 / 0.0427816 kg·m²** | 工程假设 | mechanism |
| 关于 B 原点 | `Ixx=0.0295078, Iyy=0.0286811, Izz=0.0428959, Ixz=-0.0010737` kg·m² | 工程假设 | mechanism |

读法：`参数等级` 回答“这些数从哪来”；`结论等级` 回答“拿这些数能说到多远”。z_cg 标【缺失】、CAD 全局系标【缺失】，所以整机结论只能是 `mechanism`。这与“质量分项是公开实测”不矛盾：来源硬，但缺口和容差刻度不到定量。

**质心 x 的分件归属（评审新增 C）**：本报告把从动轮 0.05 kg 单独挂在 x=+0.1445 m，算式为

```text
x_com = (2.650 kg × 0.004217 m + 0.050 kg × 0.1445 m) / 2.900 kg = 0.0063448 m
```

上游给 +2.2 mm。两者差 4.1 mm，差在分件归属：若把从动轮按 x=0 计入，本报告会得到 3.85 mm；上游的 +2.2 mm 需要他们那张分件归属表才能复算。因此本报告选择**“两套归属不同，不可比”**：不拿 +2.2 mm 作校核，也不把 4.1 mm 当测量误差；要可比须两边照同一张分件归属表重算。

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
| 驱动轮直径 | **0.071610 m** | 图纸推算（上限 sensitivity） | STEP 轮胎实体；与公开 `wheel_diameter=0.068` 冲突（差 5.3%），按 STEP 取 0.07161；**冲突不消除**，见 §4.4 |
| 驱动轮宽 | **0.015760 m** | 图纸推算 | STEP 轮胎实体；与公开 0.012 冲突，按 STEP |
| 轮距 | **0.235 m** | 公开参考 | `wheel_base`；无整机 STEP |
| 轮心高度 | **0.035805 m** | 图纸推算 | = 轮半径（A4 约束） |
| 轴距（轮轴→从动轮） | **0.1445 m** | 公开参考 | `base_diameter/2 - caster_inset`；从动轮在车头 +x |
| 从动轮半径 | **0.0125 m** | 公开参考 | `caster_diameter=0.025` |
| 壳体柱体 | R=0.1745、h=0.0665、中心 z=0.04575 m | 公开参考 | 无壳体 STEP，用柱体近似 |
| CAD 全局系 → B | **未定义** | 缺失 | 没有整机 CAD 装配，谈不上 yaw/origin |

几何冲突的处理按任务要求：**从 STEP 自己算的以 STEP 为准**。轮径/轮宽与公开值不一致，是因为公开值是 URDF 里的名义值，STEP 是 Roborock 轮的三维扫描件；两者都保留在台账里，模型用 STEP 值并标注冲突。

### 4.3 适用范围硬上限：`h ≲ 12.5 mm`（评审新增 A）

`floor_clearance = 12.5 mm` 是本模型适用范围的硬边界，不是“还能再试试”的余量：

| 台阶高度 | 最先碰台阶的几何 | 本模型能不能用 |
| --- | --- | --- |
| **h ≲ 12.5 mm** | 驱动轮（轮主导） | **成立**：轮缘接触、爬升机理在模型覆盖内 |
| **h ≳ 12.5 mm** | **壳体前下缘**（圆柱直角边缘） | **不成立**：模型没有前下缘倒角、没有保险杠柔性；最先接触处的几何是错的 |

因此：

- **h ≲ 12.5 mm 轮主导、模型成立；h ≳ 12.5 mm 本模型不成立。** 超过 12.5 mm 的结果只能当“**未覆盖此机理**”的证据，不能当“通过/不通过”，也不能外推通过高度。
- 20 mm 工况正落在不成立的一侧。它的 `blocked/belly_contact` 是**本模型几何**下的确定结果；因为模型没有保险杠柔性、没有前下缘倒角，真机可能通过，所以这个 `blocked` 是**下界**，不是结论。
- 独立模型 PR #8 的 20/30 mm 结果终点都停在壳体半径处，是同一个病的另一种表现：轮子还没成为主导接触，壳体几何先决定了结局。

**表注（同样适用于 §6.2 的台阶表）**：表中 `h > 12.5 mm` 的行只用于暴露“壳体前下缘接触”这一未覆盖机理；不得把该行的 `blocked` 读成机型能力。

### 4.4 轮径冲突裁决：取 STEP，但不消除冲突（评审新增 B）

`params.xacro` 给 `wheel_diameter = 0.068 m`，STEP 轮实体外径 **0.07161 m**，差 **5.3%**。轮径对通过高度是一阶量（爬升时轮心抬升 ≈ h），所以这不是可以“两边都记一下”的小冲突。

评审裁决：**取 STEP 值 0.07161 m**。理由：

1. STEP 是实物轮的三维扫描件，不是名义 URDF；
2. 该值已过 S17 准入四项（推导脚本、输入 sha256、逐实体输出表、运行环境声明）；
3. `params.xacro` 同文件注释自述轮距才是实测，轮径是名义值。

但**冲突不消除**：本轮不宣布 0.07161 是“真值”，只宣布“在本模型里用它”。该项参数等级为【图纸推算】，按 S17 上限只到 **`sensitivity`**；等试验标定轮径实测（目标 **0.2 mm**）后再裁。裁决前的任何通过高度都带这个 5.3% 的口径风险。


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
- **无悬挂声明**：模型 `<custom><numeric name="has_suspension" data="0"/>`；不建 `susp_L/R`、不建占位标记体。`susp_*_travel_m` 整列为空（不是 0），`run.json.columns[...].missing=true`，判定侧不产生 `suspension_bottom`。
- 执行器：`wheel_L/R` 力矩电机，`gear=1`，`forcerange=±0.5 N·m`（公开值）。

### 5.2 自检 A1–A5

Windows 每次运行前由 `run_cases` 调 `model_checks.run_checks`（含 S22 能力声明两端一致），本地复核输出：

```text
A1 True 质量 2.900000 vs 台账 2.900000，相对偏差 <1e-12
A2 True CoM [0.006345 0 0.046677] vs 台账，范数差 0.000 mm
A3 True xx/yy/zz 相对偏差 1e-11 量级
A4 True 两轮心对称、轴心 x≈0、z=R，均 0.000 mm
A5 True XML 与 t=0 位姿均为单位位姿
S22 True has_suspension=0，模型内无 susp_* 关节/执行器
```

模型 sha256：`9323a473c6d814a914cfb91fd0ac7772441ccf2b38112d468547df723b8be2e7`。

**悬挂判据 A2 对 oomwoo 不可判（评审返工 4）**：本机型**没有悬挂自由度**，所以这里的“悬挂偏差 A2”既不是通过、也不是失败，而是 **N/A（不可判）**。本轮只保证输出形状不产生 pass/fail：`susp_*` 列整列为空、`missing=true`、`failure_flags` 不含 `suspension_bottom`；“不可判”的判据写法归验收限。注意不要和契约 §1.1 的 **A2（整机 CoM ≤1 mm）** 混淆：契约 A2 仍然适用且通过；评审所说的悬挂 A2 是另一项。

### 5.3 卡在哪 / 下一步

两处试跑补丁（都写在 `scripts/run_oomwoo.py`，没有改上游 `model_checks.py`）：

1. `body_length()` 只认 `chassis_*` 的 **box** 几何，圆形壳体没有 box；包装层按 cylinder 直径求车身长。
2. `chassis_min_z()` 用包围球下界，对圆柱会给出远低于真实底面的值；包装层按 cylinder 底面求。

旧的第三处补丁（造 `susp_*` 占位铰 + 把 `susp_range_m` 置 1 m）已按契约 v1.8.0/ADR-013 **删除**，不再用假值掩盖“没有这个自由度”。

三步内可修：

1. `model_checks.body_length`/`chassis_min_z` 按 geom 类型分支（cylinder→2r / z−halfheight），删掉包装层补丁。
2. 能力声明已按 v1.8.0 落地（S22）；若后续出现“可配置悬挂”，把布尔声明升级为能力取值，而不是回到假铰。
3. 若后续拿到悬挂力–位移曲线，必须先声明 `has_suspension=1` 并给 **>0** 行程，再把真实 spring/damper 加回并重跑 A4 与台阶工况。

## 6. 第 4 步：工况 → runner → judge

### 6.1 工况配置

| case_id | 场景 | 高度 | 限扭 | 配置 sha256 | scenario_xml_sha256 |
| --- | --- | ---: | ---: | --- | --- |
| `oomwoo_flat` | 平地直行 | — | 0.5 N·m | `ed1152f3…` | `5ae2bf40…` |
| `oomwoo_step10` | 正向台阶 | 10 mm | 0.5 N·m | `2d9c4a35…` | `47f461cd…` |
| `oomwoo_step10_lowtorque` | 正向台阶（预期失败） | 10 mm | 0.15 N·m | `06636476…` | `47f461cd…` |
| `oomwoo_step20_casterblock` | 正向台阶（几何门） | 20 mm | 0.5 N·m | `1c0787e7…` | `794630ad…` |

台阶由 `run_cases.build_scenario_xml` 注入，注入后的 XML hash 记在 `run.json.scenario_xml_sha256`。所有 step 案例用 `edge_radius_m=0`：见 §7 的“台阶注入降高”缺陷，带 R3 时实际平台只有 7 mm，会把 10 mm 工况偷偷改成 7 mm。

### 6.2 Windows 结果（SHA `__RERUN_SHA__`，`--repeat 2`）

| case_id | status | passed | failure_primary | failure_flags | t_trigger s | t_wheel_touch s | t_climb s | advance m | torque_max N·m | contact_max N（数值峰值） |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `oomwoo_flat` | ok | 1 | — | — | 0.002 | — | — | 1.119326 | 0.012050 | 18.93 |
| `oomwoo_step10` | ok | 1 | — | bottom_out; torque_limit; slip | 3.976 | 4.906 | 1.188 | 1.165182 | 0.500000 | 246.39 |
| `oomwoo_step10_lowtorque` | ok | 0 | stall | bottom_out; stall; torque_limit; slip; timeout | 3.976 | 4.952 | — | 0.134265 | 0.150000 | 100.85 |
| `oomwoo_step20_casterblock` | ok | 0 | **belly_contact** | belly_contact; retreat; bottom_out; torque_limit; slip; timeout | 3.856 | — | — | -0.000035 | 0.500000 | 211.24 |

**表注 1（接触峰值，评审返工 3）**：`contact_max N` 是 **2 ms 步长下尖棱接触的数值峰值**，不是冲击力；**未标定，不具物理量含义**。它只允许在**同一配置/同一时步**之间作相对比较，不能拿去核保险杠强度、不能当冲量或峰值接触力引用。表里的 246.39 N 不是上一版报告的 230.38 N：模型去掉占位体后同一算法读数变了，但性质仍是数值峰值。

**表注 2（适用范围，评审新增 A）**：`oomwoo_step20_casterblock` 的 `h=20 mm > 12.5 mm`，落在 §4.3 的不成立区。该行的 `blocked/belly_contact` 只说明“本模型几何下壳体前下缘先挡住”，不能当机型通过/不通过；因模型无保险杠柔性、无前下缘倒角，这个 `blocked` 是**下界**（真机可能通过）。

观测解读（只写观测，不写判据结论）：

- **平地直行**：`outcome = cleared`。左右轮速与车身速度同源，8 s 前进 1.1193 m，pitch/roll 峰值为 0.0002°/0.0000°，无打滑/无托底标记。轮端扭矩 0.012 N·m，说明该配置下平地阻力很小。
- **10 mm 台阶**：`outcome = cleared`（仅此模型/此配置）。`t_trigger=3.976 s` 是**车头从动轮首次碰台阶**，`t_wheel_touch=4.906 s` 才是驱动轮首次接触：托底延误 0.930 s 已计入窗口，`t_climb=1.188 s`（旧口径 0.288 s 只从驱动轮接触起算，系统性偏小）。轮端扭矩到 0.5 N·m 上限（`torque_limit`），出现 `bottom_out` 与 `slip` 诊断。没有把它写成“能过 10 mm”的结论。
- **10 mm + 0.15 N·m**：`outcome = blocked`，`failure_mode = stall`。从动轮 3.976 s 先碰台阶，驱动轮 4.952 s 才接触；从触发点到窗口末只前进 0.134 m（旧口径只算驱动轮接触后的 0.000114 m），随后扭矩长期贴 0.15 N·m 上限、8 s 窗口超时。这是预期失败算例，失败分类命中 `stall`。
- **20 mm 台阶**：`outcome = blocked`，`failure_mode = belly_contact`。车头从动轮（r=12.5 mm，定高）和刚性壳体先于驱动轮接触台阶立面（`t_trigger=3.856 s`），驱动轮全程没有 `wheel--step` 接触（`t_wheel_touch` 空）；judge 不再判 `invalid:never_contacted`，而是判 `blocked/belly_contact`。`advance=-0.000035 m` 表示机体被台阶顶回，`retreat` 作为诊断同时命中。**这不是“过不去”的结论**：模型缺少从动轮抬升/保险杠柔性/前下缘倒角，且 `h>12.5 mm` 已超出适用范围，所以这个 `blocked` 是下界，只作“未覆盖此机理”的证据。
- **30° 斜面静置**：见 §6.3，两个变体都 `invalid`。

### 6.3 30° 斜面（runner 不支持，单独观测）

契约 `scenario.kind` 只有 `flat`/`step`，runner 没有斜面注入；judge 的平地段还要求车身速度贴近指令速度，静置斜面必然 `invalid:not_settled`。因此新增 `scripts/slope_hold.py`：不改几何，把重力绕 +y 转 30°（`g=(g·sin30, 0, −g·cos30)`），机器人仍站水平面；对刚体静力学这与 30° 斜面等价。无驱动，10 s，跑两个变体：

| 变体 | 做什么 | drift | 残余速度 | outcome | invalid_reason |
| --- | --- | ---: | ---: | --- | --- |
| `free` | 按模型原样，无驱动、无驻车 | **89.469 m** | 12.100 m/s | invalid | `no_drivetrain_holding_model` |
| `locked` | equality 锁住左右轮 + 从动轮转角，代表理想驻车 | **0.023005 m** | 0.002091 m/s | invalid | `creep_baseline_exceeded` |

观测：

- `free` 直接滚下坡，10 s 走 89.47 m。模型里只有轮轴 `damping=0.0005 N·m·s` 和 `armature=5e-5`，**没有减速箱静摩擦/自锁/驻车**；这不是“斜面站不住”的物理结论，是缺物理。
- `locked` 锁轮后仍在 10 s 内漂 23.005 mm、残余 2.091 mm/s，超过“无驱动 10 s 漂移 0.5 mm / 残余 1 mm/s”红线。轮速为 0，说明不是滚动，而是软接触/摩擦锥在持续切向载荷下的蠕滑。**结论：30° 静置在当前接触参数下不可判**；需要按斜面载荷重新做蠕滑基线，或收紧 `solref`/改用椭圆锥后重跑。
- 这两个变体同机重复 2 次，`timeseries.csv` 的 sha256 逐位一致。

### 6.4 蠕滑基线（每批次先跑）

runner 在每个 case 前做 1 s 稳定 + 10 s 无驱动静置，记 `drift_m` 与末 0.5 s 残余速度。Windows 四个配置的结果一致：

```text
drift = 0.0054156 mm (5.4156e-06 m)
residual = 0.0000 mm/s
redline = False
```

远低于 1 mm/s 与 0.5 mm 红线，因此**没有**触发 1 ms/0.5 ms 降档，不产生双档同报。斜面工况的 `locked` 变体则是 23.005 mm/2.091 mm/s，按同一红线判 `invalid`，见 §6.3。

### 6.5 一致性

| 配置 | r1 timeseries sha256 | r2 timeseries sha256 | 逐位一致 |
| --- | --- | --- | --- |
| `oomwoo_flat` | `6A15DE7C…0649` | `6A15DE7C…0649` | 是 |
| `oomwoo_step10` | `7B4C0508…1243` | `7B4C0508…1243` | 是 |
| `oomwoo_step10_lowtorque` | `09A387C9…EDC0` | `09A387C9…EDC0` | 是 |
| `oomwoo_step20_casterblock` | `1CF10045…439A` | `1CF10045…439A` | 是 |
| `slope free` | `B1F4857D…61D3` | `B1F4857D…61D3` | 是 |
| `slope locked` | `0223350D…F792` | `0223350D…F792` | 是 |

`run.json.repeat.consistent` 全部为 `true`。同配置重复两次逐位一致，符合任务要求。

本轮模型/配置已变（去掉占位体、`has_suspension=0`、`t_trigger` 语义、`fail_on` 加 `belly_contact`），旧版跨 Mac/Windows 对照数字（`d5a666da…` vs `66FA8CAE…`）作废。本轮只做 Windows 同机 `--repeat 2`；Mac 无 MuJoCo 环境，不重跑跨平台。跨平台逐位一致从未被证明，后续若要求，须固定 CPU/编译选项或改用语差比较。

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

现状：`body_length()` 只认 box，圆壳机型直接抛错；`chassis_min_z()` 用包围球，圆柱底盘给出远低于真实底面的值。这两处仍由 `scripts/run_oomwoo.py` 的 wrapper 补丁绕开。悬挂侧已按契约 v1.8.0 解决：`has_suspension=0` 的机型不再被逼造 `susp_*`，`model_checks` 会检查声明与模型两端一致（S22）。

三步内修：

1. `body_length`/`chassis_min_z` 按 geom 类型分支（cylinder/box/sphere/capsule）。
2. ~~名称表允许“无悬挂机型”省略 `susp_*`~~ **已由 v1.8.0 能力声明完成**；后续新增能力按同名机制加 `has_*`。
3. 删掉 `scripts/run_oomwoo.py` 的两处几何补丁，直接跑上游 `run_cases.py` 验证。

### D. 台阶注入把平台降低了 `edge_radius`

`build_scenario_xml` 对 box 取 `box_h = height − radius`，再把一个半径 R 的整根圆柱横放在顶面。结果是顶面平台高度变成 `height − radius`（R3 时 10 mm 变 7 mm），不是“平顶 + 圆前缘”。本轮把 `edge_radius_m` 设为 0 绕开；这会改变棱边几何，必须在报告里标明。

三步内修：

1. box 高度取 `height`，顶面在 `height`；圆角只加在前缘（半圆柱/胶囊或一段圆弧），不要横贯整个顶面。
2. 加单元断言：注入后平台顶面 z 必须等于 `height`，且 `top_width` 段是平面。
3. 用 10/20 mm 两个工况核对 `t_climb` 与平台高度，再恢复 R3 供接触敏感性对照。

### E. 车头从动轮/刚性保险杠先于驱动轮接触

OOMWOO 的从动轮在车头 +0.1445 m，r=12.5 mm，定高铰；壳体离地 12.5 mm。任何 >12.5 mm 的台阶都会先撞从动轮/壳体，驱动轮根本接触不到台阶。20 mm 工况现在判 `blocked/belly_contact`（不再判 `invalid`），判的是“本模型几何下托底受阻”，不是机型能力。真实机器靠从动轮抬升/保险杠柔性/壳体前倾越过，本模型都没有。该机理的硬边界见 §4.3。

三步内补：

1. 给从动轮加竖向滑移 + 弹簧（行程/刚度【缺失】，先用假设值并标 工程假设），允许它被台阶抬起。
2. 保险杠做成独立柔性体（弹簧+阻尼）或至少把前缘碰撞几何放到轮心高度以下，别让刚性圆柱直接挡在 20 mm 立面上。
3. 重跑 10/20 mm，确认 `wheel--step` 先接触，再谈 `bottom_out`/`stall` 分类；在补上倒角/柔性前，`h>12.5 mm` 的结果只作“未覆盖此机理”的证据。

### F. 契约没有斜面/静置工况

`scenario.kind` 只有 `flat|step`；runner 永远给驱动；judge 平地段要求速度贴近指令。静置斜面只能另写脚本观测，不能走判定。

三步内补：

1. 契约加 `scenario.kind="slope"`（角度、静置/驱动模式）或加 `drive.mode="none"`。
2. judge 加 `hold` 判据：漂移/残余速度/法向力分布，不套用平地 settle 检查。
3. 用 30° 的 free/locked 两个变体做回归，并补斜面载荷下的蠕滑基线。

### G. `slip_ratio` 分母只用轮速，近零轮速时数值爆炸

`judge._slip_max` 用 `|v_wheel − v_body| / max(|v_wheel|, ε)`。台阶接触瞬间轮速接近 0、车身还在动，比值可以爆到很大（本轮 `step10_lowtorque` 的 `slip_max_R=186.05`，`step10` 也有 1.009），既不能当物理打滑，也会把诊断列污染。

三步内修：

1. 分母改成 `max(|v_wheel|, |v_body|, ε)`，或改用绝对滑移速度 `|v_wheel − v_body|`。
2. 同时输出相对/绝对两个量，阈值分别给。
3. 用 step10 的时程重算，确认峰值落在 0–1 的物理区间。

### H. 跨平台不是逐位一致

同机 `--repeat 2` 逐位一致。旧版 Mac vs Windows 对照数字随模型变更作废；本轮未重跑跨平台（Mac 无 MuJoCo 环境）。若项目要求“跨机逐位”，需要固定 CPU/编译选项或改用语差比较；当前契约只要求同配置重复两次，本轮满足。

### I. 结构自查 S02 仍失败（观察/CAD 脚本，非本次四项返工）

`scripts/verify_structure.py` 在 Windows 上跑：S01–S22（S12/S20 SKIP）通过，**只有 S02 失败**，命中 `slope_hold.py` 的重力/角度/时长/红线字面量与 `step_mass_properties.py` 的单位换算字面量。两者是**观察脚本与离线 CAD 脚本**，不进入 G2 runner/judge 判定路径；本轮四项返工未要求改它们，故留作已知缺口，不在报告里宣称结构全绿。判定路径（`judge.py`、`run_cases.py`、`run_oomwoo.py`）已无未标注浮点字面量。

## 8. 双机执行记录（命令原文）

### 8.1 Windows（只跑已推送提交）

```powershell
Set-Location E:\mujoco-robot-vacuum
git fetch origin dryrun/oomwoo-step
git worktree add --detach .tools\worktrees\pr17-rework __RERUN_SHA__
Set-Location .tools\worktrees\pr17-rework
git rev-parse HEAD    # __RERUN_SHA__
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
cd /Users/liucong/orca/workspaces/mujoco_/pilot-rework
/Users/liucong/cad-scratch/venv/bin/python scripts/step_mass_properties.py …  # 见 §3.1
git add … && git push origin dryrun/oomwoo-step
```

Mac 只做编辑、STEP 质量属性、模型/台账生成与提交；MuJoCo 本地预检用同一份 4.0.1，但报告数字以 Windows `__RERUN_SHA__` 为准。

## 9. 产物清单

| 路径 | 说明 |
| --- | --- |
| `models/oomwoo.xml` | OOMWOO MJCF 模板，`${}` 参数注入，头部含 machine/method/source；含 `has_suspension=0` 能力声明 |
| `params/oomwoo.json` | 参数集（`config_id=oomwoo`），每个值带六值标签与 ref；轮径冲突未消除 |
| `cases/oomwoo_flat.json` | 平地直行 |
| `cases/oomwoo_step10.json` | 10 mm 台阶 |
| `cases/oomwoo_step10_lowtorque.json` | 10 mm + 0.15 N·m 预期失败 |
| `cases/oomwoo_step20_casterblock.json` | 20 mm 几何门（判 blocked/belly_contact，作下界观测） |
| `cases/_runner_oomwoo.json` | 试跑 runner 常量（`susp_bottom_rel` 保留但对无悬挂机型不生效） |
| `judge.py` | 判定唯一实现；v1.8.1 的 `t_trigger`/`belly_contact`/`t_wheel_touch_s` |
| `scripts/step_mass_properties.py` | STEP B-rep 质量属性 |
| `scripts/run_oomwoo.py` | 复用 `run_cases.py`，注入 oomwoo 台账与两处几何补丁 |
| `scripts/slope_hold.py` | 30° 等效斜面静置观测 |
| `docs/试跑/step-质量属性-oomwoo.csv` | 部件级汇总（带 generated_by/input_sha256） |
| `docs/试跑/step-质量属性-逐实体-oomwoo.csv` | 逐实体明细（轮实体 71.61×15.76 mm） |
| `docs/试跑/参数溯源-oomwoo.csv` | 本机型 9 列台账；因 §7-B 单独存放 |

## 10. 未覆盖 / 不得引用

- 不给出“通过高度”“最大可越障高度”或任何判据结论；`cleared` 只对应列出的配置。
- **适用范围硬上限 `h ≲ 12.5 mm`**：超过 12.5 mm 时最先接触的是壳体前下缘，本模型没有该处几何（直角圆柱边缘、无倒角、无保险杠柔性），结果只能当“未覆盖此机理”的证据，不能当通过/不通过。见 §4.3。
- 没有本机实测：质量分项来自作者标注，轮径/轮宽来自第三方扫描件；z_cg、摩擦、接触刚度、减速箱静摩擦、悬挂（无）、保险杠柔性都缺。
- `condim=3`，未建模滚阻/扭转摩擦；`solref/solimp` 待标定。
- 没有整机 stock STEP，`chassis` 仍是均匀柱体，惯量偏保守/偏大未知。
- **轮径冲突未消除**：`params.xacro` 0.068 m vs STEP 0.07161 m，差 5.3%；本报告取 STEP 值，该项等级只到 `sensitivity`，待 0.2 mm 试验标定轮径后再裁。见 §4.4。
- **质心 x 与上游不可比**：上游 +2.2 mm、本报告 +6.3448 mm，差在分件归属（从动轮 0.05 kg 是否单列在 x=+0.1445）；两套归属不同，不互相校核。见 §3.3。
- `contact_normal_max_n` 是**数值峰值，未标定，不具物理量含义**；只能同配置相对比较，不得用于核保险杠强度。见 §6.2 表注 1。
- **悬挂判据 A2 对 oomwoo 不可判**（无此自由度），不是通过也不是失败；输出 `susp_*` 列为空且 `missing=true`。见 §5.2。
- 20 mm 工况 `blocked/belly_contact` 是模型几何门下的**下界**（真机可能通过），不是“过不去”的结论；且 `h>12.5 mm` 超出本模型适用范围。
- 30° 斜面 `invalid` 是缺传动系保持 + 软接触蠕滑，不是“斜面站不住”的结论。
- 跨 Mac/Windows 非逐位一致；定量对比要用容差，不能拿单次 hash 当复现证据。本轮未重跑跨平台。
