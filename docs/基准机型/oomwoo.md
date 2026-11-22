# 基准机型 oomwoo｜参数来源与模型映射

- 编制日期：2026-11-22
- 基准机型：**makerspet/oomwoo**（Apache-2.0，开源 DIY 扫地机器人）
- 用途：为 `params/oomwoo.json`、`models/baseline.xml` 与 `cases/baseline.json` 提供可追溯的来源清单。所有报告涉及机型时必须写「基准机型 oomwoo」，不得默认代表自家方案。
- 关联文档：[口径裁定记录](../判据/口径裁定记录.md)、[仿真参数表](../仿真参数表.md)、[基准工况与数据缺口](../基准工况与数据缺口.md)

## 1. 来源仓库

| 仓库 | 提交 | 给了什么 | 没给什么 |
| --- | --- | --- | --- |
| [`makerspet/oomwoo`](https://github.com/makerspet/oomwoo) | `0218857b2ecc53fb8e289b097b3bdf7a9e184386` | BOM、`docs/design-document.md`、`docs/ARCHITECTURE.md`、`contributions/part-specs/`、Gazebo 说明 | 没有 CAD/STEP，没有整机参数表 |
| [`makerspet/oomwoo-one`](https://github.com/makerspet/oomwoo-one) | `a630d1c77255072d280a2a41a7a2bd1a1c98cadd` | `urdf/params.xacro`、`urdf/robot.urdf.xacro`、`urdf/inertial.xacro`；尺寸、质量、轮端堵转扭矩、CoM 注释 | 没有可信整机质量属性实测，没有悬挂/摩擦/接触参数 |
| [`makerspet/oomwoo-cad`](https://github.com/makerspet/oomwoo-cad) | `266210a47cab931c5891a07c9a29d48388a54b0c` | `designs/one/stock/` 与 `lib/` 的 STEP；`designs/one/agentic/july-2026/` 是实验快照 | 可信整机壳体几何仍不完整；实验快照不可用（见第 5 节红线） |

`oomwoo-one` 的 URDF 是当前最接近「公开参考」的机构参数来源；本项目的 MJCF 结构模板按它的 body/关节/geom 拓扑简化，数值全部从 `params/oomwoo.json` 注入。

## 2. 直接取自 `urdf/params.xacro` 的值（【公开参考】）

`ref` 写作 `makerspet/oomwoo-one@a630d1c77255072d280a2a41a7a2bd1a1c98cadd#urdf/params.xacro`。

| 键 | 值 | 单位 | 原文/说明 |
| --- | ---: | --- | --- |
| `base_diameter` | 0.349 | m | 轮式机身直径；注释：源自 Proscenic M6 Pro |
| `body_height` | 0.079 | m | 机身顶面高度（不含 LiDAR 塔） |
| `body_height_with_lidar` | 0.097 | m | 含 LiDAR 塔的整机高度 |
| `wheel_diameter` | 0.068 | m | 驱动轮直径 |
| `wheel_width` | 0.012 | m | 驱动轮宽度 |
| `wheel_base` | 0.235 | m | 实测轮距；桥接固件用 0.233 m，注释说差 2 mm 可忽略 |
| `caster_diameter` | 0.025 | m | 前从动支撑直径；万向轮在**前方 +x** |
| `caster_inset` | 0.030 | m | 从动支撑中心到机身边缘 |
| `floor_clearance` | 0.0125 | m | 底盘最小离地间隙 |
| `lower_cylinder_height` | 0.0665 | m | 下部圆柱机身高度 |
| `laser_puck_height` / `laser_puck_diameter` | 0.018 / 0.083 | m | LiDAR 塔 |
| `lower_cylinder_mass` | 2.500 | kg | 下部圆柱机身质量（含电池等，URDF 未拆分） |
| `wheel_mass` | 0.100 | kg | 单只驱动轮质量 |
| `caster_mass` | 0.050 | kg | 从动支撑质量 |
| `laser_puck_mass` | 0.150 | kg | LiDAR 塔质量 |
| `motor_stall_torque` | 0.5 | N·m | 轮端扭矩上限；仅为堵转上限，扭矩-转速曲线未公开 |
| `max_linear_acceleration` | 1 | m/s² | URDF 参数中的最大线加速度 |

## 3. CoM 的公开参考与敏感性

`urdf/params.xacro` 注释给出的全机质心：

- 万向轮在前，支撑多边形从轮轴 `x=0` 延伸到万向轮；**质心必须落在轮轴前方**，否则机身以边缘着地、LiDAR 扫描平面塌到地面。
- 按「质量 × 位置」算得 `x_cg = +2.2 mm`。
- 把 LiDAR 塔居中（相对当前偏置移动 74.5 mm），`x_cg` 变为 `-1.6 mm`。

因此 `x_cg` 对配重/塔位布置极其敏感，是一阶变量；这条已作为附注写入[口径裁定记录 D1](../判据/口径裁定记录.md)。`params/oomwoo.json` 同时保留 `chassis.com_B_x_public=+0.0022` 与 `chassis.com_B_x_lidar_centered=-0.0016` 两个【公开参考】值，供合理性交叉检查；模型内部的 `chassis.ipos_x=-0.0048` 是为了复现 `+2.2 mm` 的【工程假设】偏置（电池/线束未单独建模）。

## 4. 由公开几何按解析式推算的值（【图纸推算】）

`urdf/inertial.xacro` 提供 `solid_box / solid_cylinder / hollow_cylinder / thin_cylindrical_shell / solid_sphere` 等宏，`robot.urdf.xacro` 按 link 调用。MJCF 采用同样形状与同样的解析式，`params/oomwoo.json` 顶层标 `inertia_derivation = "uniform_primitive"`，不手填来源不明的数字。

| 模型键 | 推算方式 | 来源 |
| --- | --- | --- |
| `chassis.radius` | `body_collision_radius = bumper_face_radius - bumper_lead` | `robot.urdf.xacro` 的 base_link |
| `chassis.height_half` / `center_z` | `lower_cylinder_height/2`、`floor_clearance + lower_cylinder_height/2` | `params.xacro` + `robot.urdf.xacro` |
| `chassis.ixx/iyy/izz` | 实心圆柱 `m(3r²+h²)/12`、`m r²/2` | `inertial.xacro` 的 `solid_cylinder_inertia` |
| `wheel.z` | `wheel_diameter/2`（base_link + `d/2 - floor_clearance`） | `robot.urdf.xacro` |
| `wheel.ixx/iyy/izz` | 实心圆柱；绕 +y 轮轴 | `inertial.xacro` |
| `caster.ixx/iyy/izz` | 实心球 `2mr²/5` | `inertial.xacro` |
| `lidar.ixx/iyy/izz` | 实心圆柱 | `inertial.xacro` |

## 5. 红线：`device_full.step` 不能用

`makerspet/oomwoo-cad` 的 `designs/one/agentic/july-2026/README.md` 原文写明：

> **This is not the OOMWOO One design.** It is unreviewed pipeline output from a single revision ("RV02") and has known design errors.

该 README 列出的已知错误包括：侧刷装反/倒置、**万向轮倒装**、LiDAR 偏置、吸尘风机与主刷分处两侧、保险杠外挂、电池仓门比电池小、电池为替代件等。

因此：

- **禁止**用 `designs/one/agentic/july-2026/device_full.step`（约 15.6 MB）做几何、质量属性或接触几何。
- 可信 CAD 只指向 `designs/one/stock/` 与 `lib/` 的 off-the-shelf 件 STEP。
- 若后续使用可信 STEP 推算尺寸，必须按【图纸推算】准入四项：可复跑脚本 + 输入 sha256 + 尺寸表 + 环境声明（含 CAD 内核与 tessellation 容差）。

## 6. 仍是工程假设/待标定/缺失的项

| 项目 | 当前处理 | 标签 |
| --- | --- | --- |
| 驱动轮模块悬挂行程/刚度/阻尼/限位 | URDF 未公开；`params/oomwoo.json` 用竖向 slide + 弹簧表示，值保留工程假设 | 【工程假设】 |
| 前从动支撑的竖向行程 | URDF 是固定球；为允许 10 mm 级门槛顶起加入行程，属结构简化 | 【工程假设】 |
| 轮-地 / 轮-门槛摩擦 | 未公开；起步值 0.8 / 0.8 | 【工程假设】 |
| 接触 `solref` / `solimp` / `condim` | MuJoCo 软接触参数，非物理测量量 | 【待标定】 |
| 整机质量与质心实测 | 只有 link 质量与注释 CoM；没有整机称重/悬挂法结果 | 【缺失】 |
| 整机惯量实测 | 只有解析式推算，没有摆动/扭摆试验 | 【缺失】 |
| 轮端扭矩-转速曲线、限流、减速比、效率 | 只有堵转上限 0.5 N·m | 【缺失】 |
| 轮胎径向/侧向刚度 | 用 MuJoCo 软接触参数替代 | 【待标定】 |
| 可信整机壳体 CAD 几何 | `stock/` 与 `lib/` 尚不构成完整壳体；没有 CAD 级接触几何 | 【缺失】 |
| 编码器 PPR / 轮速传感器 | 本模型不使用编码器，只输出仿真轮速 | 【缺失】 |

## 7. 模型与参数的对应

- `models/baseline.xml`：只写结构（body 树、关节、geom 拓扑、接触对、驱动方式）；不含数值。
- `scripts/build_model.py`：从模板 + `params/<config_id>.json` 生成 `build/models/<config_id>.xml`；生成逻辑可复跑，产物不手工编辑。
- `cases/baseline.json`：`config_id = oomwoo_public_v1`；每个 case 必须与参数集的 `config_id` 一致，否则入口直接退出。
- `run.json`：回读模板 sha256、参数 sha256、生成 XML sha256、逐项参数来源标签、缺失项与阻塞项。

切换机型或参数集 = 换 `params/*.json` 和 `cases/*.json` 的 `config_id`，不重写结构模板。
