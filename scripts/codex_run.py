"""Run nine deterministic, headless simulations of the independent reference model."""

import argparse
import csv
import json
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "codex-check.xml"
HEIGHTS_MM = (10, 20, 30)
REPEATS = 3
SETTLE_S = 0.5
DRIVE_S = 8.0
DIAGNOSTIC_S = 0.5
TARGET_M_S = 0.15
RAMP_M_S2 = 1.0  # makerspet/oomwoo-one/urdf/params.xacro:47; target ramp
KP_NM_PER_RAD_S = 0.15
LOAD_N = 0.1
STALL_M_S = 0.01
SLIP_M_S = 0.05
BELLY_BAND_M = 0.002
SUPPORT_MARGIN_M = 0.002
RECOVERY_M_S = TARGET_M_S / 2


def make_model(height_m):
    xml = ET.parse(MODEL)
    step = xml.find("./worldbody/geom[@name='step']")
    hx, hy, _ = step.get("size").split()
    step.set("size", f"{hx} {hy} {height_m / 2}")
    step.set("pos", f"{hx} 0 {height_m / 2}")
    return mj.MjModel.from_xml_string(ET.tostring(xml.getroot(), encoding="unicode"))


def contact_loads(model, data, parts, floor, step, belly, height):
    """World forces on each robot geom. The contact frame rows are [n, t1, t2]."""
    forces = np.zeros((len(parts), 3))
    top = np.zeros(3)
    belly_load = 0.0
    step_contact = False
    wrench = np.zeros(6)
    for i in range(data.ncon):
        contact = data.contact[i]
        a, b = map(int, contact.geom)
        if a in parts and b in (floor, step):
            robot, surface, sign = a, b, -1
        elif b in parts and a in (floor, step):
            robot, surface, sign = b, a, 1
        else:
            continue
        mj.mj_contactForce(model, data, i, wrench)
        force = sign * (contact.frame.reshape(3, 3).T @ wrench[:3])
        part = parts.index(robot)
        forces[part] += force
        if surface != step or wrench[0] <= LOAD_N:
            continue
        step_contact = True
        if robot != belly and contact.pos[0] > 0 and abs(contact.pos[2] - height) < SUPPORT_MARGIN_M:
            if sign * contact.frame[2] > 0.5:  # predominantly upward normal on the robot
                top[part] += force[2]
        if robot == belly:
            up = data.geom_xmat[belly].reshape(3, 3)[:, 2]
            bottom = data.geom_xpos[belly] - model.geom_size[belly, 1] * up
            if (contact.pos - bottom) @ up <= BELLY_BAND_M:
                belly_load += wrench[0]
    return forces, top, belly_load, step_contact


def run(model, height, path):
    data = mj.MjData(model)
    dt = model.opt.timestep
    parts = [model.geom(name).id for name in ("left_tire", "right_tire", "caster_tire", "belly")]
    left, right, _, belly = parts
    floor, step = model.geom("floor").id, model.geom("step").id
    axle = [int(model.joint(name).dofadr[0]) for name in ("left_roll", "right_roll")]
    radius = model.geom_size[left, 0]
    body_radius, body_half_height = model.geom_size[belly, :2]
    root_dof = int(model.body("chassis").dofadr[0])
    speed = np.zeros(6)
    recovery_start = None
    recent = []
    times = {part: None for part in ("left", "right", "caster")}
    touched = False
    result = {"outcome": "invalid", "failure_mode": None, "reason": "incomplete_observation"}
    force_columns = [f"{part}_force_{axis}_N" for part in (*times, "belly") for axis in "xyz"]

    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "time_s", "x_m", "y_m", "z_m", "vx_m_s", "qw", "qx", "qy", "qz",
            "left_rad_s", "right_rad_s", "left_Nm", "right_Nm",
            "left_slip_m_s", "right_slip_m_s", "belly_step_normal_N", "step_contact",
            "left_top_N", "right_top_N", "caster_top_N", *force_columns,
        ])
        settle_steps = round(SETTLE_S / dt)
        total_steps = settle_steps + round(DRIVE_S / dt)
        for i in range(total_steps + 1):
            drive_time = max(0, (i - settle_steps) * dt)
            target = min(TARGET_M_S, RAMP_M_S2 * drive_time)
            omega = data.qvel[axle]
            data.ctrl[:] = np.clip(
                KP_NM_PER_RAD_S * (target / radius - omega),
                model.actuator_ctrlrange[:, 0],
                model.actuator_ctrlrange[:, 1],
            )
            # Recompute contacts/forces at the exact state and control written to the CSV.
            mj.mj_forward(model, data)
            if np.any(data.warning.number) or not np.isfinite(data.qacc).all():
                result["reason"] = "simulation_warning_or_nonfinite"
                break
            x, y, z = data.qpos[:3]
            vx = data.qvel[root_dof]
            forces, top, belly_load, hit = contact_loads(
                model, data, parts, floor, step, belly, height
            )
            if i == settle_steps:
                weight = model.body_mass.sum() * abs(model.opt.gravity[2])
                if abs(forces[:, 2].sum() - weight) > 0.01 * weight or (forces[:3, 2] <= LOAD_N).any():
                    result["reason"] = "settled_support_force_check"
                    break
            slip = []
            for geom, angular_speed in zip((left, right), omega):
                mj.mj_objectVelocity(model, data, mj.mjtObj.mjOBJ_GEOM, geom, speed, 0)
                slip.append(radius * angular_speed - speed[3])
            writer.writerow([
                data.time, x, y, z, vx, *data.qpos[3:7], *omega,
                *data.qfrc_actuator[axle], *slip, belly_load, int(hit),
                *top, *forces.ravel(),
            ])
            touched |= hit
            for part, load in zip(times, top):
                if times[part] is None and load > LOAD_N:
                    times[part] = round(data.time, 6)
            if i >= settle_steps:
                recent.append((x, belly_load > LOAD_N, max(slip) > SLIP_M_S,
                               (top <= LOAD_N).any()))
                up = data.geom_xmat[belly].reshape(3, 3)[:, 2]
                x_reach = body_radius * np.sqrt(max(0.0, 1 - up[0] ** 2)) + body_half_height * abs(up[0])
                rear_x = data.geom_xpos[belly, 0] - x_reach
                if rear_x > SUPPORT_MARGIN_M and up[2] > 0.95 and (top > LOAD_N).all() and vx >= RECOVERY_M_S:
                    if recovery_start is None:
                        recovery_start = x
                    if x - recovery_start >= 2 * body_radius:
                        result.update(outcome="cleared", reason="supported_forward_recovery")
                        break
                else:
                    recovery_start = None
            if i < total_steps:
                mj.mj_step(model, data)
        else:
            tail = recent[-(round(DIAGNOSTIC_S / dt) + 1):]
            if touched and abs(tail[-1][0] - tail[0][0]) / DIAGNOSTIC_S < STALL_M_S:
                majority = np.asarray(tail)[:, 1:].mean(axis=0) > 0.5
                belly_hit, slipping, incomplete_lift = majority
                if belly_hit:
                    failure = "belly_contact"
                elif slipping:
                    failure = "slip_stall"
                elif incomplete_lift:
                    failure = "lift_fail"
                else:
                    failure = None
                if failure:
                    result.update(outcome="blocked", failure_mode=failure, reason="sustained_stall")
    result.update(time_s=round(data.time, 6), final_x_m=round(float(data.qpos[0]), 6),
                  step_contact_seen=touched, **{f"{k}_first_top_s": v for k, v in times.items()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    model = make_model(HEIGHTS_MM[0] / 1000)
    geom = model.geom("left_tire")
    metadata = {
        "host": platform.node(), "python": sys.executable, "python_version": platform.python_version(),
        "mujoco": mj.__version__, "numpy": np.__version__,
        "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
        "model": str(MODEL), "cwd": str(Path.cwd()), "output": str(args.out.resolve()),
        "timestep_s": model.opt.timestep, "integrator": mj.mjtIntegrator(model.opt.integrator).name,
        "solver": mj.mjtSolver(model.opt.solver).name, "cone": mj.mjtCone(model.opt.cone).name,
        "gravity_m_s2": model.opt.gravity.tolist(), "iterations": model.opt.iterations,
        "contact_defaults": {"friction": geom.friction.tolist(), "solref": geom.solref.tolist(),
                             "solimp": geom.solimp.tolist(), "condim": int(geom.condim[0]),
                             "margin_m": float(geom.margin[0]), "gap_m": float(geom.gap[0])},
        "modeled_mass_kg": float(model.body_mass.sum()),
        "config": {name: globals()[name] for name in (
            "HEIGHTS_MM", "REPEATS", "SETTLE_S", "DRIVE_S", "DIAGNOSTIC_S", "TARGET_M_S",
            "RAMP_M_S2", "KP_NM_PER_RAD_S", "LOAD_N", "STALL_M_S", "SLIP_M_S",
            "BELLY_BAND_M", "SUPPORT_MARGIN_M", "RECOVERY_M_S")},
    }
    rows = []
    for height_mm in HEIGHTS_MM:
        model = make_model(height_mm / 1000)
        for repeat in range(1, REPEATS + 1):
            name = f"step_{height_mm:02d}mm_run_{repeat}.csv"
            rows.append({"height_mm": height_mm, "repeat": repeat, "timeseries": name,
                         **run(model, height_mm / 1000, args.out / name)})
    (args.out / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    with (args.out / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row["height_mm"], row["repeat"], row["outcome"], row["failure_mode"] or "-")


if __name__ == "__main__":
    main()
