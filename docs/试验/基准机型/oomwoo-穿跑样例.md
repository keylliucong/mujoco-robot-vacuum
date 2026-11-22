# oomwoo 基准机型｜端到端穿跑样例

- 日期：2026-11-22
- 目的：用 `makerspet/oomwoo` 的公开资料，把“取数 → 资产盘点 → 标签 → 台账 → 不确定度预算 → 报告骨架”这条**试验侧**链条走一遍，暴露字段、来源和 3D 数据的缺口。
- 边界：**不跑 MuJoCo**、不改 `models/*.xml`、不写 `params/*.json` 的仿真字段、不实测。所有值只能是【公开参考】或【工程假设】；本文件没有【本机实测】。
- 基准机型不是本机型：`machine=oomwoo` 只作对标与敏感性，不得把它的数当自家实测，也不得把两套几何拼成一台机器。

## 1. 参数表（带标签与来源）

只列有可追溯值的整机参数；缺失项见 §5。来源写法：`source=…; retrieved=2026-11-22; rev=<sha>#<path>`。

| `param_id` | 值 | 单位 | 标签 | 来源 | 备注 |
|---|---:|---|---|---|---|
| `body_diameter` | 349 | mm | 公开参考 | `source=oomwoo docs/ARCHITECTURE.md §4/§5.1; rev=0218857#docs/ARCHITECTURE.md`；`source=oomwoo-one urdf/params.xacro; rev=a630d1c#urdf/params.xacro` | 文档写“约 349 mm 圆体基线”；设计值，不是实测 |
| `body_height` | 95 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro 注释; rev=a630d1c#urdf/params.xacro` | 同文件几何推算 97 mm，差 2 mm |
| `wheel_track` | 235 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro; rev=a630d1c#urdf/params.xacro` | 同文件 bridge 常量 233 mm，差 2 mm |
| `wheelbase` | 144.5 | mm | 公开参考 | `source=oomwoo-one urdf/robot.urdf.xacro caster_joint; rev=a630d1c#urdf/robot.urdf.xacro` | 由 `174.5 − 30` 推算；定义=驱动轮轴→从动轮中心 |
| `hub_z` | 34.0 | mm | 公开参考 | `source=oomwoo-one urdf/robot.urdf.xacro wheel_joint; rev=a630d1c#urdf/robot.urdf.xacro` | 轮心高度=`wheel_diameter/2`；与组件 STEP 的 35.805 mm 冲突 |
| `r_wheel` | 34.0 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro wheel_diameter=0.068; rev=a630d1c#urdf/params.xacro` | 第三方实测轮径 71.5 mm；组件 STEP 71.61 mm；三者不混用 |
| `caster_diameter` | 25 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro caster_diameter=0.025; rev=a630d1c#urdf/params.xacro` | URDF 球径；实物外形约 46×52 mm，不是滚动半径 |
| `com_x` | +2.2 | mm | 公开参考 | `source=oomwoo-one urdf/params.xacro 注释; rev=a630d1c#urdf/params.xacro` | 只给 x；按同一 URDF 复算 +6.19 mm，差 3.99 mm |
| `i_gear` | 65.36 | 1 | 公开参考 | `source=oomwoo contributions/part-specs/IKsares/drive-wheel/README.md §5; rev=0218857#contributions/part-specs/IKsares/drive-wheel/README.md` | 第三方单件齿数实测；同文另列 ~190:1 旧推算 |
| `T_wheel` | 0.5 | N·m | 公开参考 | `source=oomwoo-one urdf/params.xacro motor_stall_torque=0.5; rev=a630d1c#urdf/params.xacro` | 这是 joint `effort` 上限，不是实测轮端扭矩 |
| `m_drive_module_pair` | 0.463 | kg | 公开参考 | `source=oomwoo contributions/part-specs/OsakaTX/README.md §Wheel Module Weight; rev=0218857#contributions/part-specs/OsakaTX/README.md` | 商品页 listing 值，非实测；只作量级 |

> 组件级（驱动轮轮体）另有 5 个值：`r_wheel_lib_step=35.805 mm`、`wheel_width_lib_step=15.760 mm`、`wheel_Ixx_lib_step=2.00e-05 kg·m²`、`wheel_Izz_lib_step=3.77e-05 kg·m²` 已按 S17 四项记【图纸推算】（无实测交叉校核，止于 `sensitivity`）；`wheel_mass_lib_step=0.0623 kg` 因密度是假设，仍记【工程假设】。原因见 §5。

## 2. 台账行（`machine=oomwoo`）

完整行在 `docs/参数溯源.csv`；这里只摘录关键行，便于看标签与来源是否一致。

| `param_id` | 值 | 标签 | `ref` 摘要 | `verified_tol` |
|---|---:|---|---|---|
| `body_diameter` | 349 mm | 公开参考 | `machine=oomwoo; rev=0218857#docs/ARCHITECTURE.md` | 空 |
| `r_wheel` | 34.0 mm | 公开参考 | `machine=oomwoo; rev=a630d1c#urdf/params.xacro` | 空 |
| `i_gear` | 65.36 | 公开参考 | `machine=oomwoo; rev=0218857#contributions/part-specs/IKsares/...` | 空 |
| `m_dry` | — | 缺失 | `machine=oomwoo; URDF 占位质量未入 value` | 空 |
| `com_z` | — | 缺失 | `machine=oomwoo; 扫描范围未建立` | 空 |
| `Ixx/Iyy/Izz` | — | 缺失 | `machine=oomwoo; ref_point=body_CoM; axes=B` | 空 |
| `k_susp/F0/c_susp/travel` | — | 缺失 | `machine=oomwoo` | 空 |
| `r_wheel_lib_step` | 35.805 mm | 图纸推算 | `machine=oomwoo; rev=b996dc0#docs/基准机型/oomwoo-drive-wheel-dimensions.md` | 空 |

规则检查：

- 所有行 `ref` 都带 `machine=oomwoo`；没有一行的 `label` 是【本机实测】。
- `m_dry`、`com_y/z`、惯量、悬挂都以**行**的形式存在，值为空；没有用“没这一行”表达缺失。
- `verified_tol` 全为空；有 `u_B pending` 就不许填 0 或估计值。
- 组件级 `r_wheel_lib_step`、`wheel_width_lib_step`、`wheel_Ixx/Izz_lib_step` 已按 S17 四项入【图纸推算】；无实测交叉校核，止于 `sensitivity`。`wheel_mass_lib_step` 因密度假设仍是【工程假设】。

## 3. 不确定度预算（哪些分量 `pending`）

完整行在 `docs/不确定度预算.csv`。这里只列 oomwoo 的公开参考来源分量；**没有一条是 `evaluated`**。

| `unc_id` | `param_id` | `component` | `status` | 为什么不是 `evaluated` |
|---|---|---|---|---|
| `unc.oomwoo.body_diameter.source_doc` | `body_diameter` | `instrument` | `assumed` | 设计基线，不是本机测量；无证书/量程 |
| `unc.oomwoo.body_height.source_doc` | `body_height` | `instrument` | `pending` | 同一文件 95/97 mm 冲突 |
| `unc.oomwoo.wheel_track.source_doc` | `wheel_track` | `instrument` | `pending` | 235/233 mm 冲突 |
| `unc.oomwoo.wheelbase.source_doc` | `wheelbase` | `instrument` | `assumed` | 由两个设计值几何推算 |
| `unc.oomwoo.hub_z.source_doc` | `hub_z` | `instrument` | `assumed` | 由轮径/2 推算；与组件 STEP 冲突 |
| `unc.oomwoo.r_wheel.source_doc` | `r_wheel` | `instrument` | `pending` | 68/71.5/71.61 mm 冲突 |
| `unc.oomwoo.caster_diameter.source_doc` | `caster_diameter` | `instrument` | `pending` | URDF 球径与实物外形不同口径 |
| `unc.oomwoo.com_x.source_doc` | `com_x` | `instrument` | `pending` | +2.2/+6.19 mm 冲突 |
| `unc.oomwoo.i_gear.source_doc` | `i_gear` | `instrument` | `assumed` | 第三方单件实测转引；无本机证书/量程 |
| `unc.oomwoo.T_wheel.source_doc` | `T_wheel` | `instrument` | `pending` | URDF effort 上限，不是实测能力 |
| `unc.oomwoo.m_drive_module_pair.listing` | `m_drive_module_pair` | `instrument` | `pending` | 商品页 listing，非实测 |

> 三门槛（有效期、量程覆盖、适用条件覆盖）一条都不满足，所以没有 `evaluated`。按封顶规则：`pending` → 结论封顶 `mechanism`；`assumed` → 结论封顶 `sensitivity`。**不往上填。**
>
> `m_dry`、`com_z`、整机惯量、悬挂参数没有预算行：这些参数当前没有值，也就没有可评的分量；等有实测/可信来源后再建行。**“没有预算行”不等于“分量已评估为 0”。**

## 4. 报告骨架（两列等级）

> 本轮**没有** MuJoCo 读数，也没有实测读数；下表只展示报告骨架的字段与填法，不展示机器结果。`verified_tol` 统一填 `不可算（u_B pending）`，判定栏统一填 `N/A（u_B pending）`。不出现任何比率或百分比；不写高度类单点结论。

| field | 参数等级（label） | 结论等级（conclusion_level） | verified_tol | 读数 | A1–A4 | note |
|---|---|---|---|---|---|---|
| `m_dry` | 缺失 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | 无可靠整机质量；URDF 占位求和未入台账 |
| `com_z` | 缺失 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | `z_cg` 扫描范围未建立；不给单点 |
| `Ixx`/`Iyy`/`Izz` | 缺失 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | 无整机惯量；组件惯量不是整机 |
| `body_diameter` | 公开参考 | `sensitivity` | 不可算（u_B pending） | — | N/A（u_B pending） | 设计基线；预算分量 `assumed` |
| `wheel_track` | 公开参考 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | 235/233 mm 冲突；预算 `pending` |
| `r_wheel` | 公开参考 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | 68/71.5/71.61 mm 冲突；预算 `pending` |
| `i_gear` | 公开参考 | `sensitivity` | 不可算（u_B pending） | — | N/A（u_B pending） | 第三方单件实测；预算 `assumed` |
| `T_wheel` | 公开参考 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | URDF 占位；预算 `pending` |
| `r_wheel_lib_step` | 图纸推算 | `sensitivity` | 不可算（u_B pending） | — | N/A（u_B pending） | S17 四项齐；无实测交叉校核，止于 sensitivity |
| `k_susp`/`travel` | 缺失 | `mechanism` | 不可算（u_B pending） | — | N/A（u_B pending） | 静态 STEP/URDF 都给不出 |

两列的含义：

- **参数等级（label）**只回答“这个数从哪来”：`公开参考` = 文档/第三方公开值；`工程假设` = 缺证据的推算；`缺失` = 没有值。
- **结论等级（conclusion_level）**回答“这句话能说到多远”：先由 `label` 定基档，再由该参数全部 B 类分量的最差 `status` 封顶。`pending` → `mechanism`，`assumed` → `sensitivity`，全 `evaluated` 才可能到 `quantitative`。
- 本表**没有** `quantitative` 行；也不给结果判定。判定栏是 `N/A（u_B pending）`，表示前提缺失，不是“判了可能会过”。

## 5. 这条链跑通了什么、卡在哪

### 5.1 跑通了什么

1. **来源可登记**：两个仓库的 commit、License、取用子路径都固定在 `oomwoo-来源.md`；仓库内容不入库。
2. **3D 资产可盘点**：确认有 55 个 STEP（B-rep）和 13 个 Fusion 原生文件；没有 STL/DAE/OBJ；URDF 不在两个仓库内，而在 `oomwoo-one`。
3. **组件级准入可执行**：驱动轮组件表按 S17 四项逐项核，脚本、输入 `sha256`、输出表、环境四项均核实；几何量按【图纸推算】入账，质量因密度假设仍【工程假设】。表头 `table_rev` 用 CSV blob sha 而非 commit，是元数据缺陷，已单列。
4. **台账可落行**：37 行 `machine=oomwoo`，其中 11 行公开参考、4 行图纸推算、1 行工程假设、19 行缺失、2 行待标定；`verified_tol` 全空，没有伪造实测。
5. **预算可落行**：11 条公开参考来源分量，全部 `pending`/`assumed`，没有 `evaluated`；三门槛一条都不满足时不下填。
6. **报告骨架可穿跑**：两列等级、`verified_tol=不可算（u_B pending）`、判定=`N/A（u_B pending）`，没有比率、没有高度类单点结论。

### 5.2 卡在哪（按影响排序）

1. **没有正式整机 3D 数据。** `designs/one/stock/` 在本 rev 没有文件；唯一整机 STEP 是 `designs/one/agentic/july-2026/device_full.step`，同目录 README 明示“This is not the OOMWOO One design”，并列出脚轮装反、侧刷方向错误等已知缺陷。**整机 `m/com/I` 的源头不成立**，不是“算得准不准”的问题。
2. **整机 STEP 没有装配树。** 15.6 MiB 的文件只有 1 个 `PRODUCT('COMPOUND')`、63 个无名称 solid。驱动轮组、车体、悬挂件不能按名称分离；只能按几何启发式挑，误判风险高。**“能分离”在组件文件上成立，在整机上不成立。**
3. **STEP 不含材料密度。** 只能 `m=ρ·V`。实验件体积 1.4636 L，ρ=1240 时 1.81 kg，ρ=1000 时 1.46 kg；质量随 ρ 变。**没有 `rho_source`，`m` 只能【缺失】或【工程假设】**，不能当公开参考。
4. **`z_cg` 没有扫描范围。** 没有分件质量/密度，没有 `com_y/z` 公开值；实验件的 44.410 mm 只是均匀密度几何质心，且装配有摆位错误。报告只能写“扫描范围未建立”，不能写单点。
5. **URDF 的质量是占位值，且可能重复计数；inertial 还有坐标系错误。** 2.5 kg 筒身注释写“caster and battery weight”，又单列 0.05 kg 从动轮；求和 2.937 kg 不能当整机质量。`urdf/inertial.xacro` 给圆柱惯量加了 90° 的 `rpy`，而 visual 圆柱轴是 link z；`base_link` 的 inertial origin 在车体底面而不是圆柱中心。**质量、`z_cg`、整机惯量都不能直接取 URDF。**
6. **轮径/轮距/轴距/离地间隙全有冲突。** 轮径 68 / 71.5 / 71.61 mm；轮距 235 / 233 mm；实验件轮距 305.05 mm；轴距 144.5 / 140.08 mm；离地间隙 URDF 12.5 mm 只是 `base_link` 底面，实验件最低非轮点约 1.5 mm。**没有一个“唯一真值”能直接进模型。**
7. **悬挂参数完全缺失。** 静态 STEP 没有弹簧/运动副；URDF 的轮只有 continuous 转轴，没有悬挂平移。`k/F0/c/travel` 只能实测。
8. **输出尺寸表的表头元数据有缺陷。** 表已在 `keylliucong/oomwoo-baseline-params@b996dc0` 推送；但表头 `table_rev=0b73eda` 是 CSV 的 blob sha，不是 commit，不能直接当 `rev=…#path` 用。本次引用实际表提交 `rev=b996dc0`，四项仍成立；表头语义需上游修正。**这不是数值错，是元数据写法错。**
9. **台账文件在 `main` 上不存在。** 本 PR 按契约 9 列/15 列新建 `docs/参数溯源.csv` 与 `docs/不确定度预算.csv`，只追加 `machine=oomwoo` 行；与模板分支合并时需要人工对表头/列名（尤其预算表 `label`→`status`）做一次核对。
10. **路径口径不一致。** 上游把尺寸表放在 `docs/基准机型/`，本任务要求 `docs/试验/基准机型/`。本 PR 不复制上游尺寸表，只在 `docs/试验/基准机型/` 写接收清单、参数与穿跑样例；**两份目录不能各养一套数**，后续要定一处为唯一来源。

### 5.3 这套数据能支撑到哪

- **能支撑**：机理层讨论、敏感性方向、把“基准机型”从空白变成有来源的对标对象；组件级轮径/轮宽/轮体惯量已可走【图纸推算】，但止于 `sensitivity`。
- **不能支撑**：任何整机定量结论、任何高度类判定、任何把 oomwoo 的几何当自家几何的模型。原因不是保守，是**整机质量/质心/惯量/悬挂的源头缺失**。

## 6. 复现与文件

```bash
# 只读克隆，放在仓库外；不提交仓库内容
git clone --depth 1 https://github.com/makerspet/oomwoo
git clone --depth 1 https://github.com/makerspet/oomwoo-one
git clone --depth 1 --filter=blob:none --no-checkout https://github.com/makerspet/oomwoo-cad

# 组件输入 sha256 复核
git -C oomwoo-cad show HEAD:lib/roborock/OOM-W01-drive-wheel-assembly.stp > drive_wheel.stp
sha256sum drive_wheel.stp
# 期望 101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2
```

本目录文件：

- `oomwoo-来源.md` — 仓库、commit、License、取用子路径
- `oomwoo-资产盘点.md` — 55 个 STEP + 原生 CAD 的格式、单位、装配、可分离性
- `接收清单.md` — 要哪些 `param_id`、必填元数据、`z_cg` 专门要求
- `oomwoo-参数.md` — 参数总表、S17 准入核查、冲突、覆盖率
- `oomwoo-穿跑样例.md` — 本文件
