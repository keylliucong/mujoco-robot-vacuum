# OOMWOO 基准机型参数提取

- 编制日期：2026-11-22
- 基准对象：[makerspet/oomwoo](https://github.com/makerspet/oomwoo)（Apache-2.0，DIY 扫地机器人，设计/RFC 阶段）
- 用途：给我们越障仿真提供一台“基准机型”的公开参数与可信 CAD 输入。**不是本机实测，不得填入本机型参数表当实测值。**
- 配套：[oomwoo-缺口与影响](oomwoo-缺口与影响.md)、[驱动轮组件 STEP 尺寸表](oomwoo-drive-wheel-dimensions.md)、[推导脚本](scripts/step_component_properties.py)
- 范围：只提取参数与血缘；**不建 MuJoCo 模型、不跑仿真**；整机几何只引用现有 URDF/文档，未复刻 `hammerhead` 的建模工作。
- 标记沿用项目参数表：`本机实测` / `图纸推算` / `公开参考` / `工程假设` / `缺失` / `待标定`。本文件没有 `本机实测` 项。

## 0. 一句话结论

OOMWOO 能提供的是一套**设计阶段的公开几何、URDF 质量占位值和一份驱动轮模块的实测级零件资料**：整机外形、轮径/轮距/轴距/离地间隙可以拿到【公开参考】；驱动轮减速比、编码器、电机电阻/堵转电流可以拿到【公开参考】；**可信的整机质量/质心/惯量没有**，`designs/one/stock/` 在当前 rev 中没有几何文件，也没有可信的整机 STEP；可用的是 `lib/` 里的零件级 STEP。因此它能把几何和轮端输入从“空白”变成“可做敏感性分析的参考”，但不能让任何整机定量结论升级。

## 1. 来源版本与读数约定

### 1.1 版本

| 来源 | rev / 日期 | 用途 |
|---|---|---|
| `makerspet/oomwoo` | `0218857b2ecc53fb8e289b097b3bdf7a9e184386`，2026-11-19 | BOM、设计文档、part-specs |
| `makerspet/oomwoo-one` | `a630d1c77255072d280a2a41a7a2bd1a1c98cadd`，2026-10-19 | URDF / Gazebo 机器人描述 |
| `makerspet/oomwoo-cad`（与 `oomwoo-one-cad` 同 HEAD） | `266210a47cab931c5891a07c9a29d48388a54b0c`，2026-11-09 | `lib/` 可信零件 STEP；`designs/one/stock/` 在本 rev **没有文件** |
| 驱动轮组件 STEP | `lib/roborock/OOM-W01-drive-wheel-assembly.stp`，sha256 `101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2` | 【图纸推算】轮径/轮宽/轮体质量与惯量 |

> `oomwoo` 仍是设计/RFC 阶段：README 明确写 “Not buildable yet” (`oomwoo@0218857:README.md:20`)，`docs/BUILD_INSTRUCTIONS.md:3-8` 也写 “Not available yet”。因此文档里的尺寸是设计值/近似值，不是量产实测。

> 下文简写：`params.xacro` = `oomwoo-one@a630d1c:urdf/params.xacro`；`robot.urdf.xacro` = `oomwoo-one@a630d1c:urdf/robot.urdf.xacro`；`IKsares:<line>` = `oomwoo@0218857:contributions/part-specs/IKsares/drive-wheel/README.md:<line>`；`OsakaTX:<line>` = `oomwoo@0218857:contributions/part-specs/OsakaTX/README.md:<line>`；`OsakaTX/vacuumtiger-verified-specs.md` 同仓库 `contributions/part-specs/OsakaTX/`。

### 1.2 机体系 B 与 URDF 的对应

本文所有“B 系”值按项目定义：

- 原点 O = 左右驱动轮轴心连线中点在地面上的投影；
- `+x` 前向（车头），`+y` 左向，`+z` 向上，右手系。

对 OOMWOO 的 URDF：

- `base_footprint` 在地面，`base_link` 抬高 `floor_clearance = 12.5 mm`（`oomwoo-one@a630d1c:urdf/robot.urdf.xacro:188-192`）；
- 两驱动轮轴心都在 `x = 0`，轮心高度正好等于轮半径（`robot.urdf.xacro:250-258, 280-288`）；
- 从动轮在车头 `+x`（`robot.urdf.xacro:224-227`）；
- 因此 **`base_footprint` 与 B 在 t=0 重合，`base_link` 是 B 抬高 12.5 mm 的机体系**。本文引用 URDF 的 z 值时，统一换算到地面（B 的 z=0）。

> URDF 的变量名 `wheel_base` 实际是**轮距（track）**，不是轴距（drive-axle-to-caster）。见 `urdf/params.xacro:7-8,19`。

### 1.3 标签口径

| 标签 | 本文件中的含义 |
|---|---|
| 【公开参考】 | 仓库文档、BOM、URDF 或 part-specs 给出的值；含作者的设计值/近似值，不等于量产实测 |
| 【图纸推算】 | 从可信 `lib/` 零件 STEP 用脚本精确积分/量出的值，带 S17 血缘（脚本、输入 sha256、尺寸表、环境/算法） |
| 【工程假设】 | 本文为解释/换算临时采用的假设（如齿轮箱效率 0.6–0.8、质量密度 ρ），须标定 |
| 【缺失】 | 仓库内没有可用值，或只有占位值不能用 |

## 2. 参数总表

### 2.1 整机几何

| 参数 | 数值 | 单位 | 标记 | 来源 | 取值理由 / 备注 |
|---|---:|---|---|---|---|
| 机身直径（OOMWOO One） | 349 | mm | 【公开参考】 | `oomwoo@0218857:docs/ARCHITECTURE.md:75`；`oomwoo-one@a630d1c:urdf/params.xacro:18`；`oomwoo-one@a630d1c:README.md:174` | 文档与 URDF 同源；URDF 自称近似，需用实物/评审 CAD 替换 |
| 机身高度（注释值） | 95 | mm | 【公开参考】 | `oomwoo-one@a630d1c:urdf/params.xacro:5`；`oomwoo-one@a630d1c:README.md:174` | 含 LiDAR 塔的近似总高 |
| 机身高度（由 URDF 参数推算） | 97 | mm | 【公开参考】（推算） | `urdf/params.xacro:20-22`：车体顶 79 mm + LiDAR 壳 18 mm | 与 95 mm 注释冲突；见 §4 |
| 车体筒高（不含 LiDAR 塔） | 66.5 | mm | 【公开参考】 | `urdf/params.xacro:20-22`；`lower_cylinder_height=0.0665` | 车体顶 79 mm − 离地 12.5 mm |
| 最小离地间隙 | 12.5 | mm | 【公开参考】 | `urdf/params.xacro:17`；`robot.urdf.xacro:188-192` | URDF 的 `floor_clearance`；只代表 `base_link` 底面，不代表最低非轮点 |
| 最低非轮点 / 托底高度 | 12.5（URDF 只建了车体/轮/从动轮）；实机最低非轮点未公开 | mm | 【公开参考】/【缺失】 | `urdf/params.xacro:17`；`robot.urdf.xacro` 没有主刷/拖布几何；`docs/ARCHITECTURE.md:88-90` 把外形/高度预算列为 TBD | URDF 的 12.5 mm 不是实机最低点；主刷/拖布/裙边会更低，必须用评审 CAD 或塞尺 |
| 接近角 / 离去角 | 未公开 | ° | 【缺失】 | 仓库无定义 | 需要项目定义 + 几何计算 |
| 轮距（track） | 235 | mm | 【公开参考】 | `urdf/params.xacro:7,19`；`wheel_base=0.235` | 注释称 “measured wheel track 235mm” |
| 轮距（bridge/odometry 常量） | 233 | mm | 【公开参考】 | `urdf/params.xacro:7-8`；`contributions/part-specs/OsakaTX/README.md:57` | 同一 URDF 注释说 bridge 用 0.233 m，差 2 mm；标定口径未统一 |
| 轴距（驱动轮轴→从动轮中心） | 144.5 | mm | 【公开参考】（推算） | `robot.urdf.xacro:224-227`：`base_diameter/2 − caster_inset = 174.5 − 30` | 从动轮在车头；URDF 没有单独的轴距变量 |
| 轮心高度 | 34.0 | mm | 【公开参考】（推算） | `robot.urdf.xacro:250-258`：`wheel_diameter/2 − floor_clearance` 加回地面 12.5 mm | 等于 URDF 轮半径；与 lib STEP 的 35.80 mm 冲突，见 §4 |
| 从动轮直径 | 25 | mm | 【公开参考】 | `urdf/params.xacro:11`；`OsakaTX/README.md:388-398`（Roomba 4624869，~25 mm） | URDF 把从动轮建成 25 mm 球；实物是球型/推入式 |
| 从动轮类型 | 球型 / 推入式（被动） | — | 【公开参考】 | `BOM.md:23`；`OsakaTX/README.md:388-398` | 无传感器、无驱动 |
| 整机外形（可信 CAD） | 未提供 | — | 【缺失】 | `oomwoo-cad@266210a` 的 `designs/one/stock/` 在本 rev 无文件；`designs/README.md` 只说明应有 stock/ | 不能用未评审实验件代替；来源分级见 [缺口与影响](oomwoo-缺口与影响.md) §4 |

> 关于 349 mm 与 donor 的 330 mm：`OsakaTX/README.md:47` 的 330 mm 来自 alvarosamudio 的 Roborock 参考 URDF，不是 OOMWOO One；不要把它当 OOMWOO 的机身直径。

### 2.2 质量、质心、惯量

| 参数 | 数值 | 单位 | 标记 | 来源 | 取值理由 / 备注 |
|---|---:|---|---|---|---|
| 整机质量（URDF 参数求和） | 2.937 | kg | 【公开参考】（求和，非实测） | `urdf/params.xacro:48-52,108,120,146,179,193` + `robot.urdf.xacro:129` | 2.5（筒身）+0.05（从动轮）+0.1×2（轮）+0.15（LiDAR）+0.004×2（IR 接收）+0.004（IR 挡板）+0.005×2（侧距）+0.005（ToF）+0.005（相机）+0.005（IMU） |
| 整机质量（BOM 估算） | 不可得 | kg | 【缺失】 | `BOM.md` 全表没有质量列 | 已知件合计只有约 0.84–0.88 kg 且覆盖不全（见下），不能当整机质量 |
| 整机质量（可信 CAD） | 未提供 | kg | 【缺失】 | `oomwoo-cad@266210a` 的 `designs/one/stock/` 无文件 | 没有可信整机 STEP，无法给质量/质心/惯量 |
| 筒身质量 | 2.500 | kg | 【公开参考】 | `urdf/params.xacro:48` | 注释 `<!-- caster and battery weight -->` 语义不明：可能已含从动轮/电池，与单独 `caster_mass` 可能重复；不能当质量分解 |
| 从动轮质量 | 0.050 | kg | 【公开参考】 | `urdf/params.xacro:50` | URDF link 质量；实物 30–61 g（`OsakaTX/README.md:395`） |
| 单个驱动轮 link 质量 | 0.100 | kg | 【公开参考】 | `urdf/params.xacro:51` | 只是轮 link；complete module 是另一口径（见下） |
| LiDAR 质量 | 0.150 | kg | 【公开参考】 | `urdf/params.xacro:52` | OsakaTX 给 ~175 g（`OsakaTX:210`）；差 25 g，见 §4 |
| 其余传感器质量合计 | 0.037 | kg | 【公开参考】 | `urdf/params.xacro:108,120,146,179,193` + `robot.urdf.xacro` | 2×4 g IR + 4 g 挡板 + 2×5 g 侧距 + 5 g ToF + 5 g 相机 + 5 g IMU |
| 质心 x（URDF 注释） | +2.2 | mm | 【公开参考】 | `urdf/params.xacro:35-42` | 注释说 “CoM = +2.2 mm with this offset”；只给 x，未给 y/z |
| 质心 x（按 URDF 质量/位置复算） | +6.19 | mm | 【公开参考】（本报告复算） | 用 `params.xacro:48-52` 与 `robot.urdf.xacro:224-258,313-336` 的质量×位置求和 | 与注释 +2.2 mm 差 4.0 mm；复算方法与假设见 §4，冲突不结论 |
| 质心 y / z | y≈0（左右对称的设计假设）；z 不可用 | mm | 【公开参考】/【缺失】 | `robot.urdf.xacro` 左右对称；z 见下方“URDF 惯量宏的两个问题” | y≈0 是设计对称，不是实测；z 因 URDF 把 2.5 kg 筒身 inertial origin 放在车体底面而不可用 |
| 整机惯量（Ixx/Iyy/Izz 或张量） | 未公开 | kg·m² | 【缺失】 | `urdf/inertial.xacro` 只有每个 link 的均质几何惯量宏；仓库未汇总整机惯量 | URDF 惯性宏有方向/原点错误（见下），不能直接复算；需修正后再算，且质量仍是占位值 |
| 驱动轮模块 pair 质量 | ~0.463 | kg | 【公开参考】 | `OsakaTX/README.md:99-102`（AliExpress 原厂 S6 轮模块 pair 的 listing，非实测） | 含电机+减速箱+悬挂+轮胎+线束；与“轮 link”不是同一口径 |
| 单电机质量 | 0.066 | kg | 【公开参考】 | `IKsares/drive-wheel/README.md:51-62`（实测：电机+后 PCB+220 mm 线） | 不含减速箱/轮胎/悬挂 |
| 驱动轮轮体质量（lib STEP） | 0.0623 @ ρ=1100；0.0702 @ ρ=1240 | kg | 【图纸推算】+密度假设 | [驱动轮尺寸表](oomwoo-drive-wheel-dimensions.md)；`lib/roborock/OOM-W01-drive-wheel-assembly.stp` tag 3 | 只含轮体实体；ρ 是假设，STEP 无材料密度 |
| 从动轮质量 | 30–61 | g | 【公开参考】 | `OsakaTX/README.md:395` | 塑料/金属+塑料两种变体；未实测 |

**质心 x 复算假设（用于解释 #6 的 +6.19 mm）**

取 URDF 各 link 质量与 x 位置：`base_link` 2.5 kg @ x=0；`caster` 0.05 kg @ x=+0.1445 m；`wheel_L/R` 各 0.1 kg @ x=0；`base_scan` 0.15 kg @ x=+0.0745 m；`ir_rx_L/R` 各 0.004 kg @ x=−0.1645 m；`ir_baffle` 0.004 kg @ x=−0.1595 m；`range_L/R` 各 0.005 kg @ x=0；`tof_front` 0.005 kg @ x=+0.1745 m；`camera` 0.005 kg @ x=+0.1745 m；`imu` 0.005 kg @ x=0。总质量 2.937 kg，质量矩求和 / 总质量 = **+6.19 mm**。如果 `lower_cylinder_mass` 的 2.5 kg 已含电池/从动轮，则这个复算本身也要改；仓库没有说明，故只作为冲突证据，不作为 CoM 值使用。

**URDF 惯量宏的两个问题（因此不能用 URDF 直接算整机惯量）**

1. `urdf/inertial.xacro:14-20` 的 `solid_cylinder_inertia` 给 `<origin rpy="pi/2 0 0">`，把圆柱轴向从 link z 转到 link −y；但 `robot.urdf.xacro` 里的 visual/collision `<cylinder>` 轴是 link z。两者差 90°，每个圆柱 link 的惯量张量方向与几何不一致。
2. `base_link` 的 visual/collision 圆柱中心在 `z=lower_cylinder_height/2=33.25 mm`（`robot.urdf.xacro:199-214`），但 `solid_cylinder_inertia` 的 inertial origin 是 0（link 原点，即车体底面）。2.5 kg 筒身的 CoM 因此被放在地面以上 12.5 mm，而不是视觉中心 45.75 mm。

所以：URDF 的总质量 2.937 kg 可以求和；但由它直接算出的整机 CoM z / 惯量不可信，不能标【图纸推算】。**URDF 的“有惯性宏”不等于“有可用惯量”。**

**BOM 已知件质量小计（不完整，不是整机质量）**

| 件 | 质量 | 来源 | 备注 |
|---|---:|---|---|
| 驱动轮模块 pair | ~463 g | `OsakaTX/README.md:101` | listing 值，非实测 |
| 从动轮 | 30–61 g | `OsakaTX/README.md:395` | 两种变体 |
| LiDAR | ~175 g | `OsakaTX/README.md:210` | CRL-200S |
| 风机裸电机 | 25–30 g | `OsakaTX/README.md:168` | 只是裸电机，不含叶轮/壳体 |
| 侧刷电机 | ~150 g | `OsakaTX/README.md:435` | Roborock 总成；BOM 实际选 JGA25-310，质量不同 |
| **小计** | **~843–879 g** | — | 缺电池、筒身、主刷、风机总成、PCB、线束等；**不能当整机质量** |

### 2.3 轮系与悬挂

| 参数 | 数值 | 单位 | 标记 | 来源 | 取值理由 / 备注 |
|---|---:|---|---|---|---|
| 驱动形式 | 左右独立驱动，差速转向 | — | 【公开参考】 | `oomwoo-cad@266210a:docs/SPEC.md` “driving wheels should be centered, wide apart”；`urdf/robot.urdf.xacro:250-288` | 两轮 continuous joint；URDF/Gazebo 用 diff-drive |
| 驱动轮型号（模块） | Roborock S5 Max 家族 aftermarket 模块 | — | 【公开参考】 | `BOM.md:21-22`；`IKsares/drive-wheel/README.md:16-20` | BOM 兼容 S4/S5/S5 Max/S6/S7 等多型号；不是单一 OEM 件 |
| 驱动轮直径（URDF） | 68 | mm | 【公开参考】 | `urdf/params.xacro:9` | URDF 的 `wheel_diameter=0.068` |
| 驱动轮直径（lib STEP） | 71.61 | mm | 【图纸推算】 | [驱动轮尺寸表](oomwoo-drive-wheel-dimensions.md)：`geom.component.wheel.diameter_mm` | 轮体实体 tag 3；B-rep 量测，非 mesh |
| 驱动轮直径（IKsares 实测） | 71.5 | mm | 【公开参考】 | `IKsares/drive-wheel/README.md:343` | 卡尺测 aftermarket 模块轮胎外径 |
| 驱动轮直径（OsakaTX 推算） | 65 | mm | 【公开参考】 | `OsakaTX/README.md:46` | 来自 alvarosamudio 的 Roborock 参考 URDF；作者自己在 `IKsares:549-550` 把它列为被实测修正的旧值 |
| 驱动轮宽度（URDF） | 12 | mm | 【公开参考】 | `urdf/params.xacro:10` | `wheel_width=0.012` |
| 驱动轮宽度（lib STEP） | 15.76 | mm | 【图纸推算】 | [驱动轮尺寸表](oomwoo-drive-wheel-dimensions.md)：`geom.component.wheel.width_mm` | 轮体实体 tag 3 沿 z 轴宽 |
| 驱动轮宽度（BOM 备用轮胎） | 14 | mm | 【公开参考】 | `BOM.md:67` | 57 mm ID / 68 mm OD / 14 mm 宽；只用于“从零做轮”的备用轮胎，不是 Roborock 模块 |
| 从动轮数量/位置 | 1 个，车头中心 | — | 【公开参考】 | `oomwoo-cad@266210a:docs/SPEC.md` “caster wheel - front center”；`robot.urdf.xacro:224-227` | 支撑多边形：轮轴（x=0）到从动轮（x=+144.5 mm） |
| 从动轮直径 | 25 | mm | 【公开参考】 | `urdf/params.xacro:11`；`OsakaTX/README.md:388-398` | URDF 球径 25 mm；实物 ~25 mm |
| 悬挂形式 | 驱动轮模块内置被动摆臂 + 弹簧 | — | 【公开参考】 | `BOM.md:21`（“Motor + encoder + suspension + tire + cables + wheel-drop sensors”）；`docs/design-document.md:79`；`IKsares/drive-wheel/README.md:475-478` | 结构存在；作者称 wheel-drop 由悬臂/弹簧动作，但未给图 |
| 悬挂行程 | 未公开 | mm | 【缺失】 | `IKsares/drive-wheel/README.md:653` 明确把 “suspension travel” 列为 open | 需要拆解模块测轮心相对机身的可动范围 |
| 弹簧预压 / 刚度 / 阻尼 | 未公开 | mm / N·mm⁻¹ / N·s·mm⁻¹ | 【缺失】 | 仓库内无 | 需要弹簧试验台/落锤或阶跃响应 |
| 限位 / 止挡 | 未公开 | — | 【缺失】 | 仓库内无 | 需要拆解或供应商图 |
| URDF 中的悬挂自由度 | 0 | — | 【公开参考】 | `robot.urdf.xacro:224-227`（从动轮 fixed）；`:250-258,280-288`（轮只有 continuous 转轴，无悬挂平移） | Gazebo 模型没有悬挂行程；不能拿 URDF 代替悬挂参数 |

### 2.4 驱动与传动

| 参数 | 数值 | 单位 | 标记 | 来源 | 取值理由 / 备注 |
|---|---:|---|---|---|---|
| 电机型号（实测 aftermarket） | CDM `GM-RS360-16248` | — | 【公开参考】 | `IKsares/drive-wheel/README.md:20,37` | 电机 can 标记；12 V DC，RS-360 短can |
| 电机型号（目录候选） | Nidec `20N704RC70` | — | 【公开参考】 | `OsakaTX/README.md:23-36` | Nidec 目录“in development”；作者警告量产可能不同 |
| 额定电压（实测电机） | 12 | V | 【公开参考】 | `IKsares:37` | can 标记 `DC 12.0V` |
| 额定电压（目录电机） | 14.4 | V | 【公开参考】 | `OsakaTX/README.md:29` | Nidec 目录值；与实测 CDM 不是同一件 |
| 供电电压 | 14.4（nominal）/16.8（满充） | V | 【公开参考】 | `BOM.md:35`；`docs/ARCHITECTURE.md:102-104` | 4S2P Li-ion |
| 减速比（实测） | 65.36 : 1 | — | 【公开参考】 | `IKsares:268-284` | 四级齿轮齿数实测：`(36·42·34·24)/(11·13·12·11)` |
| 减速比（推算） | ~190 : 1 | — | 【公开参考】 | `OsakaTX/README.md:59-62`；`OsakaTX/vacuumtiger-verified-specs.md:39-54` | 由 `VELOCITY_TO_DEVICE_UNITS=523`、0.3 m/s、16,800 rpm、65 mm 轮推算；作者未拆齿 |
| 编码器类型 | 单通道 Hall，开集输出，需外部上拉 | — | 【公开参考】 | `IKsares:169-266,332-405` | 蓝线 OUT；10 kΩ 上拉到 VCC；3.3 V 实测工作 |
| 编码器分辨率（实测） | 4 cycles/电机转；261.5 edges/轮转（仅上升沿）；0.859 mm/edge；1164 ticks/m | — | 【公开参考】 | `IKsares:332-352` | 4 对极（8 极）磁环；双边沿 522.9 edges/轮转、0.430 mm/edge、2328 ticks/m |
| 编码器分辨率（另一套推算） | ~228 PPR（轮端）；911 ticks/轮转；4464 ticks/m | — | 【公开参考】 | `OsakaTX/README.md:49-57`；`OsakaTX/vacuumtiger-verified-specs.md:22-34` | 由 `ticks_per_meter=4464` 和 65 mm 轮反推；`IKsares:556-599` 认为 4× 解码后两者差 ~4%，并把 ~228 PPR 归因于 65 mm 轮假设 |
| 编码器方向 | 单通道不能判方向 | — | 【公开参考】 | `IKsares:402-405` | VacuumTiger 用 IMU 陀螺补方向（`IKsares:614-616`） |
| 电机绕组电阻 | 5.08 | Ω | 【公开参考】 | `IKsares:79-100` | 三点法 `V = V0 + I·R` 拟合 |
| 电刷接触压降 | 1.91 | V | 【公开参考】 | `IKsares:79-100` | 同上；不能用普通欧姆表复核 |
| 堵转电流 | 1.99 @12 V；2.46 @14.4 V；2.93 @16.8 V | A | 【公开参考】 | `IKsares:107-117` | `I=(V−V0)/R`；硬件上限 16.8/5.08=3.31 A |
| 空载电流 | 0.13 @12 V | A | 【公开参考】 | `IKsares:131-145` | 电机出减速箱、轴自由 |
| 空载转速 | 6,150–6,180 | rpm | 【公开参考】 | `IKsares:358-374` | 12 V、编码器 410–412 Hz；轮端 ≈94 rpm ≈0.35 m/s |
| 额定扭矩 | 未公开 | N·m | 【缺失】 | 实测电机无额定电流/扭矩；`IKsares:632` 明确 “Torque ❌ not measured” | 不能把目录电机或推算值当成本电机的额定扭矩 |
| 堵转扭矩（轮端，推算） | 1.90 @12 V；2.35 @14.4 V；2.80 @16.8 V（η=1） | N·m | 【公开参考】+【工程假设】 | 本报告用 `IKsares:79-117,358-374` 推算：取空载转速中值 6,165 rpm，`Kt=(12−0.13·5.08−1.91)/(6165·2π/60)=0.01461 N·m/A`，`T_wheel=i·η·Kt·I_stall`，`i=65.36` | η=1 是上界；η=0.6–0.8 时 1.14–1.52 / 1.41–1.88 / 1.68–2.24 N·m。**不是实测，不能当额定值** |
| 额定扭矩（目录电机推算） | 电机 0.010；轮端 1.90（η=1，~190:1） | N·m | 【公开参考】+【工程假设】 | `OsakaTX/README.md:29-36`：13.8 W @13,200 rpm | 用的是 Nidec 目录电机和 ~190:1，与实测 CDM/65.36 不是同一套；只能当量级参考 |
| 轮端扭矩上限（URDF） | 0.5 | N·m | 【公开参考】 | `urdf/params.xacro:46`；`robot.urdf.xacro:255-257,285-287` | `motor_stall_torque=0.5` 用作轮 joint effort 上限；仓库未说明测量方法/条件，不能当实测 |
| 减速器效率 | 未公开 | — | 【缺失】 | 仓库无 | 本文推算只在 η=0.6–0.8 假设下给区间 |
| 限流 / 堵转保护 | 未公开 | A | 【缺失】 | `OsakaTX/README.md:91-97` 只给 TMI8870 3.6 A peak、集成电流调节；未给固件设定 | 需要驱动板/固件实测 |
| 电机驱动 IC | TMI8870（pin-compatible DRV8870） | — | 【公开参考】 | `OsakaTX/README.md:91-97` | 单 H 桥，3.6 A peak，6.8–45 V |
| 轮速测量 | 单通道 Hall + 轮 joint odom | — | 【公开参考】 | `IKsares:332-405`；`urdf/plugins.xacro:33-43` | Gazebo 用 `wheel_separation=wheel_base`、`wheel_radius=wheel_diameter/2` |
| 正常清扫速度 | 0.3 | m/s | 【公开参考】 | `OsakaTX/vacuumtiger-verified-specs.md:56-66`（`max_linear_speed`） | 来自 VacuumTiger 对 Roborock 的标定，不是 OOMWOO 实测；不能当本机速度 |
| 最大线加速度（URDF） | 1 | m/s² | 【公开参考】 | `urdf/params.xacro:47` | Gazebo diff-drive 参数，不是实测 |

### 2.5 电池、风机、主刷（越障非关键，只列名）

| 参数 | 数值/型号 | 单位 | 标记 | 来源 | 备注 |
|---|---|---|---|---|---|
| 电池 | 4S2P Li-ion，14.4 V nominal，~5200 mAh / 75 Wh，内置 BMS，16.8 V CC/CV | — | 【公开参考】 | `BOM.md:35`；`docs/ARCHITECTURE.md:61-63,102-104` | OEM BRR-2P4S-5200 类；电池质量未公开 |
| 电机电压 | 12 V（实测 CDM）/ 14.4 V（Nidec 目录） | V | 【公开参考】 | `IKsares:37`；`OsakaTX/README.md:29` | 与 4S 电池的 14.4 V nominal 不完全一致；见 §4 |
| 吸尘风机（6 kPa 档） | Dreame MSD-C-3 / Nidec 20N709U020 | — | 【公开参考】 | `BOM.md:24` | 风机总成质量未公开 |
| 吸尘风机（5.1–6 kPa 档） | Nidec 22N704W150 / 20N704S980 / 20N704R980L | — | 【公开参考】 | `BOM.md:25` | 同上 |
| 吸尘风机（10 kPa 档） | Roborock BL24131616 / Nidec 22N704V160 | — | 【公开参考】 | `BOM.md:26` | 同上 |
| 吸尘风机（36 kPa 档） | Roborock Saros 20 | — | 【公开参考】 | `BOM.md:27` | 同上；更高功率，质量未公开 |
| 主刷（推荐） | Dreame 锥形双滚刷（橡胶+刷毛）或 Roborock 单滚刷 | — | 【公开参考】 | `BOM.md:29-34` | 质量/惯量未公开；对越障不是关键 |
| 侧刷电机 | JGA25-310，12 V，~150 rpm，金属减速箱，无编码器 | — | 【公开参考】 | `BOM.md:51` | 用 14.4–16.8 V 供电时 PWM 限到 ~12 V |
| LiDAR | 3irobotix CRL-200S / Delta-2D，~175 g | — | 【公开参考】 | `OsakaTX/README.md:195-213` | 影响质心；URDF 用 150 g，见 §4 |

## 3. 图纸推算：可信 `lib/` 驱动轮组件

这是本文件唯一一组【图纸推算】值。它不是整机质量属性表，只覆盖 `lib/roborock/OOM-W01-drive-wheel-assembly.stp` 的**轮体实体**（tag 3）。

**S17 血缘（详见 [尺寸表](oomwoo-drive-wheel-dimensions.md)）**

| 项 | 值 |
|---|---|
| 脚本 | `docs/基准机型/scripts/step_component_properties.py@bdf5be26c68206f972d09f1c1e6d526366fc5b33` |
| 尺寸表 table_rev | `0b73edaad9a4929bc945f358c31dcc427d738d27`（CSV blob SHA，内容寻址；最终提交 SHA 见 PR） |
| 输入 | `lib/roborock/OOM-W01-drive-wheel-assembly.stp`，829,986 bytes |
| 输入 sha256 | `101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2` |
| 选中实体 | tag 3（3 个实体中的轮体） |
| 方法 | `brep_exact`（OCC B-rep 精确体积积分，非 mesh） |
| 网格容差 | `mesh_export=none`；`chord_tol=N/A`、`angle_tol=N/A`（没有导出 STL/mesh） |
| 环境 | Python 3.13.18；gmsh 4.15.2；NumPy 2.5.5；Open CASCADE 由 gmsh 内置（gmsh API 不暴露 OCC 精确版本） |
| 密度 | ρ=1100 kg/m³（主，橡胶/TPU 量级假设）；ρ=1240 kg/m³（对照，PLA） |

> `table_rev` 取尺寸表 CSV 的 blob SHA（内容寻址，避免“表头写自己的提交 SHA”的自指问题）；尺寸表最终提交 SHA 见 PR。

| 量 | 值 | 单位 | 备注 |
|---|---:|---|---|
| 轮径 | 71.61 | mm | B-rep bbox；与 IKsares 实测 71.5 mm 吻合 |
| 轮宽 | 15.76 | mm | 沿轮轴 z |
| 轮体体积 | 56.606 | cm³ | 5.6606e-5 m³ |
| 轮体质量 | 62.3 @1100；70.2 @1240 | g | 质量=ρV；STEP 无材料密度 |
| 轮体主惯性矩 | 2.00e-5, 2.00e-5, 3.77e-5 @1100 | kg·m² | 轮体自身，不是整机 |
| 轮体主惯性矩 | 2.25e-5, 2.25e-5, 4.25e-5 @1240 | kg·m² | 同上，按 ρ 线性缩放 |

**数据质量警告**：gmsh 读入该 STEP 时报告 `StepReaderData : Unresolved Reference : Fails Count : 1`。3 个实体都成功导入，轮体是完整的对称圆柱，因此轮径/轮宽可用；但 STEP 不是完全干净的导出，**整模块质量/惯量**在修好引用前不要用。

轮体 62–70 g/个；完整模块 pair 是 ~463 g，差值是电机/减速箱/悬挂/线束。两个口径不同，不能直接比较，也不能拿轮体质量当模块质量。

> 该表是组件级、STEP 自身坐标系，不是 B 系，也不是整机。不要把它和 URDF 的整机参数拼成一个模型；见 §5 候选输入与 [缺口与影响](oomwoo-缺口与影响.md) §4 来源分级。

## 4. 冲突清单（两个都列，不给结论）

| # | 量 | 值 A（来源） | 值 B（来源） | 冲突点 / 处理 |
|---|---|---|---|---|
| 1 | 驱动轮直径 | 68 mm（`urdf/params.xacro:9`） | 71.61 mm（lib STEP）；71.5 mm（`IKsares:343`） | URDF 比实测/STEP 小 3.5–3.6 mm；差异约 5%。轮径直接影响 h/R 与轮速换算，**不能混用**。OsakaTX 的 65 mm 是旧参考 URDF，`IKsares:549-550` 已把它列为被实测修正 |
| 2 | 驱动轮宽度 | 12 mm（URDF） | 15.76 mm（lib STEP） | 差 3.76 mm；URDF 轮宽可能只是接触带宽度，STEP 是轮胎全宽 |
| 3 | 轮距 | 235 mm（URDF `params.xacro:19`） | 233 mm（URDF 注释里的 bridge 常量；`OsakaTX:57`） | 差 2 mm；注释说“negligible, calibrate empirically”，但同一文件两个值，未统一 |
| 4 | 整机高度 | 95 mm（注释/README） | 97 mm（79 mm 车体顶 + 18 mm LiDAR 壳，`params.xacro:20-22`） | 差 2 mm；注释自身不自洽 |
| 5 | 整机质量 | 2.937 kg（URDF 参数求和） | BOM 不可得；无可靠 CAD | URDF 的 2.5 kg 筒身注释可能已含电池/从动轮，和单独 0.05 kg 从动轮可能重复；不能当实测 |
| 6 | 质心 x | +2.2 mm（URDF 注释） | +6.19 mm（按同一 URDF 质量/位置复算） | 差 4.0 mm；注释的 −1.6→+2.2 差值（3.8 mm）与 150 g LiDAR 在 +74.5 mm 的力矩一致，但“其余部分”的 CoM 不一致；原因未文档化 |
| 7 | 减速比 | 65.36:1（`IKsares:268-284` 齿数实测） | ~190:1（`OsakaTX:59-62` 由速度常量推算） | 差近 3 倍；`IKsares:576-599` 认为 ~190 的前提（16,800 rpm 目录电机）不适用于实测 6,165 rpm CDM 电机 |
| 8 | 编码器分辨率 | 4 cycles/电机转；261.5 edges/轮转；1164 ticks/m（`IKsares:332-352`） | ~228 PPR；911 ticks/轮转；4464 ticks/m（`OsakaTX:49-57`） | 两套相差 ~13%（轮转边缘数）；`IKsares:556-599` 说 4× 解码后与 4464 ticks/m 差 ~4%，并把差异归因于 65 mm 轮径假设；仓库未统一 |
| 9 | 电机额定电压 | 12 V（CDM can 标记） | 14.4 V（Nidec 目录） | 不是同一电机；不能用一个的电压/转速去套另一个的扭矩 |
| 10 | 轮端扭矩上限 | 0.5 N·m（URDF `motor_stall_torque`） | 1.90–2.80 N·m（本报告由 CDM 实测 R/V0/空载转速推算，η=1）；η=0.6–0.8 时 1.14–2.24 N·m | URDF 未说 0.5 是实测、额定还是占位；与推算差 2.3–5.6 倍。**失速判据不能只用 0.5**，也不能把推算当实测 |
| 11 | 轮 link 质量 | 0.100 kg（URDF） | 0.0623–0.0702 kg（lib STEP 轮体，ρ=1100/1240） | 同一“轮体”口径，URDF 比 STEP 高 30–38%；URDF 可能含轮毂/配重，STEP 只含轮体实体；未核实 |
| 12 | LiDAR 质量 | 0.150 kg（URDF） | ~0.175 kg（`OsakaTX:210`） | 差 25 g；对 CoM 有影响，但不足以解释 #6 的 4 mm |
| 13 | 从动轮质量 | 0.050 kg（URDF） | 30–61 g（`OsakaTX:395`） | 落在区间内；URDF 取 50 g 合理，但仍是设计值 |
| 14 | 机身直径 | 349 mm（OOMWOO 文档/URDF） | 330 mm（`OsakaTX:47`，alvarosamudio 的 Roborock 参考 URDF） | 后者是 donor 参考，不是 OOMWOO One；不应混入 OOMWOO 基线 |

## 5. 候选输入：两套值，不要拼在一起

> 这一节只是给建模者两套“可追溯的候选”，不是结论，也不是 MuJoCo 模型。**两套值来自不同年代/不同设计阶段，混用会造出第三台不存在的机器。**

### 5.1 U 套：ROS2 URDF 口径（首选作基准几何）

| 量 | 值 | 标签 |
|---|---:|---|
| 机身直径 | 349 mm | 【公开参考】 |
| 整机高度 | 95–97 mm | 【公开参考】 |
| 离地间隙 | 12.5 mm | 【公开参考】 |
| 轮径 / 半径 | 68 / 34 mm | 【公开参考】 |
| 轮宽 | 12 mm | 【公开参考】 |
| 轮距 | 235 mm（bridge 233 mm） | 【公开参考】 |
| 轴距（轮轴→从动轮） | 144.5 mm | 【公开参考】（推算） |
| 从动轮直径 | 25 mm | 【公开参考】 |
| 整机质量 | 2.937 kg（占位） | 【公开参考】（URDF 求和，非实测） |
| 质心 | 仅 x +2.2 mm（复算 +6.19 mm） | 【公开参考】/【缺失】 |
| 惯量 | 未公开 | 【缺失】 |
| 轮端扭矩上限 | 0.5 N·m（URDF 占位） | 【公开参考】 |

### 5.2 L 套：lib/ 组件 + part-specs 口径（用于轮端敏感性）

| 量 | 值 | 标签 |
|---|---:|---|
| 轮径 / 半径 | 71.61 / 35.80 mm | 【图纸推算】 |
| 轮宽 | 15.76 mm | 【图纸推算】 |
| 轮体质量 | 62.3 g @1100；70.2 g @1240 | 【图纸推算】+密度假设 |
| 减速比 | 65.36:1 | 【公开参考】 |
| 编码器 | 4 cycles/电机转；261.5 edges/轮转；0.859 mm/edge（上升沿） | 【公开参考】 |
| 堵转电流 | 1.99/2.46/2.93 A @12/14.4/16.8 V | 【公开参考】 |
| 轮端堵转扭矩（推算） | 1.90–2.80 N·m（η=1）；1.14–2.24 N·m（η=0.6–0.8） | 【公开参考】+【工程假设】 |
| 悬挂 | 结构存在；行程/刚度/阻尼/限位未公开 | 【公开参考】/【缺失】 |
| 整机质量/质心/惯量 | 未提供 | 【缺失】 |

**建议**：基准几何用 U 套（它是唯一完整的整机参数化描述）；轮径/轮端扭矩用 L 套做上下界和敏感性，不要用 L 套的 71.61 mm 去替换 U 套的 68 mm 后不记录。任何混用都要在模型 / 台账里逐行写来源。

## 6. 复现命令与文件清单

```bash
# 1) 三个仓库
git clone --depth 1 https://github.com/makerspet/oomwoo
git clone --depth 1 https://github.com/makerspet/oomwoo-one
git clone --depth 1 --filter=blob:none --no-checkout https://github.com/makerspet/oomwoo-cad

# 2) 取可信 lib/ 驱动轮 STEP（不需要 447 MB 全量 checkout）
git -C oomwoo-cad show HEAD:lib/roborock/OOM-W01-drive-wheel-assembly.stp > drive_wheel.stp
sha256sum drive_wheel.stp
# 期望：101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2

# 3) 复算轮体（需要 Python + gmsh + numpy；版本见尺寸表）
python docs/基准机型/scripts/step_component_properties.py \
  drive_wheel.stp --tag 3 --axis z \
  --rho 1100 --rho-alt 1240 \
  --name oomwoo-drive-wheel \
  --source 'oomwoo-cad@266210a:lib/roborock/OOM-W01-drive-wheel-assembly.stp' \
  --outdir docs/基准机型 \
  --script-rev bdf5be26c68206f972d09f1c1e6d526366fc5b33 \
  --table-rev 0b73edaad9a4929bc945f358c31dcc427d738d27
```

文件：

- `docs/基准机型/oomwoo-drive-wheel-dimensions.md` — S17 血缘 + `param_id/value/unit/method_note`
- `docs/基准机型/oomwoo-drive-wheel-dimensions.csv` — 同表 CSV
- `docs/基准机型/oomwoo-drive-wheel-metrics.json` — 原始数值
- `docs/基准机型/oomwoo-drive-wheel-solids.csv` — 3 个实体的体积/CoM/bbox（审计用）
- `docs/基准机型/scripts/step_component_properties.py` — 推导脚本
