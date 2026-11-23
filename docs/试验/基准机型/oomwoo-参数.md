# oomwoo 参数与准入核查

- 编制日期：2026-11-22
- 定位：**下游消费者**。不重复推导；对上游尺寸表做 S17 四项准入核查，把可入台账的值与【缺失】分开。
- 标签口径：文档/BOM 直接给出的数 →【公开参考】；我们从 3D 几何自己推算且四项齐 →【图纸推算】；缺一项 →【工程假设】；推不出 →【缺失】。
- **本文件没有【本机实测】项。**

## 1. 来源与版本

| 来源 | rev | 用途 |
|---|---|---|
| `makerspet/oomwoo` | `0218857b2ecc53fb8e289b097b3bdf7a9e184386` | BOM、设计文档、架构、part-specs |
| `makerspet/oomwoo-one` | `a630d1c77255072d280a2a41a7a2bd1a1c98cadd` | URDF/Gazebo；整机几何与占位质量 |
| `makerspet/oomwoo-cad` | `266210a47cab931c5891a07c9a29d48388a54b0c` | `lib/` 零件 STEP；agentic 实验整机 STEP |
| 上游尺寸表（组件） | `docs/基准机型/oomwoo-drive-wheel-dimensions.md`（已入库，随本 PR） | 驱动轮轮体 B-rep 质量属性 |

> 每条 `ref` 的格式：`machine=oomwoo; source=…; retrieved=2026-11-22; rev=<sha>#<path>（<节>）`。有 `rev` 才写 `path`；不写行号。

## 2. 参数总表（只列可追溯值）

| `param_id` | 值 | 单位 | 标签 | 来源（`source=…; retrieved=…; rev=…`） | 备注 |
|---|---:|---|---|---|---|
| `oomwoo.body_diameter` | 349 | mm | 公开参考 | `source=oomwoo docs/ARCHITECTURE.md §4/§5.1; retrieved=2026-11-22; rev=0218857#docs/ARCHITECTURE.md`；`source=oomwoo-one urdf/params.xacro; rev=a630d1c#urdf/params.xacro` | 文档写“约 349 mm 圆体基线”，URDF `base_diameter=0.349`；是设计基线，不是实测 |
| `oomwoo.body_height` | 95 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro 顶部注释; rev=a630d1c#urdf/params.xacro` | 注释给“~95 mm 含 LiDAR 塔”；同文件几何推算为 97 mm（79 + 18），冲突见 §4 |
| `oomwoo.wheel_track` | 235 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro; rev=a630d1c#urdf/params.xacro` | 注释称“measured wheel track 235 mm”；同文件 bridge 常量 233 mm，差 2 mm |
| `oomwoo.wheelbase` | 144.5 | mm | 公开参考 | `source=oomwoo-one urdf/robot.urdf.xacro caster_joint; rev=a630d1c#urdf/robot.urdf.xacro` | 由 `base_diameter/2 − caster_inset = 174.5 − 30` 推算；定义是驱动轮轴→从动轮中心 |
| `oomwoo.hub_z` | 34.0 | mm | 公开参考 | `source=oomwoo-one urdf/robot.urdf.xacro wheel_joint; rev=a630d1c#urdf/robot.urdf.xacro` | 轮心高度 = `wheel_diameter/2` = 34 mm；与 `lib` STEP 的 35.805 mm 冲突 |
| `oomwoo.r_wheel` | 34.0 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro wheel_diameter=0.068; rev=a630d1c#urdf/params.xacro` | URDF 设计值；BOM 对应 Roborock S5 Max 模块，第三方实测轮径 71.5 mm（半径 35.75），见 §4 |
| `oomwoo.caster_diameter` | 25 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro caster_diameter=0.025; rev=a630d1c#urdf/params.xacro` | URDF 把脚轮建成 25 mm 球；实物是推入式球/滚轮，外形约 46×52 mm（商品页转述，未入台账） |
| `oomwoo.com_x` | +2.2 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro 注释 “CoM = +2.2 mm”; rev=a630d1c#urdf/params.xacro` | 只给 x；按同一 URDF 质量/位置复算为 +6.19 mm，差 4.0 mm，见 §4。**不得当整机质心** |
| `oomwoo.i_gear` | 65.36 | 1 | 公开参考 | `source=oomwoo contributions/part-specs/IKsares/drive-wheel/README.md §5; rev=0218857#contributions/part-specs/IKsares/drive-wheel/README.md` | 第三方对 aftermarket 模块的齿数实测；同文另列 ~190:1 的旧推算，冲突见 §4 |
| `oomwoo.T_wheel` | 0.5 | N·m | 公开参考 | `source=oomwoo-one urdf/params.xacro motor_stall_torque=0.5; rev=a630d1c#urdf/params.xacro` | 这是 URDF 的 joint `effort` 上限，不是实测轮端扭矩；与第三方推算 1.14–2.80 冲突，见 §4 |

## 3. 准入核查

### 3.1 上游组件尺寸表（驱动轮轮体）

表：`docs/基准机型/oomwoo-drive-wheel-dimensions.md`（已入库，随本 PR）
表头声明（2026-11-23 复核）：`generated_by=script@32faa7d…`、`table_rev=0b73eda…`（尺寸表 CSV 的 blob sha，**非 commit**；表头已显式注明）、`input_sha256=101bd1ef…`、`method=brep_exact`、`env=Python 3.13.18/gmsh 4.15.2/NumPy 2.5.5`。表本体在本分支已入库（rebase 后的表提交为 `3ae9af8`，注记随本 PR 最新提交；具体 SHA 以 PR head 为准）。

| S17 项 | 核查结果 | 证据/缺口 | 判定 |
|---|---|---|---|
| ① 推导脚本 | 有 | `step_component_properties.py` 在 `keylliucong/oomwoo-baseline-params@32faa7d` 中存在（rebase 后；旧记录 `bdf5be2`），并随表提交推送 | 通过 |
| ② 输入 `sha256` | 有 | 按 `oomwoo-cad@266210a:lib/roborock/OOM-W01-drive-wheel-assembly.stp` 重算：`101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2`，829,986 bytes | 通过 |
| ③ 输出尺寸表 | 有 | 表在 `keylliucong/oomwoo-baseline-params` 已入库、引用可解析（具体 SHA 以 PR head 为准）；表头 `table_rev=0b73eda` 已注明是 CSV 的 blob sha、**非 commit** | 通过 |
| ④ 运行环境声明 | 有 | 解释器/库版本、OCC 由 gmsh 内置、`brep_exact`、无 mesh、`chord_tol/angle_tol=N/A` | 通过 |
| 附加：mesh 豁免 | 不适用 | 方法为 B-rep 精确积分，未导出 mesh；没有“漂移÷容差”可算 | 不适用 |

**结论**：S17 四项齐备且可复核（脚本 @32faa7d、输入 sha256 已重算、表已入库、环境已声明）。几何量可记【图纸推算】；质量因 STEP 无材料密度、ρ 是显式假设，仍记【工程假设】。表头 `table_rev` 是 CSV 的 blob sha、**非 commit**，已显式注明；这是内容寻址的写法，不是缺陷，不影响四项判定。

### 3.2 组件值（临时，待表入库后复核）

| `param_id` | 值 | 单位 | 当前标签 | 准入后标签 | 备注 |
|---|---:|---|---|---|---|
| `oomwoo.r_wheel_lib_step` | 35.805 | mm | 图纸推算 | 图纸推算 | B-rep 包围盒 71.6099568158 mm / 2；与 IKsares 实测 71.5 mm 吻合；无实测交叉校核，止于 sensitivity |
| `oomwoo.wheel_width_lib_step` | 15.760 | mm | 图纸推算 | 图纸推算 | 沿轮轴方向；与 URDF 12 mm 冲突；无实测交叉校核，止于 sensitivity |
| `oomwoo.wheel_mass_lib_step` | 0.0623 | kg | 工程假设 | 工程假设 | 体积 5.6606e-5 m³ × ρ=1100；ρ 是假设，STEP 无材料；S17 几何四项齐，但密度假设仍在 |
| `oomwoo.wheel_Ixx_lib_step` | 2.00e-5 | kg·m² | 图纸推算 | 图纸推算 | 轮体自身、关于自身质心；ρ=1100；不是整机惯量；无实测交叉校核，止于 sensitivity |
| `oomwoo.wheel_Izz_lib_step` | 3.77e-5 | kg·m² | 图纸推算 | 图纸推算 | 同上；无实测交叉校核，止于 sensitivity |

> 这些是**组件级**值，不是整机。不得与 URDF 整机参数拼成一台“第三台机器”。【图纸推算】默认只到 `sensitivity`，没有 `verified_by` 就不进 `quantitative`。

## 4. 冲突清单（两个都列，不给结论）

| # | 量 | 值 A | 值 B | 绝对差 | 处理 |
|---|---|---|---:|---:|---|
| 1 | 驱动轮直径 | 68 mm（URDF） | 71.61 mm（lib STEP）；71.5 mm（IKsares 实测） | 3.6 mm / 3.5 mm | 轮径直接影响 h/R 与轮速；不能混用。基准几何用 URDF 时必须写明 68 mm，敏感性另起一行 |
| 2 | 驱动轮宽度 | 12 mm（URDF） | 15.76 mm（lib STEP） | 3.76 mm | URDF 可能只建接触带；STEP 是轮胎全宽 |
| 3 | 轮距 | 235 mm（URDF） | 233 mm（URDF bridge 常量） | 2 mm | 同一文件两值；标定前不统一 |
| 4 | 轮距（实验件） | 305.05 mm（`device_full.step`） | 235 mm（URDF） | 70.05 mm | 实验件不是正式设计；**不得用 305.05 当基准** |
| 5 | 轴距 | 144.5 mm（URDF 几何） | 140.08 mm（实验件） | 4.42 mm | 实验件摆位不可信；用 URDF 值并注明是推算 |
| 6 | 整机高度 | 95 mm（注释） | 97 mm（79 + 18 几何） | 2 mm | 同一文件不自洽 |
| 7 | 质心 x | +2.2 mm（注释） | +6.19 mm（按同一 URDF 质量/位置复算） | 3.99 mm | 复算假设见上游参数提取；两值都不当整机 CoM |
| 8 | 减速比 | 65.36:1（齿数实测） | ~190:1（旧速度常量推算） | — | 不是同一电机/同一轮径；用 65.36 并注明第三方单件 |
| 9 | 轮端扭矩 | 0.5 N·m（URDF effort 上限） | 1.14–2.80 N·m（第三方推算区间） | — | 0.5 不是实测能力；推算含 η=0.6–0.8 假设 |
| 10 | 整机质量 | 2.937 kg（URDF 参数求和，占位） | BOM 已知件小计 0.843–0.879 kg（不完整） | — | 两者口径不同；**都不能当整机质量** |

## 5. `z_cg` 特别处理

- **基准值：缺失。** 没有正式整机 STEP，没有分件密度/材料表，没有 `oomwoo.com_z` 的 y/z 公开值。
- 实验整机 STEP 的均匀密度体积质心 `com_z = 44.410 mm`（B 系，ρ 无关）**只是均匀密度几何质心**；电池、电机、风机、尘盒/水箱的密度差异未覆盖，且该装配有已知摆位错误。
- **扫描范围未建立**：没有分件质量/密度，无法给出 `z_cg_min/z_cg_max`。报告里只写“扫描范围未建立”，不写单点。
- 因此 `oomwoo.com_z` 台账行为【缺失】，`verified_tol` 留空；不得用 BOM 零件位置或实验件单点凑。

## 6. 覆盖率

按 26 个整机关键参数计（几何 8、质量/惯量 10、悬挂 4、驱动 4）：

| 组 | 有可追溯值 | 缺失/待标定 | 说明 |
|---|---:|---:|---|
| 几何 | 7 | 1 | 缺 `oomwoo.clearance_min`；URDF 的 12.5 mm 只是 `base_link` 底面，不是最低非轮点 |
| 质量/惯量 | 1 | 9 | 只有 `oomwoo.com_x` 注释值；`m`、`com_y/z`、全部惯量缺失 |
| 悬挂 | 0 | 4 | `k/F0/c/travel` 全缺；URDF 没有悬挂自由度 |
| 驱动 | 2 | 2 | 有 `oomwoo.i_gear`、`oomwoo.T_wheel`（后者是占位）；缺 `oomwoo.eta`、扭矩曲线 |
| **合计** | **10** | **16** | 10 个里有 3 个是占位/近似：`oomwoo.body_height`、`oomwoo.com_x`、`oomwoo.T_wheel` |

> 结论：**10 个有公开参考值，16 个缺失或待标定**；其中没有一个是【图纸推算】整机值。组件级驱动轮有 4 项几何值已走【图纸推算】（轮径、轮宽、轮体 Ixx/Izz）；轮体质量因密度假设仍是【工程假设】。
