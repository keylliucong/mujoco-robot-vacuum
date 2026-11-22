"""MuJoCo 接触力读数校验：三档静置工况 × 两种摩擦锥。

在 Windows 项目目录执行：
    .venv\\Scripts\\python.exe scripts\\verify_env.py

读数口径（与 docs/接触力读数校验.md 一致）：
- 只用 mujoco.mj_contactForce 读取接触力。返回值为接触帧下的六维力/力矩，
  第 0 分量为法向、第 1~2 分量为切向（N），第 3~5 分为力矩（N·m）。
- 接触帧第一轴为法向（d.contact[i].frame 前三项），世界分量用 frame^T 旋转。
- 符号：力由 geom1 指向 geom2，即对第二个 geom 为正；本脚本约定地面/斜面为
  geom1、被支撑物体为 geom2，输出中打印两个 geom 的名称。
- 不使用 efc_force 行求和。

工况：
1. flat_sphere：球静置在平面，ΣFn = m*g（±1%）。
2. incline_box：30° 斜面静置（μ=1.0 ≥ tan30），|Fn| = m*g*cos30（±1%）、
   |Ft| = m*g*sin30（±2%），接触合力竖直分量 = m*g（±1%）。用方块而不是球，
   避免无滚阻的球在斜面上必然滚动；方块同时检验接触帧旋转和切向分解。
3. double_mass：球密度 ×2，Fn 应同步翻倍（±1%）。

两种摩擦锥各跑一遍（mjCONE_PYRAMIDAL / mjCONE_ELLIPTIC）。平地静置没有切向
需求，两锥应只差求解器容差：法向差 ≤0.5% 直接通过，0.5%~1% 通过但记录，
>1% 判实现错误。输出全部为 ASCII，便于 Windows 重定向保存。

数值设置：全部工况用 timestep=0.5 ms、solref=0.005 s、solimp=0.999/0.9999。
斜面持续受切向重力分量，MuJoCo 的软接触约束会产生与刚度成反比的蠕滑；提高
阻抗并减小时间步后，斜面残余速度约 1e-5 m/s、抽样窗口漂移约 1e-3 mm。该设置
只用于静置读数校验，不代表整机模型的时间步或接触柔度。
"""

import sys

import mujoco
import numpy as np

RADIUS = 0.1            # m
HALF_EXTENT = 0.1       # m，斜面方块的半边长
DENSITY = 1000.0        # kg/m^3（MuJoCo 默认值，这里显式写出）
GRAVITY = 9.81          # m/s^2
TIMESTEP = 0.0005       # s（高阻抗接触下的稳定性要求，见文档）
SOLREF = "0.005 1"
SOLIMP = "0.999 0.9999 0.0001"
DROP_HEIGHT = 0.4       # m，球心初始高度
INCLINE_DEG = 30.0      # deg
SLIDE_FRICTION = 1.0    # ≥0.6，且 > tan30
SETTLE_MAX_STEPS = 12000
SETTLE_QUIET_STEPS = 50
SETTLE_VEL = 1e-4       # m/s, rad/s
SAMPLE_STEPS = 100
ERROR_NORMAL = 0.01     # 1%
ERROR_TANGENT = 0.02    # 2%
CONE_EQUIV_PASS = 0.005  # 0.5%
CONE_EQUIV_RECORD = 0.01  # 1%
PENETRATION_LIMIT = 0.05  # 5% of radius / half extent
DRIFT_LIMIT = 1e-3        # 抽样窗口内质心漂移 < 0.1% of reference length
TORQUE_LIMIT = 1e-6     # N·m，condim=3 的点接触无力矩

FLAT_XML = """
<mujoco model="contact-force-flat">
  <option timestep="{timestep}" gravity="0 0 -{gravity}" cone="{cone}"
          solver="Newton" iterations="200" tolerance="1e-10" integrator="Euler"/>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.1" solref="{solref}" solimp="{solimp}"
          friction="{mu} 0.01 0.01" condim="3"/>
    <body name="ball" pos="0 0 {drop}">
      <joint type="free"/>
      <geom name="ball" type="sphere" size="{radius}" density="{density}"
            solref="{solref}" solimp="{solimp}"
            friction="{mu} 0.01 0.01" condim="3"/>
    </body>
  </worldbody>
</mujoco>
"""

INCLINE_XML = """
<mujoco model="contact-force-incline">
  <option timestep="{timestep}" gravity="0 0 -{gravity}" cone="{cone}"
          solver="Newton" iterations="200" tolerance="1e-10" integrator="Euler"/>
  <worldbody>
    <geom name="incline" type="plane" size="0 0 0.1" euler="0 {angle} 0"
          solref="{solref}" solimp="{solimp}"
          friction="{mu} 0.01 0.01" condim="3"/>
    <body name="block" pos="{px} 0 {pz}" quat="{qw} 0 {qy} 0">
      <joint type="free"/>
      <geom name="block" type="box" size="{half} {half} {half}" density="{density}"
            solref="{solref}" solimp="{solimp}"
            friction="{mu} 0.01 0.01" condim="3"/>
    </body>
  </worldbody>
</mujoco>
"""

CONES = (
    ("pyramidal", mujoco.mjtCone.mjCONE_PYRAMIDAL),
    ("elliptic", mujoco.mjtCone.mjCONE_ELLIPTIC),
)


def build_flat_model(cone_name: str, density: float) -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_string(
        FLAT_XML.format(
            timestep=TIMESTEP,
            gravity=GRAVITY,
            cone=cone_name,
            mu=SLIDE_FRICTION,
            drop=DROP_HEIGHT,
            radius=RADIUS,
            density=density,
            solref=SOLREF,
            solimp=SOLIMP,
        )
    )


def build_incline_model(cone_name: str) -> mujoco.MjModel:
    angle = np.deg2rad(INCLINE_DEG)
    half_angle = angle / 2.0
    # 平面法向 = R_y(angle) * z；方块中心放在法向上方半个边长处，留 2 mm 初始间隙。
    standoff = HALF_EXTENT + 0.002
    return mujoco.MjModel.from_xml_string(
        INCLINE_XML.format(
            timestep=TIMESTEP,
            gravity=GRAVITY,
            cone=cone_name,
            mu=SLIDE_FRICTION,
            angle=INCLINE_DEG,
            half=HALF_EXTENT,
            density=DENSITY,
            px=float(np.sin(angle) * standoff),
            pz=float(np.cos(angle) * standoff),
            qw=float(np.cos(half_angle)),
            qy=float(np.sin(half_angle)),
            solref=SOLREF,
            solimp=SOLIMP,
        )
    )


def pair_contact_ids(model, data, ground_id: int, object_id: int):
    return [
        i
        for i in range(data.ncon)
        if {int(data.contact[i].geom1), int(data.contact[i].geom2)}
        == {ground_id, object_id}
    ]


def geom_name(model, gid: int) -> str:
    return mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid) or f"geom{gid}"


def run_case(case: dict, cone_name: str, expected_cone: int) -> dict:
    if case["kind"] == "incline":
        model = build_incline_model(cone_name)
    else:
        model = build_flat_model(cone_name, case["density"])

    data = mujoco.MjData(model)
    ground_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, case["ground"])
    object_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, case["object"])
    object_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, case["object"])
    mass = float(model.body_mass[object_body])
    weight = mass * GRAVITY

    # 1) 静置：连续若干步线速度、角速度都低于阈值。
    quiet = 0
    settle_steps = 0
    for _ in range(SETTLE_MAX_STEPS):
        mujoco.mj_step(model, data)
        settle_steps += 1
        lin_vel = float(np.linalg.norm(data.qvel[0:3]))
        ang_vel = float(np.linalg.norm(data.qvel[3:6]))
        has_contact = bool(pair_contact_ids(model, data, ground_id, object_id))
        if has_contact and max(lin_vel, ang_vel) < SETTLE_VEL:
            quiet += 1
        else:
            quiet = 0
        if quiet >= SETTLE_QUIET_STEPS:
            break
    settled = quiet >= SETTLE_QUIET_STEPS
    final_lin_vel = float(np.linalg.norm(data.qvel[0:3]))
    final_ang_vel = float(np.linalg.norm(data.qvel[3:6]))

    # 2) 采样：每步 mj_step 之后立即读取当前帧接触力，不用上一帧。
    fn_local = np.zeros(SAMPLE_STEPS)
    f_world = np.zeros((SAMPLE_STEPS, 3))
    ft_world = np.zeros(SAMPLE_STEPS)
    fz_world = np.zeros(SAMPLE_STEPS)
    normal_vec = np.zeros(3)
    max_torque = 0.0
    contact_counts = []
    centers = np.zeros((SAMPLE_STEPS, 3))
    geom_order = "n/a"
    swapped = False
    for k in range(SAMPLE_STEPS):
        mujoco.mj_step(model, data)
        ids = pair_contact_ids(model, data, ground_id, object_id)
        if not ids:
            raise RuntimeError(f"{case['name']}/{cone_name}: lost contact during sampling")
        contact_counts.append(len(ids))
        step_world = np.zeros(3)
        step_fn = 0.0
        for cid in ids:
            c = data.contact[cid]
            names = (geom_name(model, int(c.geom1)), geom_name(model, int(c.geom2)))
            geom_order = f"{names[0]}/{names[1]}"
            if names[0] == case["object"]:
                swapped = True
            frame = np.array(c.frame, dtype=float).reshape(3, 3)
            force_local = np.zeros(6)
            mujoco.mj_contactForce(model, data, cid, force_local)
            normal_vec += frame[0]
            step_fn += float(force_local[0])
            step_world += frame.T @ force_local[0:3]
            max_torque = max(max_torque, float(np.linalg.norm(force_local[3:6])))
        fn_local[k] = step_fn
        f_world[k] = step_world
        fz_world[k] = step_world[2]
        centers[k] = data.qpos[0:3]
    normal_vec /= max(1, int(np.sum(contact_counts)))
    normal_vec /= np.linalg.norm(normal_vec)
    fn_world = f_world @ normal_vec
    ft_vec = f_world - np.outer(fn_world, normal_vec)
    ft_world = np.linalg.norm(ft_vec, axis=1)

    # 3) 静置漂移与穿透。
    if case["kind"] == "incline":
        penetration = float(HALF_EXTENT - np.mean(centers @ normal_vec))
    else:
        penetration = float(RADIUS - np.mean(centers[:, 2]))
    penetration_ratio = penetration / case["penetration_ref"]
    center_drift = float(np.linalg.norm(centers[-1] - centers[0]))
    drift_ratio = center_drift / case["penetration_ref"]

    warnings = np.asarray(data.warning.number)
    warning_count = int(np.count_nonzero(warnings))
    finite = bool(
        np.isfinite(f_world).all()
        and np.isfinite(fn_local).all()
        and np.isfinite(data.qpos).all()
        and np.isfinite(data.qvel).all()
    )

    expected_fn = weight * case["fn_factor"]
    expected_ft = weight * case["ft_factor"]
    fn_mean = float(fn_local.mean())
    ft_mean = float(ft_world.mean())
    fz_mean = float(fz_world.mean())
    err_fn = (fn_mean - expected_fn) / expected_fn
    err_ft = (ft_mean - expected_ft) / expected_ft if expected_ft else None
    err_fz = (fz_mean - weight) / weight

    order_ok = geom_order == f"{case['ground']}/{case['object']}"
    flat_tangent_ok = expected_ft != 0 or ft_mean <= 1e-3 * weight

    checks = {
        "cone": int(model.opt.cone) == expected_cone,
        "geom order": order_ok and not swapped,
        "settled": settled,
        "normal": abs(err_fn) <= ERROR_NORMAL,
        "tangential": (abs(err_ft) <= ERROR_TANGENT) if expected_ft else flat_tangent_ok,
        "vertical": abs(err_fz) <= ERROR_NORMAL,
        "penetration": penetration_ratio <= PENETRATION_LIMIT,
        "static drift": drift_ratio <= DRIFT_LIMIT,
        "warnings": warning_count == 0,
        "finite": finite,
        "torque": max_torque <= TORQUE_LIMIT,
    }

    print()
    print(f"--- case={case['name']}  cone={cone_name} "
          f"(mjCONE_{cone_name.upper()}={int(expected_cone)}) ---")
    print(f"model.opt.cone:            {int(model.opt.cone)} (expected {int(expected_cone)})")
    print(f"model.opt.solver:          {mujoco.mjtSolver(model.opt.solver).name} "
          f"({int(model.opt.solver)})")
    print(f"model.opt.timestep:        {model.opt.timestep} s, "
          f"iterations={int(model.opt.iterations)}, tolerance={model.opt.tolerance:g}")
    print(f"contact solref/solimp:     {SOLREF} / {SOLIMP}")
    print(f"geom1/geom2:               {geom_order}  (force positive on geom2)")
    print(f"condim ground/object:      {int(model.geom_condim[ground_id])}/"
          f"{int(model.geom_condim[object_id])}")
    print(f"friction ground/object:    "
          f"{np.round(model.geom_friction[ground_id], 4).tolist()}/"
          f"{np.round(model.geom_friction[object_id], 4).tolist()}")
    print(f"mass (model.body_mass):    {mass:.6f} kg")
    print(f"m*g:                       {weight:.6f} N")
    print(f"settle steps:              {settle_steps} (settled={settled})")
    print(f"residual |v|, |w|:         {final_lin_vel:.3e} m/s, {final_ang_vel:.3e} rad/s")
    print(f"center drift (sample):     {center_drift * 1000:.6f} mm "
          f"({drift_ratio * 100:.6f} % of reference)")
    print(f"sample steps:              {SAMPLE_STEPS}, contacts per sample "
          f"{min(contact_counts)}..{max(contact_counts)}")
    print(f"contact normal (world):    [{normal_vec[0]: .6f} {normal_vec[1]: .6f} "
          f"{normal_vec[2]: .6f}]")
    print(f"Fn  expected (m*g*{case['fn_factor']:.4f}): {expected_fn:.6f} N")
    print(f"Fn  measured (sum res[0]): {fn_mean:.9f} N "
          f"(min {fn_local.min():.9f}, max {fn_local.max():.9f})")
    print(f"Fn  measured (R^T sum):    {float(fn_world.mean()):.9f} N")
    print(f"Fn  error:                 {err_fn * 100:+.6f} %")
    if expected_ft:
        print(f"Ft  expected (m*g*{case['ft_factor']:.4f}): {expected_ft:.6f} N")
        print(f"Ft  measured:              {ft_mean:.9f} N")
        print(f"Ft  error:                 {err_ft * 100:+.6f} %")
    else:
        print(f"Ft  measured (expect 0):   {ft_mean:.9e} N")
    print(f"Fz  world (expect m*g):    {fz_mean:.9f} N ({err_fz * 100:+.6f} %)")
    print(f"max |torque|:              {max_torque:.3e} N*m")
    print(f"penetration:               {penetration * 1000:.6f} mm "
          f"({penetration_ratio * 100:.4f} % of reference)")
    print(f"warning.number nonzero:    {warning_count} {warnings.tolist()}")
    print(f"finite:                    {finite}")
    for key, value in checks.items():
        print(f"check {key:<14} {'PASS' if value else 'FAIL'}")
    print(f"RESULT:                    {'PASS' if all(checks.values()) else 'FAIL'}")

    return {
        "case": case["name"],
        "cone": cone_name,
        "mass": mass,
        "weight": weight,
        "fn_expected": expected_fn,
        "fn_measured": fn_mean,
        "ft_expected": expected_ft,
        "ft_measured": ft_mean,
        "fz_measured": fz_mean,
        "err_fn": err_fn,
        "err_ft": err_ft,
        "err_fz": err_fz,
        "geom_order": geom_order,
        "penetration": penetration,
        "warnings": warning_count,
        "ok": all(checks.values()),
    }


def main() -> int:
    cases = (
        {
            "name": "flat_sphere",
            "kind": "flat",
            "density": DENSITY,
            "ground": "floor",
            "object": "ball",
            "fn_factor": 1.0,
            "ft_factor": 0.0,
            "penetration_ref": RADIUS,
        },
        {
            "name": "incline_box",
            "kind": "incline",
            "density": DENSITY,
            "ground": "incline",
            "object": "block",
            "fn_factor": float(np.cos(np.deg2rad(INCLINE_DEG))),
            "ft_factor": float(np.sin(np.deg2rad(INCLINE_DEG))),
            "penetration_ref": HALF_EXTENT,
        },
        {
            "name": "double_mass",
            "kind": "flat",
            "density": DENSITY * 2.0,
            "ground": "floor",
            "object": "ball",
            "fn_factor": 1.0,
            "ft_factor": 0.0,
            "penetration_ref": RADIUS,
        },
    )

    print("=== MuJoCo contact force readout check ===")
    print(f"Python:                    {sys.version.split()[0]}")
    print(f"MuJoCo:                    {mujoco.__version__}")
    print(f"NumPy:                     {np.__version__}")
    print(f"Executable:                {sys.executable}")
    print(f"gravity:                   {GRAVITY} m/s^2, timestep={TIMESTEP} s")
    print(f"error limits:              normal {ERROR_NORMAL * 100:.0f}%, "
          f"tangential {ERROR_TANGENT * 100:.0f}%, cone equivalence "
          f"{CONE_EQUIV_PASS * 100:.1f}%/record {CONE_EQUIV_RECORD * 100:.1f}%")
    print("force source:              mujoco.mj_contactForce only (contact frame; "
          "0=normal, 1-2=tangential, 3-5=torque)")

    results = []
    for case in cases:
        for cone_name, cone_enum in CONES:
            results.append(run_case(case, cone_name, cone_enum))

    # 两种摩擦锥在平地静置的等效性（只要没有切向需求）。
    flat = {(r["case"], r["cone"]): r for r in results if r["case"] == "flat_sphere"}
    p = flat[("flat_sphere", "pyramidal")]
    e = flat[("flat_sphere", "elliptic")]
    mean_fn = 0.5 * (p["fn_measured"] + e["fn_measured"])
    cone_diff = abs(p["fn_measured"] - e["fn_measured"]) / mean_fn
    if cone_diff <= CONE_EQUIV_PASS:
        cone_equiv = "PASS"
    elif cone_diff <= CONE_EQUIV_RECORD:
        cone_equiv = "PASS (recorded 0.5-1%)"
    else:
        cone_equiv = "FAIL"

    # 密度翻倍后法向力应同步翻倍。
    f1 = flat[("flat_sphere", "pyramidal")]["fn_measured"]
    f2 = [r for r in results if r["case"] == "double_mass" and r["cone"] == "pyramidal"][0]
    ratio = f2["fn_measured"] / f1
    ratio_error = (ratio - 2.0) / 2.0

    print()
    print("=== SUMMARY (mean over 100 samples after settling) ===")
    print(f"{'case':<14}{'cone':<11}{'Fn_exp':>12}{'Fn_meas':>14}{'err_%':>10}"
          f"{'Ft_exp':>11}{'Ft_meas':>12}{'err_%':>10}{'Fz_err_%':>10}  result")
    for r in results:
        ft_err = f"{r['err_ft'] * 100:+.6f}" if r["err_ft"] is not None else "-"
        print(f"{r['case']:<14}{r['cone']:<11}{r['fn_expected']:>12.6f}"
              f"{r['fn_measured']:>14.9f}{r['err_fn'] * 100:>+10.6f}"
              f"{r['ft_expected']:>11.6f}{r['ft_measured']:>12.9f}{ft_err:>10}"
              f"{r['err_fz'] * 100:>+10.6f}  {'PASS' if r['ok'] else 'FAIL'}")

    print()
    print(f"flat_sphere cone equivalence (normal force): {cone_diff * 100:.6f} % "
          f"-> {cone_equiv}")
    print(f"double_mass / flat_sphere Fn ratio (pyramidal): {ratio:.9f} "
          f"(expected 2.000000000, error {ratio_error * 100:+.6f} %)")

    overall = all(r["ok"] for r in results) and cone_equiv.startswith("PASS") \
        and abs(ratio_error) <= ERROR_NORMAL
    print()
    print("CONTACT FORCE CHECK:", "PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
