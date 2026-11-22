# oomwoo 数据清点（干跑阶段一）

## 引用核对（摘录说明）

> **来源**：`origin/dryrun/oomwoo`（PR #27），摘录时分支提交 `fb53b53`。本文件只摘文档，**该分支的模型/参数/工况未合并**；main 上的 G2 实现以 #15 `f712289` 为准。

| 文中引用 | main 现状 | 处理 |
|---|---|---|
| 上游 pin：`makerspet/oomwoo@0218857`、`oomwoo-cad@266210a`、`oomwoo-one@a630d1c` | 三个仓库都在仓库外，未入库；与随附 `docs/干跑/证据/sources.txt` 一致 | 只能按 SHA 向持有人索取 |
| `params/oomwoo.json`（`config_id=oomwoo`） | main 的 `params/` 只有 `prototype.json` | 引用核对：此项对应文件在本轮未合并，仅作历史记录 |
| `models/baseline.xml` | 存在，但 main sha256=`153b7697…91d01`，本文证据里是 `ff3dff5d…`（分支改过模型） | 文中「进入模型的量」对应分支模型，不是 main 模型 |
| `docs/参数溯源.csv`（9 列、`machine=oomwoo`） | 存在；含 37 行 `machine=oomwoo`，键名已按 v1.8.1 迁为 `oomwoo.*` 前缀 | 可对上（键名已变） |
| `docs/不确定度预算.csv`（15 列、`status` 三值） | 存在，列数 15 | 可对上 |
| `scripts/model_checks.py`（A1–A5） | 存在 | 可对上 |
| `requirements.lock.txt` | 存在 | 可对上 |
| 「等拿到可信 STEP 后用 `scripts/` 下的推导脚本重新升档」 | main 无可复用的 STEP 质量属性推导脚本 | 引用核对：此项对应脚本在本轮未合并，仅作历史记录 |
| `docs/干跑/证据/*` | 已随本文件一并摘入 | 可对上 |

- 文中的 `公开参考 / 工程假设 / 缺失 / 待标定` 是**参数来源等级**，不是判定等级，按原文保留。
- 生成日期：2026-11-22
- 分支：`dryrun/oomwoo`
- 用途：G2 契约可实现性干跑；本文件只记录**数据能不能拿到**，不把假设写成实测。

## 1. 数据源与 pin

| 仓库 | 用途 | HEAD SHA | 本地路径（仓库外） |
|---|---|---|---|
| `makerspet/oomwoo` | BOM、设计文档、部件实测笔记 | `0218857b2ecc53fb8e289b097b3bdf7a9e184386` | `~/orca/tmp/oomwoo/oomwoo` |
| `makerspet/oomwoo-cad`（原名 oomwoo-one-cad） | CAD / STEP / RV02 报告 | `266210a47cab931c5891a07c9a29d48388a54b0c` | 未完整 clone（见下） |
| `makerspet/oomwoo-one` | URDF / xacro 参数（本轮数值来源） | `a630d1c77255072d280a2a41a7a2bd1a1c98cadd` | 未 clone；按 SHA 引用，见 §3 |

> 两个上游仓库均**未提交**进本仓库；STEP（15.6 MB）与 PDF 不进入本仓库。

**clone 记录**：`oomwoo` 用 `git clone --depth 1`（HEAD `0218857`）。`oomwoo-cad` 与
`oomwoo-one` 首次普通 clone 时，`oomwoo-cad` 在 96 MB 处报
`fetch-pack: unexpected disconnect while reading sideband packet`；改用
`git clone --depth 1 --filter=blob:none --no-checkout` 后两者都成功，HEAD 分别为
`266210a` / `a630d1c`，与 `git ls-remote` 一致。按需 `git show` 读取的输入文件 sha256：

| 文件（`oomwoo-one@a630d1c`） | sha256 |
|---|---|
| `urdf/params.xacro` | `f1bf84a42b7e0db13dd7b50c2b8f44acd39d3a631ae15336c2da18861ef6a817` |
| `urdf/robot.urdf.xacro` | `838e4547227cea447b7c6b65b3de401ef2f2c454e254b255f2d4db47de8bb13c` |
| `urdf/inertial.xacro` | `8a2b5ea273cbddb2a2307df319d2ddeb95a1a92f6d1b36d83b1514bf70d4f778` |

RV02 文件只用于核对“不可用”结论，未做质量属性：

| 文件（`oomwoo-cad@266210a`） | 大小 | sha256 |
|---|---|---|
| `designs/one/agentic/july-2026/README.md` | 4,021 B | `bcfac3b3edc4b1d9108f9407a51610b8e5ab63d55d6b1748fe3ee8abeaaa8edf` |
| `designs/one/agentic/july-2026/device_full.step` | 16,375,631 B | `e1b3453e8eccdf5a5c3baf927bdfe4632348febc19b415786c417caca0295682` |
| `designs/one/agentic/july-2026/OOMWOO_Device_RV02_Report.pdf` | 5,928,217 B | `daaafa111553792a44ef0fd4ea2702be9ba990222be3e0a339cd09329d4a53fe` |

## 2. 来源分级与撤回

| 来源 | 例子 | 处理 |
|---|---|---|
| 仓库直接给的数 | `oomwoo-one/urdf/params.xacro` 的 `wheel_diameter`、`lower_cylinder_mass`、`motor_stall_torque` | 【公开参考】，`ref` 带 `source=` / `rev=` / `retrieved=` |
| 可信 STEP 推算 | `lib/`、`designs/one/stock/` | 本轮**未使用**：没有把 STEP 当质量属性来源 |
| 不可信 CAD 实验件 | `designs/one/agentic/july-2026/device_full.step`、`OOMWOO_Device_RV02_Report.pdf` | **不用**，也不给【图纸推算】 |

### 2.1 来源撤回：RV02 不可用

`oomwoo-cad` 的 `designs/one/agentic/july-2026/README` 原文明确：

> This is **not** the OOMWOO One design. It is unreviewed pipeline output from a single
> revision ("RV02") and has **known design errors**.

已知错误包括侧刷装反、万向轮倒装、LiDAR 偏置、风机与主刷分处两侧、保险杠装在筒身外侧、
电池仓门比电池小。万向轮倒装与风机位置会直接改变质心、支撑多边形和越障接触几何，因此：

- `device_full.step` 与 `OOMWOO_Device_RV02_Report.pdf` **不作为任何参数来源**；
- 本报告不给出 RV02 的质量属性、包围盒或惯量；
- 若后续有人已从 RV02 算过数，按本节视为作废。

## 3. 环境声明

| 项 | 值 |
|---|---|
| 主机 | macOS 27.2.1（arm64） |
| 解释器 | CPython 3.13.18（项目 `.venv/`） |
| MuJoCo | 4.0.1（`mujoco==4.0.1`，与 `requirements.lock.txt` 一致） |
| NumPy | 2.5.5 |
| CAD 内核 | **未使用**（FreeCAD / OCP / cadquery 均未安装、未调用） |
| tessellation | **不适用**（没有对 STEP/mesh 做三角化；无弦高/角度容差） |
| 质量属性算法 | 无 B-rep 质量属性。质量取 URDF/xacro 公开值；轮/球/柱惯量按实心体公式换算；A1–A3 目标是**由同一模型反算的自洽值**，不是独立 CAD 或实测 |

依赖安装命令（本机）：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install mujoco==4.0.1 numpy
```

`requirements.lock.txt` 里的 `glfw` 等仅用于查看器，本轮批运行不需要；未装不影响
`scripts/run_cases.py`。Windows 复跑时按仓库锁文件重建 `.venv`，并在 `run.json` 的
`platform`/`mujoco` 字段留痕。

## 4. 可得性表

| 量 | 值 / 结论 | 能否直接拿到 | 标签 | 依据 |
|---|---|---|---|---|
| 整机外径 | 0.349 m | 是（注释） | 公开参考 | `params.xacro` 注释：forked from Proscenic M6 Pro |
| 整机高 | ≈0.095–0.097 m（含 LiDAR 塔） | 是（注释/尺寸链） | 公开参考 | `params.xacro` + `robot.urdf.xacro` |
| 轮距 | 0.235 m（固件桥接 0.233） | 是 | 公开参考 | `wheel_base` |
| 轴距 | 驱动轮轴 x=0；前从动球 x=0.1445 m | 是（几何链） | 公开参考 | `robot.urdf.xacro` |
| 轮径 | **0.068 m（URDF）/ 0.0715 m（部件实测笔记）** | 有冲突 | 公开参考（冲突未裁决） | `wheel_diameter`；`contributions/part-specs/IKsares/drive-wheel/README.md` |
| 轮宽 | **0.012 m（URDF）/ 0.014 m（BOM 轮胎）** | 有冲突 | 公开参考（冲突未裁决） | `wheel_width`；`BOM.md` |
| 离地间隙 | 0.0125 m | 是 | 公开参考 | `floor_clearance` |
| 整机质量 | 2.9 kg（2.5 筒身 + 2×0.1 轮 + 0.05 万向轮 + 0.15 LiDAR） | 否，拼合值 | 公开参考（分项）+ 加和 | `lower_cylinder_mass`、`wheel_mass`、`caster_mass`、`laser_puck_mass` |
| 质心 x | +2.2 mm（LiDAR 居中时 −1.6 mm） | 否，注释推算 | 工程假设 | `params.xacro` 注释由质量×位置算出；未称重 |
| 质心 y | 0（左右对称假设） | 否 | 工程假设 | 对称性假设 |
| 质心 z | **拿不到** | 否 | **缺失** | 无三点称重/倾斜法数据；模型用 0.04575 m 几何中心占位 |
| 惯量张量 | 无公开值 | 否 | 工程假设 | 实心圆柱/球公式换算，未满足 v1.7.7 图纸推算准入 |
| 轮端堵转扭矩 | 0.5 N·m | 是 | 公开参考 | `motor_stall_torque` |
| 扭矩-转速曲线/限流/减速比/效率 | 拿不到 | 否 | 缺失 | URDF 只给堵转上限 |
| 驱动轮悬挂行程/刚度/阻尼 | 拿不到 | 否 | 工程假设（本轮固定为 0 行程） | URDF 未公开；契约允许首版 0 行程固定铰 |
| 轮-地/轮-门槛摩擦 | 拿不到 | 否 | 工程假设 | 未做斜面法/拉力计 |
| 轮胎径向/侧向刚度 | 拿不到 | 否 | 待标定 | 用 MuJoCo 软接触参数替代 |
| 电池/线束质量分布 | 拿不到 | 否 | 工程假设 | 未拆分；用 `com.chassis.x` 反推公开 CoM |
| CAD 全局系 → B | 无 CAD | 否 | 工程假设（恒等映射） | 未使用 CAD；B≡world≡chassis |

### 4.1 为什么没有【图纸推算】

v1.7.7 要求【图纸推算】齐备四件：推导脚本、输入文件 sha256、输出尺寸表（表头带
`generated_by` / `input_sha256`）、运行环境声明。本轮：

- 没有可信 STEP 输入（RV02 被撤回）；
- 公式换算值虽然可复算，但没有把 xacro 解析成受控输入 + 尺寸表；
- 因此所有公式换算值**按契约降为【工程假设】**，并在 `docs/参数溯源.csv` 的 `ref`
  写明降档原因。

这不是“懒得做”，是**没有可核的输入**。等拿到 `lib/`/`stock/` 的可信 STEP 后，用
`scripts/` 下的推导脚本 + 输入 sha256 + 尺寸表 + 环境声明重新升档。

## 5. 公开来源之间的冲突（未裁决）

1. **轮径 68 mm vs 71.5 mm**：URDF `wheel_diameter=0.068`；`IKsares` 部件实测笔记用
   卡尺量到 71.5 mm 外径（同一驱动轮模块家族）。差 5.1%，对 20 mm 台阶的爬升裕度是
   一阶量。本轮按 URDF 0.068 m 建模，台账注明冲突；未擅自取 71.5 mm。
2. **轮宽 12 mm vs 14 mm**：URDF `wheel_width=0.012`；BOM 轮胎条目写 14 mm 宽。
3. **整机质量**：2.9 kg 是四个分项相加，没有任何一处给出整机称重值；分项是否含电池、
   线束、风机、主刷，URDF 注释未逐项说明。`lower_cylinder_mass=2.5 kg` 自称含电池，
   但“含电池”不等于“含全部”。
4. **质心**：`params.xacro` 注释给 +2.2 mm（LiDAR 居中 −1.6 mm），是质量×位置的
   手算，不是称重；z 向完全没有。

## 6. 本轮实际进入模型的量

- 结构：`models/baseline.xml`（body 树、关节、geom 拓扑、名称表）。
- 数值：`params/oomwoo.json`（`config_id=oomwoo`）。
- 逐值来源：`docs/参数溯源.csv`（9 列，`machine=oomwoo`）。
- 不确定度：`docs/不确定度预算.csv`（15 列，`status` 三值）。
- 质量属性自洽：A1–A5 在 `scripts/model_checks.py`，目标行 `mass.assembly` /
  `com_B_m.*` / `inertia_B.*` 标【工程假设】，是自洽校验，不是独立测量。
