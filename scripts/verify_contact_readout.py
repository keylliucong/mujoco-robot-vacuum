"""接触力读数前置校验：落球静置，用 mj_contactForce 与球重对照。

要点
----
- 只从 ``mujoco.mj_contactForce`` 读取接触力：``res[0]`` 为法向，
  ``res[1..2]`` 为切向，``res[3..5]`` 为力矩；返回值在接触帧内，
  第一轴为法向。需要世界分量时用 ``data.contact[i].frame`` 旋转。
- ``efc_force`` 在金字塔锥下是棱边系数、不是力，禁止进入输出；本脚本
  只在调试文字里提示它被排除，不读取它做任何计算。
- 摩擦锥 ``pyramidal`` 与 ``elliptic`` 各跑一次，各自保留原始输出；
  两份输出的表头都写入两条的法向力与相对差。

作为 ``scripts/run_cases.py`` 的前置条件：``run_verification()`` 返回
``ok=False`` 时，批运行入口不得产出 ``summary.csv``。

在 Windows 项目目录执行：
    .venv\\Scripts\\python.exe scripts\\verify_contact_readout.py --out-dir docs\\验证输出
"""

from __future__ import annotations

import argparse
import datetime as _dt
import platform
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

ERROR_LIMIT_PCT = 1.0
TIMESTEP_S = 0.0005
SETTLE_STEPS = 1500
SAMPLE_STEPS = 100

CONES = ("pyramidal", "elliptic")


def _cone_enum(cone: str) -> int:
    if cone == "pyramidal":
        return int(mujoco.mjtCone.mjCONE_PYRAMIDAL)
    if cone == "elliptic":
        return int(mujoco.mjtCone.mjCONE_ELLIPTIC)
    raise ValueError(f"unknown cone: {cone}")


def build_xml(cone: str) -> str:
    """最小落球模型；所有参数只为读数校验构造，与整机原型无关。"""
    return f"""
<mujoco model="contact_readout">
  <option timestep="{TIMESTEP_S}" integrator="implicitfast"
          cone="{cone}" solver="Newton" iterations="200"
          tolerance="1e-10" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" size="2 2 0.1"
          friction="1 0.01 0.01" condim="3"
          solref="0.005 1" solimp="0.999 0.9999 0.0001"/>
    <body name="ball" pos="0 0 0.4">
      <freejoint name="ball_free"/>
      <geom name="ball" type="sphere" size="0.1" density="1000"
            friction="1 0.01 0.01" condim="3"
            solref="0.005 1" solimp="0.999 0.9999 0.0001"/>
    </body>
  </worldbody>
</mujoco>
"""


def _body_name(model: mujoco.MjModel, geom_id: int) -> str:
    return model.geom(geom_id).name or f"geom{geom_id}"


def run_cone(cone: str) -> dict:
    """跑一种摩擦锥，返回读数与检查结果。"""
    model = mujoco.MjModel.from_xml_string(build_xml(cone))
    data = mujoco.MjData(model)

    actual_cone = int(model.opt.cone)
    if actual_cone != _cone_enum(cone):
        raise RuntimeError(f"cone mismatch: requested {cone}, model has {actual_cone}")

    for _ in range(SETTLE_STEPS):
        mujoco.mj_step(model, data)

    # 抽样窗口
    forces = []
    fz_world = []
    tangentials = []
    torques = []
    positions = []
    penetrations = []
    contacts_per_sample = []
    geom_order = set()
    normals_world = []

    res = np.zeros(6, dtype=np.float64)
    for _ in range(SAMPLE_STEPS):
        mujoco.mj_step(model, data)
        fn_sum = 0.0
        fz_sum = 0.0
        ft_sum = 0.0
        tq_max = 0.0
        pen_max = 0.0
        for i in range(data.ncon):
            c = data.contact[i]
            mujoco.mj_contactForce(model, data, i, res)
            frame = np.asarray(c.frame, dtype=np.float64).reshape(3, 3)
            f_world = frame.T @ res[0:3]
            fn_sum += abs(float(res[0]))
            fz_sum += float(f_world[2])
            ft_sum += float(np.linalg.norm(res[1:3]))
            tq_max = max(tq_max, float(np.max(np.abs(res[3:6]))))
            pen_max = max(pen_max, max(0.0, -float(c.dist)))
            geom_order.add((_body_name(model, c.geom1), _body_name(model, c.geom2)))
            normals_world.append(f_world / max(np.linalg.norm(f_world), 1e-12))
        forces.append(fn_sum)
        fz_world.append(fz_sum)
        tangentials.append(ft_sum)
        torques.append(tq_max)
        positions.append(np.array(data.qpos[0:3], dtype=np.float64))
        penetrations.append(pen_max)
        contacts_per_sample.append(data.ncon)

    mass = float(model.body_mass[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "ball")])
    gravity = float(-model.opt.gravity[2])
    fn_expected = mass * gravity

    fn_mean = float(np.mean(forces))
    fz_mean = float(np.mean(fz_world))
    fn_error_pct = (fn_mean - fn_expected) / fn_expected * 100.0
    fz_error_pct = (fz_mean - fn_expected) / fn_expected * 100.0
    tangential_mean = float(np.mean(tangentials))
    drift_mm = float(np.linalg.norm(positions[-1][0:2] - positions[0][0:2]) * 1000.0)
    penetration_mm = float(max(penetrations) * 1000.0)
    warnings = int(np.sum(np.asarray(data.warning.number)))
    finite = bool(np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)))
    residual_speed = float(np.linalg.norm(data.qvel[0:3]))
    torque_max = float(max(torques))

    checks = {
        "cone": actual_cone == _cone_enum(cone),
        "geom_order": geom_order == {("floor", "ball")},
        "ncon": data.ncon == 1 and max(contacts_per_sample) == 1,
        "normal": abs(fn_error_pct) <= ERROR_LIMIT_PCT and abs(fz_error_pct) <= ERROR_LIMIT_PCT,
        "tangential": tangential_mean <= 1e-6,
        "settled": residual_speed <= 1e-4 and drift_mm <= 0.1,
        "penetration": penetration_mm <= 5.0,
        "warnings": warnings == 0,
        "finite": finite,
        "torque": torque_max <= 1e-9,
    }
    ok = all(checks.values())

    return {
        "cone": cone,
        "cone_id": actual_cone,
        "mass_kg": mass,
        "gravity_mps2": gravity,
        "fn_expected_n": fn_expected,
        "fn_mean_n": fn_mean,
        "fn_error_pct": fn_error_pct,
        "fz_mean_n": fz_mean,
        "fz_error_pct": fz_error_pct,
        "tangential_mean_n": tangential_mean,
        "torque_max_nm": torque_max,
        "residual_speed_mps": residual_speed,
        "drift_mm": drift_mm,
        "penetration_mm": penetration_mm,
        "warnings": warnings,
        "finite": finite,
        "ncon": int(data.ncon),
        "geom_order": sorted(geom_order),
        "normal_world": np.mean(np.asarray(normals_world), axis=0).tolist(),
        "checks": checks,
        "ok": ok,
    }


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _format_report(result: dict, other: dict, diff_pct: float) -> str:
    lines = []
    lines.append("=== MuJoCo contact force readout check ===")
    lines.append(f"Python:                     {sys.version.split()[0]}")
    lines.append(f"MuJoCo:                     {mujoco.__version__}")
    lines.append(f"NumPy:                      {np.__version__}")
    lines.append(f"Executable:                 {sys.executable}")
    lines.append(f"Platform:                   {platform.platform()}")
    lines.append(f"Git SHA:                    {_git_sha()}")
    lines.append(f"gravity:                    {result['gravity_mps2']:.2f} m/s^2, timestep={TIMESTEP_S} s")
    lines.append(f"error limit:                {ERROR_LIMIT_PCT:.1f}% (normal force vs m*g)")
    lines.append("force source:               mujoco.mj_contactForce only "
                 "(contact frame; 0=normal, 1-2=tangential, 3-5=torque)")
    lines.append("efc_force:                  excluded; under pyramidal cone it is an edge")
    lines.append("                            coefficient, not a force")
    lines.append("")
    lines.append("cone comparison (this run, flat resting sphere):")
    lines.append(f"  {result['cone']:<10} Fn={result['fn_mean_n']:.9f} N "
                 f"(error {result['fn_error_pct']:+.6f}%)")
    lines.append(f"  {other['cone']:<10} Fn={other['fn_mean_n']:.9f} N "
                 f"(error {other['fn_error_pct']:+.6f}%)")
    lines.append(f"  difference between cones: {diff_pct:.6f}% of m*g")
    lines.append("  Why this project uses mj_contactForce for every output column:")
    lines.append("  - it returns the actual contact wrench in the contact frame (N, N*m);")
    lines.append("  - efc_force is a solver-row quantity and depends on cone type; under")
    lines.append("    pyramidal it is an edge coefficient, so it cannot be reported as force;")
    lines.append("  - flat static contact does not exercise tangential allocation, so the")
    lines.append("    two cones differ only at numerical round-off here; slope/dynamic cases")
    lines.append("    are outside this check.")
    lines.append("")
    lines.append(f"--- case=flat_sphere  cone={result['cone']} (mjCONE id={result['cone_id']}) ---")
    lines.append(f"model.opt.cone:             {result['cone_id']} (expected {_cone_enum(result['cone'])})")
    lines.append(f"model.opt.timestep:         {TIMESTEP_S} s")
    lines.append(f"mass (model.body_mass):     {result['mass_kg']:.6f} kg")
    lines.append(f"m*g:                        {result['fn_expected_n']:.6f} N")
    lines.append(f"sample steps:               {SAMPLE_STEPS}, contacts per sample 1..{result['ncon']}")
    lines.append(f"geom1/geom2:                {'/'.join(result['geom_order'][0])}  "
                 "(force positive on geom2)")
    lines.append(f"contact normal (world):     "
                 f"[{result['normal_world'][0]: .6f} {result['normal_world'][1]: .6f} "
                 f"{result['normal_world'][2]: .6f}]")
    lines.append(f"Fn  measured (sum res[0]):  {result['fn_mean_n']:.9f} N")
    lines.append(f"Fn  error:                  {result['fn_error_pct']:+.6f} %")
    lines.append(f"Fz  world (expect m*g):     {result['fz_mean_n']:.9f} N "
                 f"({result['fz_error_pct']:+.6f} %)")
    lines.append(f"Ft  measured (expect 0):    {result['tangential_mean_n']:.3e} N")
    lines.append(f"max |torque|:               {result['torque_max_nm']:.3e} N*m")
    lines.append(f"residual |v|:               {result['residual_speed_mps']:.3e} m/s")
    lines.append(f"center drift (sample):      {result['drift_mm']:.6f} mm")
    lines.append(f"penetration:                {result['penetration_mm']:.6f} mm")
    lines.append(f"warning.number nonzero:     {result['warnings']}")
    lines.append(f"finite:                     {result['finite']}")
    for name, ok in result["checks"].items():
        lines.append(f"check {name:<14} {'OK' if ok else 'NOT_OK'}")
    lines.append(f"RESULT:                     {'OK' if result['ok'] else 'NOT_OK'}")
    return "\n".join(lines) + "\n"


def run_verification(write_files: bool = False, out_dir: str | Path | None = None,
                     verbose: bool = True) -> dict:
    """跑两种锥型并返回汇总；write_files=True 时各留一份原始输出。"""
    results = {cone: run_cone(cone) for cone in CONES}
    pyr = results["pyramidal"]
    ell = results["elliptic"]
    diff_pct = abs(pyr["fn_mean_n"] - ell["fn_mean_n"]) / pyr["fn_expected_n"] * 100.0
    ok = bool(pyr["ok"] and ell["ok"] and diff_pct <= ERROR_LIMIT_PCT)

    summary = {
        "ok": ok,
        "cone_difference_pct": diff_pct,
        "error_limit_pct": ERROR_LIMIT_PCT,
        "results": results,
    }

    if write_files:
        target = Path(out_dir) if out_dir else Path("docs/验证输出")
        target.mkdir(parents=True, exist_ok=True)
        stamp = _dt.date.today().isoformat()
        sha = _git_sha()[:8]
        for cone, other in (("pyramidal", ell), ("elliptic", pyr)):
            text = _format_report(results[cone], other, diff_pct)
            path = target / f"{stamp}_接触力读数_{cone}_{sha}.txt"
            path.write_text(text, encoding="utf-8")
            if verbose:
                print(f"raw output: {path}")

    if verbose:
        print("=== CONTACT FORCE READOUT SUMMARY ===")
        for cone in CONES:
            r = results[cone]
            print(f"{cone:<10} Fn_meas={r['fn_mean_n']:.9f} N  "
                  f"Fn_exp={r['fn_expected_n']:.9f} N  "
                  f"error={r['fn_error_pct']:+.6f}%  "
                  f"{'OK' if r['ok'] else 'NOT_OK'}")
        print(f"cone difference: {diff_pct:.6f}% of m*g (limit {ERROR_LIMIT_PCT:.1f}%)")
        print("CONTACT FORCE CHECK:", "OK" if ok else "NOT_OK")

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="docs/验证输出",
                        help="原始输出目录（默认 docs/验证输出）")
    args = parser.parse_args(argv)
    summary = run_verification(write_files=True, out_dir=args.out_dir, verbose=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
