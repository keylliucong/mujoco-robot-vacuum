# oomwoo 参数与 #13 模型的对应关系（存档）

- 来源：PR #13 `proto/baseline-cases` @ `bcb478f`（参数文件 head `1a7f5c3` 之后的文档提交），原文件 `docs/基准机型/oomwoo.md`。
- 定位：**只存档参数与模型的对应知识**。#13 的 `models/baseline.xml`、`scripts/build_model.py`、`scripts/run_cases.py` 按 G2 收口决定**不并入 main**（main 以 #15 为唯一实现基线），所以本文件不描述当前可运行的模型。
- 去重说明：原文件的来源仓库、公开参数表和 CoM 敏感性已由本目录的 [`oomwoo-来源.md`](oomwoo-来源.md)、[`oomwoo-参数.md`](oomwoo-参数.md)、[`oomwoo-资产盘点.md`](oomwoo-资产盘点.md) 覆盖；这里只保留原文件独有的模型映射与结构简化部分。路径统一放在 `docs/试验/基准机型/`，不再建第二套 `docs/基准机型/`。

## 1. 参数键到模型构件的映射

| 参数键（`params/oomwoo.json`） | 模型构件 | 说明 |
| --- | --- | --- |
| `chassis.mass` / `chassis.ipos_x` / `chassis.ipos_z` | 机身 `chassis` 的质量与质心 | `ipos_x=-4.8 mm` 是为复现 URDF 注释 `x_cg=+2.2 mm` 的工程假设偏置；电池/线束未单独建模 |
| `chassis.ixx/iyy/izz` | 机身惯量 | 由 `m=2.5 kg`、`r=0.1745 m`、`h=0.0665 m` 的实心圆柱公式推算 |
| `chassis.radius` / `chassis.height_half` / `chassis.center_z` | 机身圆柱几何 | `radius=body_collision_radius`；`center_z=floor_clearance+lower_cylinder_height/2` |
| `wheel.x` / `wheel.track_half` / `wheel.z` | 左右驱动轮安装位 | `z=wheel_diameter/2`；两轮关于机身对称 |
| `wheel.mass` / `wheel.ixx/iyy/izz` / `wheel.radius` / `wheel.halfwidth` | 驱动轮质量、惯量与接触几何 | 轮胎在原模型中用球体近似，轮宽不参与接触；质量属性仍取圆柱值 |
| `susp.*` | 驱动轮竖向滑移悬挂 | URDF 没有悬挂自由度；#13 首版按 0 行程固定铰（`travel=±1 µm`、`stiffness/damping=0`）处理 |
| `caster.x` / `caster.z` / `caster.mass` / `caster.radius` / `caster.ixx/iyy/izz` | 前从动支撑 | URDF 把脚轮建成 25 mm 固定球；质心/惯量按实心球推算 |
| `caster_rear.*` | 后从动支撑 | **工程假设**：URDF 没有后支撑；为数值稳定新增，镜像前支撑 |
| `lidar.*` | LiDAR 塔 | 质量/半径/高度取 URDF；惯量按实心圆柱推算 |
| `drive.torque_limit` | 轮端执行器上限 | 取 `motor_stall_torque=0.5 N·m`，只是堵转上限，不是实测轮端扭矩 |
| `control.*` / `numerics.*` | 批运行控制与数值设置 | 原属 #13 `cases/*.json` 与 `run_cases.py`；在 `params/oomwoo.json` 中保留为带标签的设置项，main 的 #15 入口不读取这些键 |

## 2. 结构简化（均为工程假设）

- **轮胎用球体近似**：接触稳健，不建模轮宽、胎面花纹、轮胎径向/侧向刚度；轮半径、质量、转动惯量仍取公开值或解析推算值。
- **保险杠分片简化为一个圆柱底盘**：保留 `body_collision_radius`；24 片保险杠圆弧没有逐片建模。
- **前从动支撑保留在 +x**：另加后从动支撑 `caster_rear` 用于数值稳定，不是 oomwoo 的公开结构。
- **驱动轮/从动支撑按 0 行程固定铰处理**：首版没有可测弹簧悬挂，A2 记 `na`；悬挂行程、刚度、阻尼、限位需实机试验后启用。
- **台阶/地面由 runner 注入**：结构模板的 `<contact>` 只引用 `floor`/`step`/`step_edge` 名称；flat 工况把台阶放到远处，保证接触对引用始终存在。

## 3. 使用边界

- 本文件只解释 `params/oomwoo.json` 的键为什么这样取；不证明这些值可当实测值。
- 整机质量、质心、惯量、悬挂、摩擦、轮端扭矩-转速曲线的标签仍以 [`docs/参数溯源.csv`](../../参数溯源.csv) 的 `machine=oomwoo` 行为准。
- 若将来要把 oomwoo 接入 main 的 #15 runner，需要新写一个 `machine=oomwoo` 的 MJCF 模板；不能直接把 #13 的 `models/baseline.xml` 当作 main 的基线模型。
