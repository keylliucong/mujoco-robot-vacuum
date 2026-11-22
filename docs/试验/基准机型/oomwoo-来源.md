# oomwoo 基准机型｜来源登记

- 登记日期：2026-11-22
- 用途：基准机型（`machine=oomwoo`）的公开资料与 3D 资产来源；**不是本机实测**。
- 边界：本文件只登记来源和取用范围，不复制仓库内容，不推导参数。

## 1. 仓库

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/makerspet/oomwoo` |
| 分支/提交 | `main` @ `0218857b2ecc53fb8e289b097b3bdf7a9e184386` |
| 获取日期 | 2026-11-22 |
| 获取方式 | `git clone --depth 1`，落在仓库外临时目录（未入库） |
| License | 代码 Apache-2.0（`LICENSE`）；README 注明“硬件设计文件加入后采用开放硬件许可（TBD）” |
| 项目状态 | README 明示 “Not buildable yet”，BOM 为 rough/work in progress |

| 项 | 值 |
|---|---|
| CAD 仓库 | `https://github.com/makerspet/oomwoo-cad` |
| 分支/提交 | `main` @ `266210a47cab931c5891a07c9a29d48388a54b0c` |
| 获取日期 | 2026-11-22 |
| 获取方式 | `git clone --depth 1 --filter=blob:none --no-checkout`；文件头/尾按需读取 |
| License | Apache-2.0（`LICENSE`） |
| 命名不一致 | `oomwoo` 的 `contributions/source-3d-models/README.md` 仍指向旧名 `makerspet/oomwoo-one-cad`；实际可访问的是 `makerspet/oomwoo-cad`。本文件以实际克隆的 `oomwoo-cad` 为准 |

> 两个仓库都只作**公开参考**使用。仓库内容不进入本仓库；如需复核，按上表 commit 重新克隆。

## 2. 我们取用的子路径

### 2.1 `makerspet/oomwoo`

| 子路径 | 用途 | 备注 |
|---|---|---|
| `BOM.md` | 选型、轮胎尺寸、驱动轮总成来源、整机预算 | work in progress；缺整机质量与质心 |
| `docs/design-document.md` | 设计取舍、约 10 cm 高度预算、打印/采购分工 | 无整机尺寸表 |
| `docs/ARCHITECTURE.md` | 机体系约定、约 349 mm 圆体基线（转引 URDF） | 明确 `base_link` 与整机尺寸“TBD” |
| `contributions/part-specs/IKsares/drive-wheel/README.md` | Roborock S5 Max 兼容驱动轮模块的实测规格：轮外径 71.5 mm、减速比 65.36:1、电机质量 66 g 等 | 第三方对实物单件的测量，按本项目口径记【公开参考】，不是本机实测 |
| `contributions/part-specs/OsakaTX/io-board-wheel-connector-and-caster.md` | 脚轮外形约 46×52 mm、驱动轮连接器与驱动方案 | 部分来自商品页转述 |
| `contributions/part-specs/Scowt/DriveWheel.md` | 驱动轮引脚与线长（自述“estimate only”） | 仅作线索，不进入参数台账 |
| `contributions/source-3d-models/README.md` | 声明 STEP 资产在 CAD 仓库的 `lib/`，以及资产准入要求（外形、安装特征、接口、来源） | 说明 3D 数据不是“整机设计图” |
| `contributions/urdf-gazebo-sim/README.md` | 指向独立 URDF/Gazebo 仓库 `makerspet/oomwoo-one`、`oomwoo_gazebo` | **本仓库内没有 URDF/SDF** |
| `contributions/stair-climbing/README.md` | 说明越障不是 v1 范围，无机构方案 | 不能作为越障机构依据 |

### 2.2 `makerspet/oomwoo-cad`

| 子路径 | 用途 | 备注 |
|---|---|---|
| `designs/one/agentic/july-2026/device_full.step` | 目前唯一的整机装配 STEP（15.6 MB） | **README 明示这是 agentic 实验 RV02，不是 OOMWOO One 设计**，且列出已知错误 |
| `designs/one/agentic/july-2026/README.md` | 该装配的来源、工具链、已知缺陷 | 判断能否作为基准机型几何的关键证据 |
| `designs/one/agentic/july-2026/OOMWOO_Device_RV02_Report.pdf` | 该实验的 9 页报告 | 管道自检报告，不是设计冻结文件 |
| `designs/one/fusion360/Top_Assembly_110926.f3z` | 实际设计链的 Fusion 360 顶层装配 | 原生格式，需 Fusion 360 打开；本仓库无其 STEP 整机导出 |
| `designs/one/fusion360/STEP/03-01 Motor_Gearbox.step` | 电机/减速箱子装配 STEP | 子装配，不是整机 |
| `designs/one/fusion360/STEP/03-02 Red_Brush_Gearbox_step.step` | 主刷齿轮箱子装配 STEP | 子装配，不是整机 |
| `lib/roborock/OOM-W01-drive-wheel-assembly.stp` | 驱动轮模块 STEP（单个模块） | 3D 扫描件，AP242；可单独分离驱动轮组 |
| `lib/casters/irobot_caster.step` | iRobot 脚轮 STEP | 3D 扫描件 |
| `lib/roborock/OOM-E01-battery.stp` | 电池 STEP | 3D 扫描件 |
| `lib/` 其余 STEP | 风扇、刷、LiDAR、CM4/CM5、传感器、开关等外购件 | 均为**零件级**资产，不是整机 |
| `docs/SPEC.md` | 选型与设计意图 | 明确“3D 设计规格”指向本仓库，但没有整机尺寸表 |

## 3. 取数纪律

1. 上述仓库的任何数值只记【公开参考】，不得写成本机实测。
2. 第三方贡献者对自己那件实物做的测量（如 `IKsares` 的 71.5 mm 轮径、66 g 电机质量）仍是**别人的实测**；进入本项目台账时只能是【公开参考】，并注明“第三方单件测量”。
3. 从 `device_full.step` 推算出的几何/质量属性，只有在推导脚本、输入 `sha256`、输出尺寸表、运行环境声明四项齐备时才可能记【图纸推算】；缺一降【工程假设】。
4. `device_full.step` 是实验装配而非正式设计，**即使四项齐备，也不能自动当作 OOMWOO One 的量产几何**；这一点在资产盘点和准入核查中单独标注。
