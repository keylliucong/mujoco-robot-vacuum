# OOMWOO 组件 STEP 尺寸表（S17 准入）：`oomwoo-drive-wheel`

- generated_by=`docs/基准机型/scripts/step_component_properties.py@32faa7d9fb0e4cb27971ddbd98c96b2132e60513`
- table_rev=`0b73edaad9a4929bc945f358c31dcc427d738d27`
- table_rev_note=上一条是尺寸表 CSV 的 blob sha，**非 commit**；内容寻址。本行为人工注记（脚本不生成），重算时保留。
- source=`oomwoo-cad@266210a:lib/roborock/OOM-W01-drive-wheel-assembly.stp`
- input_file=`drive_wheel.stp` (829986 bytes)
- input_sha256=`101bd1ef763c3b11fe60dd31274b58afc26cd071d1205c8a210f7c74020e2fe2`
- input_warning=`gmsh/StepReaderData: Unresolved Reference, Fails Count: 1; 3 solids imported; wheel solid complete, whole-module mass/inertia not used`
- selected_tag=`3` (of 3 solids)
- selected_axis=`z`
- method=`brep_exact`
- mesh_export=`none`
- chord_tol=`N/A` (B-rep exact; no tessellation)
- angle_tol=`N/A` (B-rep exact; no tessellation)
- env=`Python 3.13.18; gmsh 4.15.2; NumPy 2.5.5; Open CASCADE bundled with gmsh (exact OCC version not exposed by gmsh API)`
- rho_primary=`1100 kg/m^3`; rho_alt=`1240 kg/m^3`
- frame=`STEP frame as exported; no B-frame rotation applied to a component`

| param_id | value | unit | method_note |
|---|---|---|---|
| `geom.component.bbox.x_mm` | 71.6099568158 | mm | OCC B-rep bbox of the selected solid; STEP frame; no mesh. |
| `geom.component.bbox.y_mm` | 71.6099568158 | mm | OCC B-rep bbox of the selected solid; STEP frame; no mesh. |
| `geom.component.bbox.z_mm` | 15.7599568158 | mm | OCC B-rep bbox of the selected solid; STEP frame; no mesh. |
| `geom.component.wheel.diameter_mm` | 71.6099568158 | mm | Mean of the two extents perpendicular to the z axle axis; selected solid tag 3; STEP frame. |
| `geom.component.wheel.width_mm` | 15.7599568158 | mm | Extent along the z axle axis; selected solid tag 3; STEP frame. |
| `mass.volume_m3` | 5.66060036894e-05 | m^3 | B-rep volume of the selected solid; no mesh. |
| `mass.kg_at_rho_1100` | 0.0622666040583 | kg | V * rho; rho is an explicit assumption, not a STEP material. |
| `mass.kg_at_rho_1240` | 0.0701914445748 | kg | V * rho; alternate density for scale comparison; same caveat. |
| `com.x_mm` | 3.56655101957e-05 | mm | Volume centroid of the selected solid; STEP frame; density-independent. |
| `com.y_mm` | -5.25775465906e-05 | mm | Volume centroid of the selected solid; STEP frame; density-independent. |
| `com.z_mm` | -7.91437944255 | mm | Volume centroid of the selected solid; STEP frame; density-independent. |
| `inertia.Ixx_kgm2` | 1.99799767437e-05 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.Iyy_kgm2` | 1.99800262779e-05 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.Izz_kgm2` | 3.76659993087e-05 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.Ixy_kgm2` | -6.22109464708e-11 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.Ixz_kgm2` | -1.5756494806e-11 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.Iyz_kgm2` | 2.32317945654e-11 | kg*m^2 | B-rep exact GProp matrix about the selected solid's CoM, scaled by rho=1100; STEP frame; no mesh. |
| `inertia.principal.1_kgm2` | 1.9979934551e-05 | kg*m^2 | Eigenvalue 1 of the selected solid's STEP-frame inertia tensor at rho=1100. |
| `inertia.principal.2_kgm2` | 1.99800684705e-05 | kg*m^2 | Eigenvalue 2 of the selected solid's STEP-frame inertia tensor at rho=1100. |
| `inertia.principal.3_kgm2` | 3.76659993088e-05 | kg*m^2 | Eigenvalue 3 of the selected solid's STEP-frame inertia tensor at rho=1100. |

> This table is for one trusted component, not for the whole machine. It must not be combined with another frame or another design without a documented transform.

## 与当前 MuJoCo 模型的关系：模型用的是 STEP 轮径，不是 URDF 的 68 mm

> 本节只说明“当前模型采用了哪套几何”，不改任何数值，也不把组件值升成整机值。

**逐项采用关系**

| 量 | 当前模型值 | 取自 | 出处 |
|---|---:|---|---|
| 整机 Ø349、离地 12.5 mm | Ø349 / 12.5 mm | U 套（URDF，公开参考） | `models/oomwoo.xml` 顶部几何注释 |
| 轮距 / 半轮距 | 235 / 117.5 mm | U 套（URDF） | `params/oomwoo_g25.json` 的 `pos.susp.y` |
| 从动轮位置 | +144.5 mm | U 套（URDF） | `models/oomwoo.xml` 顶部几何注释 |
| 驱动轮半径 | **R=35.805 mm（Ø71.61）** | **L 套（lib STEP 轮体）** | `params/oomwoo_g25.json` 的 `geom.wheel_radius_m`；`docs/试跑/参数溯源-oomwoo.csv` 的 `geom.wheel_radius_m` |
| 驱动轮全宽 / 半宽 | 15.76 / 7.88 mm | L 套（lib STEP 轮体） | `params/oomwoo_g25.json` 的 `geom.wheel_half_width_m`；`docs/试跑/参数溯源-oomwoo.csv` 的 `geom.wheel_half_width_m` |
| 驱动轮 link 质量 | 0.100 kg | U 套（URDF 参数；作者标注实测） | `params/oomwoo_g25.json` 的 `mass.wheel_L` |
| 轮体质量 / 惯量 | 未进入模型 | L 套只作敏感性上下界 | 本表 `mass.kg_at_rho_*`、`inertia.*` |

即当前模型是 **U 套整机布局 + L 套轮端几何** 的混合，不是 [参数提取 §5](oomwoo-参数提取.md) 建议的“U 套几何为主、L 套只做上下界”：**68 mm 没有进模型**，R=35.805 mm 才是现行值。

**数值链与边界**

- 模型的 `0.035805 m` 来自 #13/试跑这条线：`params/oomwoo_g25.json` 与 `docs/试跑/参数溯源-oomwoo.csv` 记的是 `script=scripts/step_mass_properties.py@e2952e9` + `table=docs/试跑/step-质量属性-逐实体-oomwoo.csv@dbdd34b`，输入仍是同一份 `OOM-W01-drive-wheel-assembly.stp`（sha256 相同）。这两个血缘文件目前不在仓库树里，是本 PR 之前的既有缺口，另行处理。
- 本 PR 的 `step_component_properties.py` + 本表是**同一输入上的另一条独立血缘**，B-rep 积分同样得到 71.61 / 15.76 mm。两者数值一致，但本表不是模型值的直接上游：引用模型值应引台账行（`params/oomwoo_g25.json` 的 `geom.wheel_radius_m`），引用几何复算才引本表。
- 因此读 h/R、轮速换算时，当前模型的 R 是 35.805 mm（h=10/20/30/40 mm → h/R=0.279/0.559/0.838/1.117），不是 34 mm（→ 0.294/0.588/0.882/1.176）。对 OOMWOO 基准，这一差约 5%，只能说明量级，不能当通过/不通过结论。
- 若要让 URDF 的 68 mm 做对照，另起 config/case 并在台账写明，不得静默改模型；也不得把 L 套的轮体质量/惯量替换进模型而不记来源。
- 等级不变：轮径仍是【图纸推算】（无实测交叉校核，止于 `sensitivity`）；整机结论仍受质量/质心/惯量/悬挂/摩擦的【缺失】封顶，见[缺口与影响](oomwoo-缺口与影响.md) §3。
