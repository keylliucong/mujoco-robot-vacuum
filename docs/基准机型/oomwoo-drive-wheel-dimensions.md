# OOMWOO 组件 STEP 尺寸表（S17 准入）：`oomwoo-drive-wheel`

- generated_by=`docs/基准机型/scripts/step_component_properties.py@bdf5be26c68206f972d09f1c1e6d526366fc5b33`
- table_rev=`0b73edaad9a4929bc945f358c31dcc427d738d27`
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