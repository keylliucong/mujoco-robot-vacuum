# oomwoo 3D 资产盘点

- 盘点日期：2026-11-22
- 对象：`makerspet/oomwoo` @ `0218857b2ecc53fb8e289b097b3bdf7a9e184386`；`makerspet/oomwoo-cad` @ `266210a47cab931c5891a07c9a29d48388a54b0c`
- 方法：按上述 commit 读取文件树、文件头/尾、STEP `PRODUCT` 与单位声明；**不推导参数、不跑 MuJoCo**。
- 结论先行：**有全套零件级 3D 扫描数据，但没有可当作 OOMWOO One 正式设计的整机 STEP。** 唯一整机 STEP 是 agentic 实验件（仓库自己声明“不是 OOMWOO One 设计”），只能做几何量级与敏感性；质量、`z_cg`、惯量、悬挂参数不能从它得到可信值。

## 1. 有没有 3D 数据

| 类型 | 是否存在 | 数量/证据 | 说明 |
|---|---|---|---|
| STEP / STP（B-rep） | **有** | `oomwoo-cad` 中 55 个 `.step`/`.stp` | 含 1 个整机实验装配、2 个正式设计链的子装配 STEP、约 50 个外购件/扫描件 |
| IGES / IGS | 无 | 两个仓库都没有 | — |
| STL / DAE / OBJ / glTF / USD / PLY | 无 | 两个仓库都没有 | 不能直接拿 mesh；若需要 mesh，只能从 STEP 自行 tessellate |
| URDF | **不在两个仓库内** | `oomwoo` 只链接到 `makerspet/oomwoo-one` | `oomwoo-one` @ `a630d1c77255072d280a2a41a7a2bd1a1c98cadd` 有 `urdf/*.xacro`；质量是占位值，且没有悬挂自由度 |
| SDF / Gazebo 模型 | 不在两个仓库内 | `oomwoo` 的 `contributions/urdf-gazebo-sim/README.md` 指向 `makerspet/oomwoo_gazebo` | 本仓库没有 `.sdf`/`.world` |
| `docs/design-document.md` | 有 | `oomwoo/docs/design-document.md` | 设计取舍与打印/采购分工；没有整机尺寸表 |
| `docs/ARCHITECTURE.md` | 有 | `oomwoo/docs/ARCHITECTURE.md` | 机体系、约 349 mm 圆体基线；整体直径/高度明确写为 TBD |
| `contributions/part-specs/` | 有 | 多个贡献者的零件规格 | 驱动轮有第三方实测规格；脚轮/连接器部分来自商品页 |
| 原生 CAD（Fusion 360） | 有 | 7 个 `.f3z` + 6 个 `.f3d` | 正式设计链的顶层装配是 `Top_Assembly_110926.f3z`（93 MB）；需 Fusion 360，仓库没有对应整机 STEP 导出 |

## 2. 整机级文件：能不能当基准几何

| 文件 | 格式/单位 | 大小 | 装配关系 | 可分离性 | 判断 |
|---|---|---:|---|---|---|
| `designs/one/agentic/july-2026/device_full.step` | STEP AP214；mm（`SI_UNIT(.MILLI.,.METRE.)`）；B-rep | 15.6 MiB | **无装配树**：整文件只有 1 个 `PRODUCT('COMPOUND')`；63 个 solid，无零件名 | 只能按几何启发式分（触地、薄、圆、位置）；不能按名称分离驱动轮组/车体/悬挂 | **不能当 OOMWOO One 基准几何。** 同目录 README 明示 “This is not the OOMWOO One design”，并列出脚轮装反、侧刷方向错误等已知缺陷 |
| `designs/one/fusion360/Top_Assembly_110926.f3z` | Fusion 360 归档（zip）；原生单位 | 93.2 MiB | **有**完整装配关系（Fusion 原生） | 可在 Fusion 360 中按组件分离 | 是正式设计链的顶层装配；但**没有整机 STEP 导出**，本环境无法直接积分。需要设计方导出 STEP 才能进入 S17 |
| `designs/one/fusion360/STEP/03-01 Motor_Gearbox.step` | STEP AP214；mm；B-rep | 8.7 MiB | **有**：18 个 `PRODUCT` | 可按子装配/零件分离 | 电机/减速箱子装配，不是整机；可用于驱动组质量/惯量的局部参考 |
| `designs/one/fusion360/STEP/03-02 Red_Brush_Gearbox_step.step` | STEP AP214；mm；B-rep | 2.8 MiB | **有**：11 个 `PRODUCT` | 可按子装配/零件分离 | 主刷齿轮箱，与越障无关 |

> `designs/one/stock/` 在本 rev **没有文件**，尽管 `designs/README.md` 说正式设计应放在 `stock/`。这是“没有正式整机 STEP”的直接证据。

## 3. 零件级资产：能分离出什么

| 组 | 可用文件 | 格式/单位 | 装配关系 | 能否分离 | 说明 |
|---|---|---|---|---|---|
| **驱动轮组** | `lib/roborock/OOM-W01-drive-wheel-assembly.stp` | STEP AP242；mm；B-rep + AP242 tessellated 声明 | 1 个 `PRODUCT`，3 个 solid | **能**（单文件就是驱动轮模块；轮体是 tag 3） | 3D 扫描件；读入时 gmsh 报 1 个 unresolved reference，3 个实体均导入；轮体完整，整模块质量/惯量在修引用前不要用 |
| 驱动轮限位/开关 | `lib/roborock/OOM-W01-02-drive-wheel-switch.stp` | STEP；mm | 单件 | 能（单件） | 轮组附属件，不是悬挂弹簧 |
| 脚轮 | `lib/casters/irobot_caster.step` | STEP AP214；mm；SolidWorks 导出 | 单件 | 能（单件） | iRobot 脚轮扫描件；与 URDF 的 25 mm 球不同口径 |
| 车体/上盖/bumper | 无独立文件 | — | — | **不能可靠分离** | 只能从 `device_full.step` 的 63 个 solid 中用几何启发式挑；无名称、无材料 |
| 悬挂件 | 无独立文件 | — | — | **不能分离** | 悬挂在驱动轮模块内部；STEP 是静态外形，没有弹簧/摆臂运动副；URDF 也没有悬挂自由度 |
| 电池 | `lib/roborock/OOM-E01-battery.stp` | STEP；mm | 单件 | 能（单件） | 影响 `z_cg` 的关键件；但无质量/密度 |
| 风机/刷/LiDAR/CM4/CM5/传感器/开关 | `lib/` 其余约 45 个 STEP | STEP AP214/AP242；mm | 多数单件，少数多产品装配 | 能按零件分离 | 都是**外购件**，不是 OOMWOO 自己的车体；CM4/CM5 单文件 62–96 MiB |

### 3.1 整机 STEP 的 63 个 solid 能说明什么

- 63 个 solid 中可识别出两只触地驱动轮（薄、圆、约 69 mm 直径）和一只触地脚轮；这是唯一可靠的“组”分离线索。
- 车体是最大两件（约 355×348×81 mm）的包围盒；但 **bumper、LiDAR 塔、尘盒、电池门** 等都是生成件，且该装配有已知摆位错误。
- 没有名称、没有材料、没有装配约束；**不能把“几何上像”当成“机构上就是”**。

## 4. 能不能推出 `m`、`com`、惯量、轮径、轮距、轴距、离地间隙

| 量 | 能否从 3D 推出 | 口径 | 结论 |
|---|---|---|---|
| 轮径 | **能** | 驱动轮单文件 B-rep 包围盒：71.61 mm；整机实验件几何：约 69.15 mm | 两个值差 2.46 mm，且都不是正式设计；正式值应取 BOM 对应 Roborock S5 Max 模块（第三方实测 71.5 mm，属【公开参考】） |
| 轮距 | **能（仅实验件）** | 两驱动轮中心距：305.05 mm（实验件）；URDF 声明 235 mm | 差 70 mm，说明实验件不是正式设计；**不能拿实验件的 305 mm 当基准** |
| 轴距 | **能（仅实验件）** | 轮轴→脚轮中心：140.08 mm（实验件）；URDF 几何 144.5 mm | 两个来源差 4.4 mm；只能作量级 |
| 离地间隙 | **部分** | 实验件最低非轮点约 1.5 mm、车体约 6 mm；URDF `floor_clearance` 12.5 mm | 实验件摆位错误 + URDF 只代表 `base_link` 底面；**真实最低非轮点缺失**，不能给单点基准 |
| 整机质量 `m` | **不能** | STEP 不含材料密度；只能 `ρ·V` | 实验件体积 1.4636 L；ρ=1240 时 1.81 kg，ρ=1000 时 1.46 kg。**质量随 ρ 变，不是 CAD 给定值**；正式设计也没有整机 STEP |
| 质心 `com` | **只能均匀密度近似** | B-rep 体积质心：实验件 B 系 (8.944, 0.067, 44.410) mm | 只代表“全件同一密度”的几何质心；电池/电机/尘水的密度差异未覆盖。**不能当 `z_cg` 基准** |
| 惯量 | **只能均匀密度近似** | B-rep 关于质心的惯量张量，按 ρ 线性缩放 | 同上；分件密度未知，整机惯量不可信。可作为敏感性上/下界的起点，不能进定量结论 |
| 悬挂 `k/F0/c/travel` | **不能** | 静态 STEP 没有弹簧/运动副；URDF 没有悬挂自由度 | 只能实测 |

### 4.1 一句话结论

> **能推出**：零件级几何（轮径、轮宽、脚轮外形、驱动轮模块体积/均匀密度质心与惯量）和实验整机的包围盒/均匀密度质心；**不能推出**：正式设计的整机质量、真实 `z_cg`、整机惯量、轮距/轴距/离地间隙的正式值、任何悬挂参数。

## 5. 资产准入（S17 四项）现状

| 项 | 状态 | 证据 |
|---|---|---|
| 推导脚本 | 有（组件级） | `docs/基准机型/scripts/step_component_properties.py` @ `bdf5be2`，随 `b996dc0` 推送；只处理单个组件，不处理整机 |
| 输入 `sha256` | 有（驱动轮） | `OOM-W01-drive-wheel-assembly.stp` = `101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2` |
| 输出尺寸表 | 有（组件级，已推送） | `docs/基准机型/oomwoo-drive-wheel-dimensions.{md,csv}` 在 `keylliucong/oomwoo-baseline-params@b996dc0`；引用 `rev=b996dc0#docs/基准机型/oomwoo-drive-wheel-dimensions.md` 可解析；表头 `table_rev=0b73eda` 是 CSV 的 blob sha，不是 commit（语义待修正） |
| 环境声明 | 有 | Python 3.13.18 / gmsh 4.15.2 / NumPy 2.5.5；OCC 由 gmsh 内置；方法 `brep_exact`，无 mesh |
| 整机级四项 | **不齐** | 没有正式整机 STEP；实验件没有整机尺寸表；没有密度来源；没有整机脚本 |

> 因此：**组件级轮径/轮宽/轮体惯量已可走【图纸推算】**（四项齐、表已推送；无实测交叉校核，止于 `sensitivity`）；**轮体质量仍是【工程假设】**，因为密度是假设；**整机 `m/com/I` 最高只能【工程假设】**，且实验件本身还不是正式设计。

## 6. 没有的东西（不要用别的东西凑）

- 没有正式设计的整机 STEP；没有 `designs/one/stock/` 几何。
- 没有材料/密度表；STEP 无 material assignment。
- 没有整机质量、质心 y/z、整机惯量、悬挂参数、轮端扭矩的实测或设计冻结值。
- 没有 STL/DAE/OBJ；没有 URDF/SDF 在这两个仓库内。
- 没有越障机构方案；`contributions/stair-climbing/README.md` 明确是 exploratory，不构成 v1 机构。

## 7. 附：全部 STEP 文件清单

> 单位按文件内 `SI_UNIT` 声明；`mm` 表示检出 `.MILLI.,.METRE.`，`未检出` 表示文件头/尾 40 KiB 内没有单位声明（不代表不是 mm）。产品数按文件尾段 `PRODUCT(` 计数；`0/未检出` 多为单件或产品定义不在尾段。
>
> 55 个 STEP 中，46 个按文件头/尾直接检出单位；其余 9 个（CM5 两个、ydlidar_x3_pro、4 个开关、P01–P03 等）未在头/尾 40 KiB 内检出 `LENGTH_UNIT`，表中写“未检出/未逐一检出”，**不代表不是 mm**。所有 STEP 的格式均为 B-rep；AP214/AP242 是 schema，不是精度等级。

| `designs/one/agentic/july-2026/device_full.step` | AP214 | 15.6 MiB | mm | 0 |
| `designs/one/fusion360/STEP/03-01 Motor_Gearbox.step` | AP214 | 8.7 MiB | mm | 18 |
| `designs/one/fusion360/STEP/03-02 Red_Brush_Gearbox_step.step` | AP214 | 2.8 MiB | mm | 11 |
| `lib/casters/irobot_caster.step` | AP214 | 731 KiB | mm | 0 |
| `lib/cm/CM4.step` | AP214 | 62.2 MiB | mm | 1 |
| `lib/cm/CM4Lite.step` | AP214 | 62.5 MiB | mm | 1 |
| `lib/cm/CM5R5-3dsteps.step` | AP214 | 13.4 MiB | 未检出 | 0 |
| `lib/cm/CM5liteR5-3dstep.step` | AP214 | 96.0 MiB | 未检出 | 0 |
| `lib/dreame/Cliff_Bumper_Sensor_Assembly-2.STP` | AP242 | 591 KiB | mm | 3 |
| `lib/dreame/brush-no-bristles-core.step` | AP242 | 713 KiB | mm | 1 |
| `lib/dreame/brush-no-bristles.stp` | AP242 | 3.3 MiB | mm | 1 |
| `lib/dreame/brush_CAD-REVISED_stp_1.stp` | AP242 | 3.3 MiB | mm | 1 |
| `lib/dreame/dreame-tricut-brush.step` | AP242 | 230 KiB | mm | 1 |
| `lib/dreame/dreame_brush_core_with_bristles.step` | AP242 | 986 KiB | mm | 1 |
| `lib/dreame/dreame_brush_screw_cap.step` | AP214 | 264 KiB | mm | 0 |
| `lib/dreame/dreame_brush_snap_cap.step` | AP214 | 217 KiB | mm | 0 |
| `lib/dreame/dreame_brushes_housing.step` | AP214 | 1.8 MiB | mm | 4 |
| `lib/dreame/dreame_brushes_housing2.step` | AP214 | 8.0 MiB | mm | 0 |
| `lib/dreame/dreame_dust_bin.step` | AP242 | 1.4 MiB | mm | 1 |
| `lib/dreame/dreame_hepa_filter.step` | AP214 | 2.0 MiB | mm | 0 |
| `lib/dreame/dreame_mop_bottom_cover.step` | AP242 | 977 KiB | mm | 1 |
| `lib/dreame/dreame_side_brush_angled.step` | AP214 | 1.1 MiB | mm | 1 |
| `lib/dreame/dreame_side_brush_angled_bristles.step` | AP214 | 4.0 MiB | mm | 1 |
| `lib/dreame/suction_fan_mount.stp` | AP214 | 3.6 MiB | mm | 0 |
| `lib/fans/22N704V160.stp` | AP214 | 1.4 MiB | mm | 0 |
| `lib/fans/msdg-fan.step` | AP214 | 3.4 MiB | mm | 0 |
| `lib/irobot/OOM-E03-01-bumper-switch.stp` | AP242 | 1.8 MiB | mm | 1 |
| `lib/irobot/OOM-E03-02-bumper-switch.stp` | AP242 | 2.0 MiB | mm | 1 |
| `lib/irobot/cliff_bumper_sensor_assembly.step` | AP242 | 532 KiB | mm | 3 |
| `lib/ky-003.step` | AP214 | 268 KiB | mm | 1 |
| `lib/lidars/camsense_x1.step` | AP214 | 262 KiB | mm | 1 |
| `lib/lidars/ldlidar_ld19.step` | AP214 | 10.2 MiB | mm | 3 |
| `lib/lidars/xiaomi_lds02rr.step` | AP214 | 268 KiB | mm | 1 |
| `lib/lidars/ydlidar_scl.step` | AP214 | 85 KiB | mm | 1 |
| `lib/lidars/ydlidar_x2.step` | AP214 | 1.5 MiB | mm | 1 |
| `lib/lidars/ydlidar_x2l.step` | AP214 | 172 KiB | mm | 5 |
| `lib/lidars/ydlidar_x3_pro.step` | AP214 | 2.3 MiB | 未检出 | 69 |
| `lib/ov5647-wide-angle-camera-module.step` | AP214 | 1.2 MiB | mm | 13 |
| `lib/roborock/OOM-B02-side-brush.stp` | AP242 | 1.5 MiB | mm | 1 |
| `lib/roborock/OOM-B03-01-split-brush.stp` | AP242 | 540 KiB | mm | 1 |
| `lib/roborock/OOM-B03-02-split-brush.stp` | AP242 | 542 KiB | mm | 1 |
| `lib/roborock/OOM-E01-battery.stp` | AP242 | 71 KiB | mm | 1 |
| `lib/roborock/OOM-E05-carpet-sensor.stp` | AP242 | 19 KiB | mm | 1 |
| `lib/roborock/OOM-F02-fan-BL24131616.stp` | AP242 | 1.9 MiB | mm | 1 |
| `lib/roborock/OOM-M01-main-brush-gearbox.step` | AP214 | 280 KiB | mm | 1 |
| `lib/roborock/OOM-M02-side-brush-assembly-flexiarm.stp` | AP242 | 5.7 MiB | mm | 7 |
| `lib/roborock/OOM-P01-mop-assembly-flexiarm.stp` | STEP | 4.6 MiB | mm | 1 |
| `lib/roborock/OOM-P02-mop-assembly-fixed.stp` | STEP | 443 KiB | mm | 1 |
| `lib/roborock/OOM-P03-mop-disk.stp` | STEP | 1.0 MiB | mm | 1 |
| `lib/roborock/OOM-W01-02-drive-wheel-switch.stp` | STEP | 77 KiB | mm | 1 |
| `lib/roborock/OOM-W01-drive-wheel-assembly.stp` | AP242 | 811 KiB | mm | 1 |
| `lib/switches/C107266.step` | STEP | 1.3 MiB | 未检出 | 0 |
| `lib/switches/C2906291.step` | STEP | 1.6 MiB | 未检出 | 0 |
| `lib/switches/C405949.step` | STEP | 1.7 MiB | 未检出 | 0 |
| `lib/switches/C50395969.step` | STEP | 1.1 MiB | 未检出 | 0 |

## 8. 原生 CAD 与压缩包

| 文件 | 格式 | 大小 | 装配关系 | 说明 |
|---|---|---:|---|---|
| `designs/one/fusion360/Top_Assembly_110926.f3z` | Fusion 360 归档 | 93.2 MiB | 有 | 正式设计链顶层装配；需 Fusion 360 |
| `designs/one/fusion360/old/Assembly_2.f3z` | Fusion 360 归档 | 39.5 MiB | 有 | 旧版装配 |
| `designs/one/fusion360/old/Top_Assembly_103026.f3z` | Fusion 360 归档 | 83.8 MiB | 有 | 旧版顶层装配 |
| `designs/one/fusion360/old/Top_Assembly_110126.f3z` | Fusion 360 归档 | 84.5 MiB | 有 | 旧版顶层装配 |
| `designs/one/fusion360/old/Top_Assembly_110626.f3z` | Fusion 360 归档 | 85.8 MiB | 有 | 旧版顶层装配 |
| `designs/one/fusion360/old/OOM-B03_Main_Assembly.f3d` | Fusion 360 零件/装配 | 28.2 MiB | 可能有 | 主刷总成 |
| `designs/one/fusion360/old/OOM-M02-Assembly.f3d` | Fusion 360 零件/装配 | 15.2 MiB | 可能有 | 侧刷/FlexiArm |
| `lib/dreame/dreame_brush_core_with_bristles.7z.001` / `.002` | 7z 分卷 | 未展开 | 无 | 刷芯压缩包；不是可直接读取的 mesh/STEP |
