"""通用样机批运行入口：场景注入、限扭驱动、接触读数、A1–A4 与结果归档。

入口
----
    .venv\\Scripts\\python.exe scripts\\run_cases.py --config cases/baseline.json --out outputs/baseline

本脚本只负责“这一次算例有没有爬上去”以及机理诊断，输出列使用
``outcome = cleared | blocked | invalid``，不使用判定级措辞。A1–A4 的
逐项结果用 ``met | not_met | na``。

接触力
------
所有接触力列只来自 ``mujoco.mj_contactForce``：``res[0]`` 法向、
``res[1..2]`` 切向、``res[3..5]`` 力矩；返回值在接触帧内。输出取法向
与切向的模长，并同时保留接触对名称与 active 计数。``efc_force`` 不进
任何输出列。

无接触与真实零值
----------------
CSV 空字段 = 无数据/无接触；``0.0`` = 有接触且实测合力为零。每个
``contact_<pair>_normal_n`` 都有同对 ``contact_<pair>_active``；
``active=0`` 时力列必须为空，``active=1`` 时力列必须非空。

无接触、穿透超限、蠕滑基线降步长后仍超限、``v_impact`` 与触发不同源
同帧，这四类落 ``outcome=invalid`` 并在 ``run.json`` 记原因。
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_contact_readout import run_verification  # noqa: E402
import build_model as bm  # noqa: E402

# ---------------------------------------------------------------------------
# 名称表（只按名字取，禁止整数索引）
# ---------------------------------------------------------------------------
BODY_CHASSIS = "chassis"
BODY_WHEEL = {"L": "wheel_L", "R": "wheel_R"}
BODY_CASTER = "caster"
JOINT_SPIN = {"L": "wheel_L_spin", "R": "wheel_R_spin"}
JOINT_SUSP = {"L": "susp_L", "R": "susp_R"}
ACT_WHEEL = {"L": "wheel_L", "R": "wheel_R"}
GEOM_WHEEL = {"L": "wheel_L_tire", "R": "wheel_R_tire"}

CLEARED = "cleared"
BLOCKED = "blocked"
INVALID = "invalid"

INVALID_REASONS = {
    "no_contact",
    "penetration_exceeded",
    "creep_baseline_exceeded",
    "impact_frame_mismatch",
    "numerical_invalid",
}

# 机理名，不是判定级枚举
MODE_TOPPLED = "topple"
MODE_BELLY = "belly_contact"
MODE_RETREAT = "retreat"
MODE_SLIP_STALL = "slip_stall"
MODE_LIFT = "lift_fail"
MODE_RECOVER = "recover_fail"
MODE_TIMEOUT = "timeout"
MODE_SUSP_BOTTOM = "suspension_bottom"
MODE_TORQUE_LIMIT = "torque_limit"
MODE_SLIP = "slip"

BLOCKING_MODES = [
    MODE_TOPPLED,
    MODE_BELLY,
    MODE_RETREAT,
    MODE_SLIP_STALL,
    MODE_LIFT,
    MODE_RECOVER,
    MODE_TIMEOUT,
]

LABELS = ("本机实测", "图纸推算", "公开参考", "工程假设", "缺失", "待标定")

SUMMARY_COLUMNS = [
    "case_id", "repeat", "config_id", "heading_deg", "step_height_m",
    "v_impact_mps", "v_approach_mean_mps", "outcome", "failure_mode",
    "failure_modes",
    "A1", "A1_v_impact_mps", "A1_limit_mps",
    "A2", "A2_max_dev_m", "A2_limit_m",
    "A3", "A3_max_accel_mps2", "A3_limit_mps2",
    "A4", "A4_steady_step_ratio", "A4_transient_step_ratio",
    "timestep_s", "cone", "integrator", "status",
    "t_trigger_s", "t_climb_s", "advance_m", "first_contact_wheel",
    "contact_dt_s", "flat_speed_rel_diff_L", "flat_speed_rel_diff_R",
    "penetration_max_m", "model_sha256", "config_sha256", "output_dir",
]

TIMESERIES_COLUMNS = [
    "t_s",
    "pos_x_m", "pos_y_m", "pos_z_m",
    "quat_w", "quat_x", "quat_y", "quat_z",
    "pitch_rad", "roll_rad", "yaw_rad",
    "vel_x_mps", "vel_y_mps", "vel_z_mps",
    "wheel_L_speed_radps", "wheel_R_speed_radps",
    "wheel_L_torque_nm", "wheel_R_torque_nm",
    "wheel_L_qvel_radps", "wheel_R_qvel_radps",
    "wheel_L_actuator_force_nm", "wheel_R_actuator_force_nm",
    "susp_L_travel_m", "susp_R_travel_m",
    "contact_wheel_L_floor_active", "contact_wheel_L_floor_normal_n",
    "contact_wheel_L_floor_tangent_n", "contact_wheel_L_floor_count",
    "contact_wheel_R_floor_active", "contact_wheel_R_floor_normal_n",
    "contact_wheel_R_floor_tangent_n", "contact_wheel_R_floor_count",
    "contact_wheel_L_step_active", "contact_wheel_L_step_normal_n",
    "contact_wheel_L_step_tangent_n", "contact_wheel_L_step_count",
    "contact_wheel_R_step_active", "contact_wheel_R_step_normal_n",
    "contact_wheel_R_step_tangent_n", "contact_wheel_R_step_count",
    "contact_caster_floor_active", "contact_caster_floor_normal_n",
    "contact_caster_floor_tangent_n", "contact_caster_floor_count",
    "contact_caster_rear_floor_active", "contact_caster_rear_floor_normal_n",
    "contact_caster_rear_floor_tangent_n", "contact_caster_rear_floor_count",
    "contact_chassis_step_active", "contact_chassis_step_normal_n",
    "contact_chassis_step_tangent_n", "contact_chassis_step_count",
    "wheel_L_normal_n", "wheel_R_normal_n",
    "wheel_L_tangent_n", "wheel_R_tangent_n", "wheel_tangent_total_n",
    "all_contact_normal_n", "all_contact_count",
    "chassis_min_z_m", "data_valid",
]

PAIR_COLUMNS = {
    "contact_wheel_L_floor": ("wheel_L_floor",),
    "contact_wheel_R_floor": ("wheel_R_floor",),
    "contact_wheel_L_step": ("wheel_L_step",),
    "contact_wheel_R_step": ("wheel_R_step",),
    "contact_caster_floor": ("caster_floor",),
    "contact_caster_rear_floor": ("caster_rear_floor",),
    "contact_chassis_step": ("chassis_step",),
}


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------
def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info(repo: Path) -> dict:
    def _run(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=repo, stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return ""

    commit = _run("rev-parse", "HEAD")
    branch = _run("rev-parse", "--abbrev-ref", "HEAD")
    status = _run("status", "--porcelain")
    return {"commit": commit, "branch": branch, "dirty": bool(status)}


def jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def csv_num(value, digits: int = 12) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return ""
        return f"{float(value):.{digits}g}"
    return str(value)


def _body_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def _joint_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)


def _act_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)


def _geom_id(model: mujoco.MjModel, name: str) -> int:
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)


def _enum_name(mapping: dict, value: int, default: str) -> str:
    return mapping.get(int(value), f"{default}({int(value)})")


def integrator_map() -> dict:
    m = mujoco.mjtIntegrator
    return {
        int(m.mjINT_EULER): "Euler",
        int(m.mjINT_RK4): "RK4",
        int(m.mjINT_IMPLICIT): "implicit",
        int(m.mjINT_IMPLICITFAST): "implicitfast",
    }


def cone_map() -> dict:
    m = mujoco.mjtCone
    return {
        int(m.mjCONE_PYRAMIDAL): "pyramidal",
        int(m.mjCONE_ELLIPTIC): "elliptic",
    }


def solver_map() -> dict:
    m = mujoco.mjtSolver
    return {
        int(m.mjSOL_PGS): "PGS",
        int(m.mjSOL_CG): "CG",
        int(m.mjSOL_NEWTON): "Newton",
    }


def cone_enum(name: str) -> int:
    return {"pyramidal": int(mujoco.mjtCone.mjCONE_PYRAMIDAL),
            "elliptic": int(mujoco.mjtCone.mjCONE_ELLIPTIC)}[name]


def integrator_enum(name: str) -> int:
    return {"Euler": int(mujoco.mjtIntegrator.mjINT_EULER),
            "RK4": int(mujoco.mjtIntegrator.mjINT_RK4),
            "implicit": int(mujoco.mjtIntegrator.mjINT_IMPLICIT),
            "implicitfast": int(mujoco.mjtIntegrator.mjINT_IMPLICITFAST)}[name]


def solver_enum(name: str) -> int:
    return {"PGS": int(mujoco.mjtSolver.mjSOL_PGS),
            "CG": int(mujoco.mjtSolver.mjSOL_CG),
            "Newton": int(mujoco.mjtSolver.mjSOL_NEWTON)}[name]


def euler_zyx(quat) -> tuple[float, float, float]:
    w, x, y, z = (float(v) for v in quat)
    r20 = 2.0 * (x * z - w * y)
    r21 = 2.0 * (y * z + w * x)
    r22 = 1.0 - 2.0 * (x * x + y * y)
    r10 = 2.0 * (x * y + w * z)
    r00 = 1.0 - 2.0 * (y * y + z * z)
    pitch = math.asin(max(-1.0, min(1.0, -r20)))
    roll = math.atan2(r21, r22)
    yaw = math.atan2(r10, r00)
    return pitch, roll, yaw


# ---------------------------------------------------------------------------
# 场景 XML 注入
# ---------------------------------------------------------------------------
def _friction_str(values) -> str:
    vals = [float(v) for v in values]
    if len(vals) == 4:
        vals = [vals[0], vals[1], vals[2]]
    if len(vals) < 3:
        vals = vals + [0.005, 0.0001][: 3 - len(vals)]
    return " ".join(f"{v:.9g}" for v in vals[:3])


def _rot_z(x: float, y: float, psi: float) -> tuple[float, float]:
    return (x * math.cos(psi) - y * math.sin(psi),
            x * math.sin(psi) + y * math.cos(psi))


def case_step_height(case: dict) -> float:
    obstacle = case.get("scenario", {}).get("obstacle")
    return 0.0 if not obstacle else float(obstacle["height_m"])


def case_has_step(case: dict) -> bool:
    return case.get("scenario", {}).get("kind") == "step"


def pv(params: dict, key: str):
    return params["values"][key]["value"]


def _friction(params: dict, group: str) -> str:
    return " ".join(f"{float(pv(params, f'contact.mu_{group}_{axis}')):.9g}"
                    for axis in ("s", "t", "r"))


def build_scenario_xml(model_xml: str, case: dict, params: dict) -> str:
    """注入 floor / step / step_edge；接触对拓扑在结构模板里，不在这里重建。

    flat 工况也注入 step 和 step_edge，但放到 y=100 m 的远处，保证模板里的
    接触对引用始终存在，同时不会与机器人发生接触。
    """
    scenario = case["scenario"]
    condim = int(pv(params, "contact.condim"))
    solref = (f"{float(pv(params, 'contact.solref_timeconst')):.9g} "
              f"{float(pv(params, 'contact.solref_dampratio')):.9g}")
    solimp = " ".join(f"{float(pv(params, f'contact.solimp_{i}')):.9g}" for i in range(5))
    floor_fric = _friction(params, "wheel_floor")

    geoms = [
        '<geom name="floor" type="plane" size="4 4 0.1" pos="0 0 0" '
        f'material="floor" friction="{floor_fric}" condim="{condim}" '
        f'solref="{solref}" solimp="{solimp}" contype="1" conaffinity="3"/>'
    ]

    if case_has_step(case):
        obstacle = scenario["obstacle"]
        height = float(obstacle["height_m"])
        edge_r = max(0.0, min(float(obstacle.get("edge_radius_m", 0.0)), 0.9 * height))
        top_len = float(obstacle.get("top_width_m", 2.0))
        heading = math.radians(float(scenario.get("heading_deg", 0.0)))
        ox, oy = 0.0, 0.0
        step_fric = _friction(params, "wheel_step")
    else:
        # 远景占位台阶，尺寸与位置都不参与本节结论
        height, edge_r, top_len = 0.05, 0.003, 0.2
        heading = 0.0
        ox, oy = 0.1, 100.0
        step_fric = _friction(params, "wheel_step")

    box_h = max(height - edge_r, 1e-4)
    cx, cy = _rot_z(ox + top_len / 2.0, oy, heading)
    qw = math.cos(heading / 2.0)
    qz = math.sin(heading / 2.0)
    geoms.append(
        f'<geom name="step" type="box" size="{top_len / 2.0:.9g} 1 {box_h / 2.0:.9g}" '
        f'pos="{cx:.9g} {cy:.9g} {box_h / 2.0:.9g}" '
        f'quat="{qw:.9g} 0 0 {qz:.9g}" material="step" '
        f'friction="{step_fric}" condim="{condim}" solref="{solref}" '
        f'solimp="{solimp}" contype="1" conaffinity="3"/>'
    )
    # 圆角顶棱：圆柱轴沿台阶前缘；圆心在局部 (edge_r, 0, height-edge_r)
    ex, ey = _rot_z(ox + edge_r, oy, heading)
    ax, ay = _rot_z(0.0, 1.0, heading)
    geoms.append(
        f'<geom name="step_edge" type="cylinder" size="{edge_r:.9g} 1" '
        f'pos="{ex:.9g} {ey:.9g} {height - edge_r:.9g}" '
        f'zaxis="{ax:.9g} {ay:.9g} 0" material="step" '
        f'friction="{step_fric}" condim="{condim}" solref="{solref}" '
        f'solimp="{solimp}" contype="1" conaffinity="3"/>'
    )

    return model_xml.replace("</worldbody>", "\n".join(geoms) + "\n  </worldbody>", 1)


# ---------------------------------------------------------------------------
# 模型参数校验
# ---------------------------------------------------------------------------
def validate_model(model: mujoco.MjModel, params: dict, model_path: Path,
                   model_sha: str) -> dict:
    cid = _body_id(model, BODY_CHASSIS)
    if cid < 0:
        raise SystemExit("model contract error: body 'chassis' not found")

    checks = {
        "chassis.mass": (float(model.body_mass[cid]), float(pv(params, "chassis.mass")), 1e-6),
        "chassis.ipos_x": (float(model.body_ipos[cid][0]), float(pv(params, "chassis.ipos_x")), 1e-6),
        "chassis.ipos_z": (float(model.body_ipos[cid][2]), float(pv(params, "chassis.ipos_z")), 1e-6),
        "chassis.ixx": (float(model.body_inertia[cid][0]), float(pv(params, "chassis.ixx")), 1e-6),
        "chassis.iyy": (float(model.body_inertia[cid][1]), float(pv(params, "chassis.iyy")), 1e-6),
        "chassis.izz": (float(model.body_inertia[cid][2]), float(pv(params, "chassis.izz")), 1e-6),
    }
    problems = []
    for name, (actual, expected, tol) in checks.items():
        if abs(actual - expected) > tol:
            problems.append(f"{name}: model={actual} params={expected}")
    if problems:
        raise SystemExit(
            "config_id / chassis-inertial mismatch (contract v1.4):\n  - "
            + "\n  - ".join(problems)
        )

    total_mass = float(np.sum(model.body_mass[1:]))
    com = np.zeros(3)
    for bid in range(1, model.nbody):
        # 本模型的子 body 都是 chassis 的直接子节点，姿态为单位；用 body_pos + ipos
        com += float(model.body_mass[bid]) * (
            np.asarray(model.body_pos[bid]) + np.asarray(model.body_ipos[bid])
        )
    com /= max(total_mass, 1e-12)

    travel = {}
    for side in ("L", "R"):
        jid = _joint_id(model, JOINT_SUSP[side])
        lo, hi = model.jnt_range[jid]
        travel[side] = float(hi - lo)

    return {
        "config_id": params["config_id"],
        "machine": params["machine"],
        "mass_chassis_kg": float(model.body_mass[cid]),
        "mass_assembly_kg": total_mass,
        "com_offset_B_m": com.tolist(),
        "inertia_B_diag_kgm2": np.asarray(model.body_inertia[cid]).tolist(),
        "susp_travel_m": travel,
        "model_sha256": model_sha,
    }


def read_contacts(model: mujoco.MjModel, data: mujoco.MjData, gid: dict) -> dict:
    """用 mj_contactForce 汇总；空/零语义由调用方按 active 写出。"""
    wheel_ids = {side: gid[GEOM_WHEEL[side]] for side in ("L", "R")}
    floor_id = gid["floor"]
    step_ids = {gid.get("step"), gid.get("step_edge")}
    step_ids.discard(None)
    caster_id = gid["caster_ball"]
    caster_rear_id = gid["caster_rear_ball"]
    chassis_geoms = gid["chassis_geoms"]

    out = {
        "pairs": {},
        "wheel_L_normal": 0.0,
        "wheel_R_normal": 0.0,
        "wheel_L_tangent": 0.0,
        "wheel_R_tangent": 0.0,
        "wheel_L_step_normal": 0.0,
        "wheel_R_step_normal": 0.0,
        "chassis_step_normal": 0.0,
        "caster_floor_normal": 0.0,
        "caster_rear_floor_normal": 0.0,
        "all_normal": 0.0,
        "max_penetration": 0.0,
        "ncon": int(data.ncon),
        "warnings": 0,
        "valid": True,
    }
    for key in (
        "wheel_L_floor", "wheel_R_floor", "wheel_L_step", "wheel_R_step",
        "caster_floor", "caster_rear_floor", "chassis_step",
    ):
        out["pairs"][key] = {"active": 0, "normal": 0.0, "tangent": 0.0, "count": 0}

    res = np.zeros(6, dtype=np.float64)
    finite = True
    for i in range(data.ncon):
        c = data.contact[i]
        g1 = int(c.geom1)
        g2 = int(c.geom2)
        pair = {g1, g2}
        mujoco.mj_contactForce(model, data, i, res)
        if not np.all(np.isfinite(res)):
            finite = False
            continue
        fn = abs(float(res[0]))
        ft = float(np.linalg.norm(res[1:3]))
        out["all_normal"] += fn
        out["max_penetration"] = max(out["max_penetration"], max(0.0, -float(c.dist)))

        for side in ("L", "R"):
            if wheel_ids[side] in pair:
                other = g2 if g1 == wheel_ids[side] else g1
                if other == floor_id:
                    p = out["pairs"][f"wheel_{side}_floor"]
                    p["active"] = 1
                    p["normal"] += fn
                    p["tangent"] += ft
                    p["count"] += 1
                elif other in step_ids:
                    p = out["pairs"][f"wheel_{side}_step"]
                    p["active"] = 1
                    p["normal"] += fn
                    p["tangent"] += ft
                    p["count"] += 1
                out[f"wheel_{side}_normal"] += fn
                out[f"wheel_{side}_tangent"] += ft
                if other in step_ids:
                    out[f"wheel_{side}_step_normal"] += fn

        if caster_rear_id in pair and floor_id in pair:
            p = out["pairs"]["caster_rear_floor"]
            p["active"] = 1
            p["normal"] += fn
            p["tangent"] += ft
            p["count"] += 1
            out["caster_rear_floor_normal"] += fn

        if caster_id in pair and floor_id in pair:
            p = out["pairs"]["caster_floor"]
            p["active"] = 1
            p["normal"] += fn
            p["tangent"] += ft
            p["count"] += 1
            out["caster_floor_normal"] += fn

        if pair & chassis_geoms and pair & step_ids:
            p = out["pairs"]["chassis_step"]
            p["active"] = 1
            p["normal"] += fn
            p["tangent"] += ft
            p["count"] += 1
            out["chassis_step_normal"] += fn

    warnings = int(np.sum(np.asarray(data.warning.number)))
    out["warnings"] = warnings
    out["valid"] = bool(finite and warnings == 0)
    return out


# ---------------------------------------------------------------------------
# XML / 模型构建
# ---------------------------------------------------------------------------
def make_model(model_xml: str, case: dict, params: dict, effective: dict,
               cone_name: str) -> tuple[mujoco.MjModel, str, list[dict]]:
    xml = build_scenario_xml(model_xml, case, params)
    model = mujoco.MjModel.from_xml_string(xml)

    overrides = []
    dt = float(effective["timestep_s"])
    if abs(float(model.opt.timestep) - dt) > 1e-12:
        overrides.append({"field": "timestep", "xml": float(model.opt.timestep), "run": dt})
        model.opt.timestep = dt
    cone_id = cone_enum(cone_name)
    if int(model.opt.cone) != cone_id:
        overrides.append({"field": "cone", "xml": _enum_name(cone_map(), model.opt.cone, "cone"),
                          "run": cone_name})
        model.opt.cone = cone_id
    integ_id = integrator_enum(effective["integrator"])
    if int(model.opt.integrator) != integ_id:
        overrides.append({"field": "integrator",
                          "xml": _enum_name(integrator_map(), model.opt.integrator, "integrator"),
                          "run": effective["integrator"]})
        model.opt.integrator = integ_id
    solver_id = solver_enum(effective["solver"])
    if int(model.opt.solver) != solver_id:
        overrides.append({"field": "solver",
                          "xml": _enum_name(solver_map(), model.opt.solver, "solver"),
                          "run": effective["solver"]})
        model.opt.solver = solver_id
    if int(model.opt.iterations) != int(effective["iterations"]):
        overrides.append({"field": "iterations", "xml": int(model.opt.iterations),
                          "run": int(effective["iterations"])})
        model.opt.iterations = int(effective["iterations"])
    if abs(float(model.opt.tolerance) - float(effective["tolerance"])) > 1e-18:
        overrides.append({"field": "tolerance", "xml": float(model.opt.tolerance),
                          "run": float(effective["tolerance"])})
        model.opt.tolerance = float(effective["tolerance"])

    # 限扭：case 可覆盖全局
    base_torque = float(pv(params, "drive.torque_limit"))
    torque = float(case.get("drive", {}).get("torque_limit_nm", base_torque))
    for side in ("L", "R"):
        aid = _act_id(model, ACT_WHEEL[side])
        model.actuator_forcerange[aid] = [-torque, torque]
        model.actuator_ctrlrange[aid] = [-torque, torque]
        if abs(torque - base_torque) > 1e-12:
            overrides.append({"field": f"actuator.{ACT_WHEEL[side]}.forcerange",
                              "xml": base_torque,
                              "run": torque})

    scenario_sha = sha256_bytes(xml.encode("utf-8"))
    return model, scenario_sha, overrides


def geom_index(model: mujoco.MjModel) -> dict:
    gid = {
        "floor": _geom_id(model, "floor"),
        "caster_ball": _geom_id(model, "caster_ball"),
        "caster_rear_ball": _geom_id(model, "caster_rear_ball"),
        "chassis_geoms": set(),
    }
    for name in ("step", "step_edge"):
        gid[name] = _geom_id(model, name)
        if gid[name] < 0:
            raise SystemExit(f"scenario XML missing {name} geom")
    for side in ("L", "R"):
        gid[GEOM_WHEEL[side]] = _geom_id(model, GEOM_WHEEL[side])
    cid = _body_id(model, BODY_CHASSIS)
    for g in range(model.ngeom):
        if int(model.geom_bodyid[g]) == cid:
            gid["chassis_geoms"].add(g)
    if gid["floor"] < 0 or gid["caster_ball"] < 0 or gid["caster_rear_ball"] < 0:
        raise SystemExit("scenario XML missing floor / caster geom")
    return gid


def reset_state(model: mujoco.MjModel, data: mujoco.MjData, case: dict) -> tuple[float, float]:
    scenario = case["scenario"]
    start_distance = float(scenario["approach"]["start_distance_m"])
    x0 = -(start_distance + 0.15)
    y0 = float(scenario.get("start_offset_y_m", 0.0))
    mujoco.mj_resetData(model, data)
    data.qpos[:] = 0.0
    data.qvel[:] = 0.0
    data.qpos[0] = x0
    data.qpos[1] = y0
    data.qpos[2] = 0.0
    data.qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
    mujoco.mj_forward(model, data)
    return x0, y0


# ---------------------------------------------------------------------------
# 蠕滑基线
# ---------------------------------------------------------------------------
def creep_baseline(model_xml: str, flat_case: dict, params: dict, cfg: dict,
                   dt: float, cone_name: str) -> dict:
    effective = {
        "timestep_s": dt,
        "integrator": pv(params, "numerics.integrator"),
        "solver": pv(params, "numerics.solver"),
        "iterations": int(pv(params, "numerics.iterations")),
        "tolerance": float(pv(params, "numerics.tolerance")),
    }
    model, _, _ = make_model(model_xml, flat_case, params, effective, cone_name)
    data = mujoco.MjData(model)
    reset_state(model, data, flat_case)
    creep = cfg["judge"]["creep"]
    steps_settle = int(round(float(creep["settle_s"]) / dt))
    steps_measure = int(round(float(creep["measure_s"]) / dt))
    steps_drift = int(round(float(creep["drift_s"]) / dt))

    for _ in range(steps_settle):
        mujoco.mj_step(model, data)

    p0 = np.array(data.qpos[0:2], dtype=float)
    prev = p0.copy()
    speeds = []
    for _ in range(steps_measure):
        mujoco.mj_step(model, data)
        cur = np.array(data.qpos[0:2], dtype=float)
        speeds.append(float(np.linalg.norm(cur - prev) / dt))
        prev = cur.copy()
    p1 = prev.copy()
    for _ in range(steps_drift):
        mujoco.mj_step(model, data)
    p2 = np.array(data.qpos[0:2], dtype=float)

    mean_speed = float(np.mean(speeds)) if speeds else 0.0
    net_speed = float(np.linalg.norm(p1 - p0) / float(creep["measure_s"]))
    drift = float(np.linalg.norm(p2 - p0))
    over = (mean_speed > float(creep["speed_limit_mps"]) or
            drift > float(creep["drift_limit_m"]))
    return {
        "timestep_s": dt,
        "settle_s": float(creep["settle_s"]),
        "measure_s": float(creep["measure_s"]),
        "drift_s": float(creep["drift_s"]),
        "mean_speed_mps": mean_speed,
        "net_speed_mps": net_speed,
        "drift_m": drift,
        "speed_limit_mps": float(creep["speed_limit_mps"]),
        "drift_limit_m": float(creep["drift_limit_m"]),
        "over_limit": bool(over),
    }


# ---------------------------------------------------------------------------
# 单 case 运行
# ---------------------------------------------------------------------------
def _smooth(values: np.ndarray, n: int) -> np.ndarray:
    if n <= 1 or values.size < n:
        return values
    kernel = np.ones(n, dtype=float) / n
    return np.convolve(values, kernel, mode="same")


def _max_continuous_true(mask: np.ndarray, dt: float) -> float:
    best = 0.0
    run = 0.0
    for flag in mask:
        if flag:
            run += dt
            best = max(best, run)
        else:
            run = 0.0
    return best


def _a_result(value, threshold, ok: bool) -> dict:
    return {"result": "met" if ok else "not_met", "measured": value,
            "threshold": threshold}


def evaluate_case(rows: list[dict], case: dict, cfg: dict, params: dict,
                  model: mujoco.MjModel, travel: dict, t_drive_start: float,
                  static_susp: dict, trigger: dict | None, penetration_max: float,
                  creep_over: bool) -> dict:
    judge = cfg["judge"]
    wheel_radius = float(pv(params, "wheel.radius"))
    base_torque = float(pv(params, "drive.torque_limit"))
    h = case_step_height(case)
    is_step = case_has_step(case)
    speeds = [r["vel_x_mps"] for r in rows]
    times = np.array([r["t_s"] for r in rows], dtype=float)
    vx = np.array(speeds, dtype=float)
    vy = np.array([r["vel_y_mps"] for r in rows], dtype=float)
    px = np.array([r["pos_x_m"] for r in rows], dtype=float)
    horiz = np.hypot(vx, vy)

    t_trigger = None if trigger is None else float(trigger["t_s"])
    trigger_idx = None if trigger is None else int(trigger["index"])
    t_climb = None if trigger is None else trigger.get("t_climb")

    invalids = []
    if creep_over:
        invalids.append("creep_baseline_exceeded")
    if penetration_max > float(judge["penetration_limit_m"]):
        invalids.append("penetration_exceeded")
    if is_step and trigger is None:
        invalids.append("no_contact")

    # A1：触槛瞬间速度，与接触触发同一采样行
    a1 = {"result": "na", "measured": None, "threshold": None,
          "v_approach_mean_mps": None, "same_frame": None}
    v_impact = None
    v_approach = None
    if is_step and trigger is not None:
        v_impact = float(horiz[trigger_idx])
        limit = math.sqrt(float(judge["A1"]["coefficient"]) *
                          float(-model.opt.gravity[2]) * h)
        x_trigger = float(px[trigger_idx])
        window = float(judge["approach_mean_distance_m"])
        sel = np.where((px >= x_trigger - window) & (times <= t_trigger))[0]
        if sel.size >= 5:
            v_approach = float(np.mean(horiz[sel]))
        same_frame = bool(
            abs(float(times[trigger_idx]) - t_trigger) <= 1e-12
            and float(trigger["normal_at_trigger"]) >
            float(judge["contact_normal_min_n"])
        )
        a1 = _a_result(v_impact, limit, v_impact <= limit)
        a1["v_approach_mean_mps"] = v_approach
        a1["same_frame"] = same_frame
        a1["basis"] = "v_impact at the same sample as first wheel-step contact"
        if not same_frame:
            invalids.append("impact_frame_mismatch")

    # A2：悬挂相对静态平衡位
    a2 = {"result": "na", "measured": None, "threshold": None}
    if is_step and trigger is not None:
        t_end = float(t_climb) if t_climb is not None else t_trigger + float(judge["window_s"])
        sel = np.where((times >= t_trigger) & (times <= t_end))[0]
        dev = 0.0
        for side in ("L", "R"):
            q = np.array([r[f"susp_{side}_travel_m"] for r in rows], dtype=float)[sel]
            q0 = float(static_susp[side])
            dev = max(dev, float(np.max(np.abs(q - q0))) if q.size else 0.0)
        travel_ref = min(float(travel["L"]), float(travel["R"]))
        limit = min(float(judge["A2"]["abs_limit_m"]),
                    float(judge["A2"]["travel_frac_limit"]) * travel_ref)
        a2 = _a_result(dev, limit, dev < limit)
        a2["travel_m"] = travel_ref
        a2["basis"] = "max |q_susp - q_static| in crossing window; compression positive"

    # A3：接近段加速度
    a3 = {"result": "na", "measured": None, "threshold": None}
    t_a3_start = t_drive_start + 0.5
    t_a3_end = t_trigger if t_trigger is not None else float(times[-1])
    if not is_step:
        t_a3_end = float(times[-1])
    if t_a3_end - t_a3_start >= 0.2:
        sel = np.where((times >= t_a3_start) & (times <= t_a3_end))[0]
        if sel.size >= 10:
            n = max(1, int(round(float(judge["A3"]["smooth_window_s"]) /
                                  float(model.opt.timestep))))
            acc = np.gradient(_smooth(vx[sel], n), times[sel])
            value = float(np.max(np.abs(acc)))
            limit = float(judge["A3"]["accel_limit_mps2"])
            a3 = _a_result(value, limit, value <= limit)
            a3["basis"] = "max |d v_x/dt| after smoothing, approach segment"

    # A4：关节力矩时程无阶跃；相对步长阈值
    a4 = {"result": "na", "measured": None, "threshold": None,
          "steady_step_ratio": None, "transient_step_ratio": None}
    if t_trigger is not None:
        steady_mask = (
            ((times >= t_trigger - 0.5) & (times < t_trigger)) |
            ((times >= (t_climb if t_climb is not None else t_trigger + 0.5) + 0.2) &
             (times <= (t_climb if t_climb is not None else t_trigger + 0.5) + 1.2))
        )
        transient_mask = (
            (times >= t_trigger) &
            (times <= t_trigger + float(judge["A4"]["transient_window_s"]))
        )
    else:
        steady_mask = times >= t_drive_start + 0.5
        transient_mask = np.zeros_like(steady_mask, dtype=bool)

    torque_limit = float(case.get("drive", {}).get(
        "torque_limit_nm", base_torque))
    floor_tau = float(judge["A4"]["min_torque_frac"]) * torque_limit

    def _ratio(mask: np.ndarray) -> float | None:
        ratios = []
        for side in ("L", "R"):
            tau = np.array([r[f"wheel_{side}_torque_nm"] for r in rows], dtype=float)
            idx = np.where(mask)[0]
            for k in range(len(idx) - 1):
                i0, i1 = idx[k], idx[k + 1]
                if i1 != i0 + 1:
                    continue
                denom = max(abs(float(tau[i0])), abs(float(tau[i1])))
                if denom < floor_tau:
                    continue
                ratios.append(abs(float(tau[i1]) - float(tau[i0])) / denom)
        return float(max(ratios)) if ratios else None

    steady_ratio = _ratio(steady_mask)
    transient_ratio = _ratio(transient_mask)
    if steady_ratio is not None or transient_ratio is not None:
        s_ok = steady_ratio is None or steady_ratio <= float(judge["A4"]["steady_step_ratio"])
        t_ok = transient_ratio is None or transient_ratio <= float(judge["A4"]["transient_step_ratio"])
        value = max([v for v in (steady_ratio, transient_ratio) if v is not None])
        a4 = {"result": "met" if (s_ok and t_ok) else "not_met",
              "measured": value,
              "threshold": {"steady": float(judge["A4"]["steady_step_ratio"]),
                            "transient": float(judge["A4"]["transient_step_ratio"])},
              "steady_step_ratio": steady_ratio,
              "transient_step_ratio": transient_ratio,
              "basis": "max |tau(k+1)-tau(k)| / max(|tau|) for |tau| >= min_torque_frac*limit; actuator force at wheel joint, N*m"}

    # 诊断：姿态、托底、打滑、限扭、悬挂触底
    pitch = np.array([r["pitch_rad"] for r in rows], dtype=float)
    roll = np.array([r["roll_rad"] for r in rows], dtype=float)
    max_pitch = float(np.max(np.abs(pitch)))
    max_roll = float(np.max(np.abs(roll)))
    toppled = (max_pitch > math.radians(float(judge["tilt"]["pitch_deg"])) or
               max_roll > math.radians(float(judge["tilt"]["roll_deg"])))

    belly_mask = np.array([r["contact_chassis_step_normal_n"] is not None and
                           float(r["contact_chassis_step_normal_n"]) >
                           float(judge["contact_normal_min_n"]) for r in rows])
    belly_hit = bool(np.any(belly_mask))

    after = np.zeros_like(times, dtype=bool) if t_trigger is None else times >= t_trigger
    stall_speed = float(judge["stall"]["speed_mps"])
    stall_mask = after & (horiz < stall_speed)
    stall_time = _max_continuous_true(stall_mask, float(model.opt.timestep))

    slip_max = 0.0
    slip_time = 0.0
    for side in ("L", "R"):
        w = np.array([r[f"wheel_{side}_speed_radps"] for r in rows], dtype=float)
        vwheel = np.abs(w) * wheel_radius
        denom = np.maximum(vwheel, 0.05)
        slip = np.abs(vwheel - np.abs(vx)) / denom
        slip_max = max(slip_max, float(np.max(slip[after])) if np.any(after) else 0.0)
        slip_time = max(slip_time, _max_continuous_true(
            after & (slip > float(judge["slip_ratio"])), float(model.opt.timestep)))

    torque_series = []
    for side in ("L", "R"):
        torque_series.extend([abs(float(r[f"wheel_{side}_torque_nm"])) for r in rows])
    torque_peak = max(torque_series) if torque_series else 0.0
    saturated = np.zeros_like(times, dtype=bool)
    if t_trigger is not None:
        cross = (times >= t_trigger) & (times <= t_trigger + float(judge["window_s"]))
    else:
        cross = after
    sat_mask = cross & (np.maximum(
        np.abs(np.array([r["wheel_L_torque_nm"] for r in rows], dtype=float)),
        np.abs(np.array([r["wheel_R_torque_nm"] for r in rows], dtype=float))
    ) >= 0.98 * torque_limit)
    sat_frac = float(np.mean(sat_mask[cross])) if np.any(cross) else 0.0

    susp_bottom = False
    if t_trigger is not None:
        sel = np.where(times >= t_trigger)[0]
        for side in ("L", "R"):
            q = np.array([r[f"susp_{side}_travel_m"] for r in rows], dtype=float)[sel]
            if q.size and np.max(np.abs(q)) >= float(travel[side]) / 2.0 - 5e-4:
                susp_bottom = True

    advance = float(px[-1] - px[trigger_idx]) if trigger_idx is not None else float(px[-1] - px[0])
    retreat = advance < -0.02

    modes = []
    if toppled:
        modes.append(MODE_TOPPLED)
    if belly_hit:
        modes.append(MODE_BELLY)
    if retreat:
        modes.append(MODE_RETREAT)
    if slip_max > float(judge["slip_ratio"]):
        modes.append(MODE_SLIP)
    if susp_bottom:
        modes.append(MODE_SUSP_BOTTOM)
    if sat_frac > 0.5:
        modes.append(MODE_TORQUE_LIMIT)

    # 恢复段
    recovered = True
    if t_climb is not None:
        target_speed = float(case["scenario"]["approach"]["speed_mps"])
        rec_mask = (times >= float(t_climb)) & (vx >=
                                                float(judge["recover_speed_ratio"]) * target_speed)
        recovered = _max_continuous_true(rec_mask, float(model.opt.timestep)) >= float(
            judge["recover_hold_s"])
    body_length = 2.0 * float(pv(params, "chassis.radius"))
    min_advance = float(judge["min_advance_body_lengths"]) * body_length

    if invalids:
        outcome = INVALID
        primary = invalids[0]
    elif toppled or belly_hit or retreat:
        outcome = BLOCKED
        primary = next(m for m in BLOCKING_MODES if m in modes)
    elif t_climb is not None and advance >= min_advance and recovered:
        outcome = CLEARED
        primary = ""
    elif t_climb is not None and not recovered:
        outcome = BLOCKED
        primary = MODE_RECOVER
        modes.append(MODE_RECOVER)
    elif not is_step:
        if advance >= min_advance:
            outcome = CLEARED
            primary = ""
        else:
            outcome = BLOCKED
            primary = MODE_LIFT
            modes.append(MODE_LIFT)
    else:
        outcome = BLOCKED
        if stall_time >= float(judge["stall"]["duration_s"]):
            if slip_max > float(judge["slip_ratio"]) or slip_time >= 0.2:
                primary = MODE_SLIP_STALL
                modes.append(MODE_SLIP_STALL)
            else:
                primary = MODE_LIFT
                modes.append(MODE_LIFT)
        else:
            primary = MODE_TIMEOUT
            modes.append(MODE_TIMEOUT)

    # 前缘接触时序
    contact_order = None
    contact_dt = None
    if trigger is not None:
        contact_order = trigger.get("first_wheel")
        contact_dt = trigger.get("contact_dt_s")

    return {
        "outcome": outcome,
        "failure_mode": primary,
        "failure_modes": sorted(set(modes)),
        "invalid_reason": primary if outcome == INVALID else "",
        "A1": a1, "A2": a2, "A3": a3, "A4": a4,
        "v_impact_mps": v_impact,
        "v_approach_mean_mps": v_approach,
        "t_trigger_s": t_trigger,
        "t_climb_s": t_climb,
        "advance_m": advance,
        "first_contact_wheel": contact_order,
        "contact_dt_s": contact_dt,
        "pitch_max_deg": math.degrees(max_pitch),
        "roll_max_deg": math.degrees(max_roll),
        "slip_max": slip_max,
        "slip_duration_s": slip_time,
        "stall_duration_s": stall_time,
        "torque_peak_nm": torque_peak,
        "torque_saturated_fraction": sat_frac,
        "susp_bottom": susp_bottom,
        "penetration_max_m": penetration_max,
    }


def run_case(model_xml: str, case: dict, cfg: dict, params: dict,
             effective: dict, cone_name: str) -> dict:
    model, scenario_sha, overrides = make_model(model_xml, case, params, effective, cone_name)
    data = mujoco.MjData(model)
    gid = geom_index(model)
    reset_state(model, data, case)

    scenario = case["scenario"]
    is_step = case_has_step(case)
    h = case_step_height(case)
    approach = scenario["approach"]
    settle_s = float(approach["settle_s"])
    speed = float(approach["speed_mps"])
    radius = float(pv(params, "wheel.radius"))
    target_omega = speed / radius
    base_torque = float(pv(params, "drive.torque_limit"))
    torque_limit = float(case.get("drive", {}).get("torque_limit_nm", base_torque))
    kp = float(pv(params, "control.kp_nm_per_radps"))
    ki = float(pv(params, "control.ki_nm_per_rad"))
    integral_clamp = float(pv(params, "control.integral_clamp_nm"))
    torque_filter_s = float(pv(params, "control.torque_filter_s"))
    torque_rate_limit = float(pv(params, "control.torque_rate_limit_nm_per_s"))
    act_id = {s: _act_id(model, ACT_WHEEL[s]) for s in ("L", "R")}

    wheel_body = {s: _body_id(model, BODY_WHEEL[s]) for s in ("L", "R")}
    wheel_joint = {s: _joint_id(model, JOINT_SPIN[s]) for s in ("L", "R")}
    wheel_dof = {s: int(model.jnt_dofadr[wheel_joint[s]]) for s in ("L", "R")}
    wheel_qpos = {s: int(model.jnt_qposadr[_joint_id(model, JOINT_SUSP[s])]) for s in ("L", "R")}
    chassis_id = _body_id(model, BODY_CHASSIS)
    caster_joint = _joint_id(model, "caster_susp")
    caster_qpos = int(model.jnt_qposadr[caster_joint])

    dt = float(model.opt.timestep)
    rows: list[dict] = []
    int_err = {s: 0.0 for s in ("L", "R")}
    tau_out = {s: 0.0 for s in ("L", "R")}
    t_climb = None
    climb_hold = 0.0
    trigger = None
    first_contact = {"L": None, "R": None}
    static_samples = {s: [] for s in ("L", "R")}
    t_drive_start = settle_s
    min_normal = float(cfg["judge"]["contact_normal_min_n"])
    window = float(cfg["judge"]["window_s"])
    max_time = float(case["max_time_s"])
    no_contact_timeout = approach.get("no_contact_timeout_s")

    reset_state(model, data, case)

    # 初始行
    def current_row(t: float) -> dict:
        quat = np.array(data.xquat[chassis_id], dtype=float)
        pitch, roll, yaw = euler_zyx(quat)
        pos = np.array(data.qpos[0:3], dtype=float)
        vel = np.array(data.qvel[0:3], dtype=float)
        contact = read_contacts(model, data, gid)
        valid = contact["valid"] and np.all(np.isfinite(data.qpos)) and \
            np.all(np.isfinite(data.qvel))
        row = {
            "t_s": t,
            "pos_x_m": float(pos[0]), "pos_y_m": float(pos[1]), "pos_z_m": float(pos[2]),
            "quat_w": float(quat[0]), "quat_x": float(quat[1]),
            "quat_y": float(quat[2]), "quat_z": float(quat[3]),
            "pitch_rad": pitch, "roll_rad": roll, "yaw_rad": yaw,
            "vel_x_mps": float(vel[0]), "vel_y_mps": float(vel[1]),
            "vel_z_mps": float(vel[2]),
            "susp_L_travel_m": float(data.qpos[wheel_qpos["L"]]),
            "susp_R_travel_m": float(data.qpos[wheel_qpos["R"]]),
            "wheel_L_qvel_radps": float(data.qvel[wheel_dof["L"]]),
            "wheel_R_qvel_radps": float(data.qvel[wheel_dof["R"]]),
            "wheel_L_actuator_force_nm": float(data.actuator_force[act_id["L"]]),
            "wheel_R_actuator_force_nm": float(data.actuator_force[act_id["R"]]),
            "all_contact_count": contact["ncon"],
            "all_contact_normal_n": contact["all_normal"] if contact["ncon"] else None,
            "chassis_min_z_m": _chassis_min_z(model, data, gid["chassis_geoms"]),
            "data_valid": 1 if valid else 0,
            "penetration_max_m": float(contact["max_penetration"]),
        }
        for side in ("L", "R"):
            # 前进为正：+x 前向、+y 左向时，绕 +y 的正角速度即前进
            row[f"wheel_{side}_speed_radps"] = row[f"wheel_{side}_qvel_radps"]
            row[f"wheel_{side}_torque_nm"] = row[f"wheel_{side}_actuator_force_nm"]
            row[f"wheel_{side}_normal_n"] = contact[f"wheel_{side}_normal"] if contact["ncon"] else None
            row[f"wheel_{side}_tangent_n"] = contact[f"wheel_{side}_tangent"] if contact["ncon"] else None
        row["wheel_tangent_total_n"] = (
            (contact["wheel_L_tangent"] + contact["wheel_R_tangent"])
            if contact["ncon"] else None
        )
        for pair_key, p in contact["pairs"].items():
            active = 1 if p["active"] else 0
            row[f"contact_{pair_key}_active"] = active
            row[f"contact_{pair_key}_count"] = int(p["count"])
            if active and valid:
                row[f"contact_{pair_key}_normal_n"] = float(p["normal"])
                row[f"contact_{pair_key}_tangent_n"] = float(p["tangent"])
            else:
                row[f"contact_{pair_key}_normal_n"] = None
                row[f"contact_{pair_key}_tangent_n"] = None
        if not valid:
            for key in list(row):
                if key.startswith("contact_") and (key.endswith("_normal_n") or
                                                   key.endswith("_tangent_n")):
                    row[key] = None
            row["wheel_L_normal_n"] = None
            row["wheel_R_normal_n"] = None
            row["wheel_L_tangent_n"] = None
            row["wheel_R_tangent_n"] = None
            row["wheel_tangent_total_n"] = None
            row["all_contact_normal_n"] = None
        return row

    rows.append(current_row(0.0))
    penetration_max = 0.0

    while True:
        t_now = float(data.time)
        if t_now >= max_time - 1e-12:
            break

        if t_now >= t_drive_start:
            for side in ("L", "R"):
                omega = float(data.qvel[wheel_dof[side]])
                err = target_omega - omega
                int_err[side] += err * dt
                lim = integral_clamp / max(ki, 1e-12)
                int_err[side] = max(-lim, min(lim, int_err[side]))
                tau_des = kp * err + ki * int_err[side]
                if abs(tau_des) > torque_limit:
                    tau_des = math.copysign(torque_limit, tau_des)
                    int_err[side] -= err * dt
                # 一阶滤波 + 速率限幅，避免指令本身形成阶跃
                alpha = dt / (torque_filter_s + dt)
                tau_next = tau_out[side] + (tau_des - tau_out[side]) * alpha
                max_delta = torque_rate_limit * dt
                tau_next = max(tau_out[side] - max_delta,
                               min(tau_out[side] + max_delta, tau_next))
                tau_out[side] = max(-torque_limit, min(torque_limit, tau_next))
                data.ctrl[act_id[side]] = tau_out[side]
        else:
            for side in ("L", "R"):
                data.ctrl[act_id[side]] = 0.0
                if t_now >= t_drive_start - 0.5:
                    static_samples[side].append(float(data.qpos[wheel_qpos[side]]))

        mujoco.mj_step(model, data)
        row = current_row(float(data.time))
        rows.append(row)

        penetration_max = max(penetration_max, float(row.get("penetration_max_m", 0.0)))

        if is_step:
            for side in ("L", "R"):
                if first_contact[side] is None:
                    val = row.get(f"contact_wheel_{side}_step_normal_n")
                    if val is not None and float(val) > min_normal:
                        first_contact[side] = float(row["t_s"])
            if trigger is None and (first_contact["L"] is not None or
                                    first_contact["R"] is not None):
                a = first_contact["L"]
                b = first_contact["R"]
                if a is not None and b is not None:
                    if abs(a - b) < 1e-12:
                        first_wheel = "both"
                    elif a < b:
                        first_wheel = "L"
                    else:
                        first_wheel = "R"
                    contact_dt = abs(a - b)
                else:
                    first_wheel = "L" if a is not None else "R"
                    contact_dt = None
                trigger_t = a if (a is not None and (b is None or a <= b)) else b
                trigger = {
                    "t_s": float(trigger_t),
                    "index": len(rows) - 1,
                    "first_wheel": first_wheel,
                    "contact_dt_s": contact_dt,
                    "normal_at_trigger": float(
                        row.get("contact_wheel_L_step_normal_n") or 0.0)
                    + float(row.get("contact_wheel_R_step_normal_n") or 0.0),
                }

            if trigger is not None and t_climb is None:
                on_top = True
                for side in ("L", "R"):
                    z = float(data.xpos[wheel_body[side]][2])
                    if z < h + radius - 0.005:
                        on_top = False
                if on_top and float(data.xpos[chassis_id][2]) > h * 0.8:
                    climb_hold += dt
                else:
                    climb_hold = 0.0
                if climb_hold >= 0.2:
                    t_climb = float(row["t_s"])
                    trigger["t_climb"] = t_climb

        # 收尾条件
        if is_step:
            if trigger is None:
                stop_after = (float(no_contact_timeout) if no_contact_timeout is not None
                              else (float(approach["start_distance_m"]) + 0.3) / max(speed, 1e-6))
                if float(data.time) - t_drive_start >= stop_after:
                    break
            else:
                if float(data.time) - float(trigger["t_s"]) >= window:
                    break
                if t_climb is not None and float(data.time) - t_climb >= 1.2:
                    # 已登录平台后再给 1.2 s 观察恢复与前进
                    break
        # 发散保护
        if not np.all(np.isfinite(data.qpos)) or np.max(np.abs(data.qpos)) > 100.0:
            break

    static_susp = {}
    for side in ("L", "R"):
        vals = static_samples[side] if static_samples[side] else [0.0]
        static_susp[side] = float(np.mean(vals[-100:]))

    travel = {}
    for side in ("L", "R"):
        jid = _joint_id(model, JOINT_SUSP[side])
        lo, hi = model.jnt_range[jid]
        travel[side] = float(hi - lo)

    result = evaluate_case(
        rows, case, cfg, params, model,
        travel=travel,
        t_drive_start=t_drive_start,
        static_susp=static_susp,
        trigger=trigger,
        penetration_max=penetration_max,
        creep_over=bool(effective.get("creep_over", False)),
    )

    # 平地：轮速与车身速度一致性（供报告引用）
    flat_rel_L = flat_rel_R = None
    if not is_step:
        sel = np.array([r["t_s"] >= t_drive_start + 0.5 for r in rows], dtype=bool)
        if np.any(sel):
            v_body = float(np.mean([rows[i]["vel_x_mps"] for i in np.where(sel)[0]]))
            wl = float(np.mean([rows[i]["wheel_L_speed_radps"] for i in np.where(sel)[0]]))
            wr = float(np.mean([rows[i]["wheel_R_speed_radps"] for i in np.where(sel)[0]]))
            flat_rel_L = abs(wl * radius - v_body) / max(abs(v_body), 1e-9)
            flat_rel_R = abs(wr * radius - v_body) / max(abs(v_body), 1e-9)

    result.update({
        "case_id": case["case_id"],
        "config_id": case["config_id"],
        "heading_deg": float(scenario.get("heading_deg", 0.0)),
        "step_height_m": h,
        "scenario_xml_sha256": scenario_sha,
        "overrides": overrides,
        "numerics": {
            "timestep_s": float(model.opt.timestep),
            "integrator": _enum_name(integrator_map(), model.opt.integrator, "integrator"),
            "solver": _enum_name(solver_map(), model.opt.solver, "solver"),
            "cone": _enum_name(cone_map(), model.opt.cone, "cone"),
            "iterations": int(model.opt.iterations),
            "tolerance": float(model.opt.tolerance),
        },
        "static_susp_m": static_susp,
        "flat_speed_rel_diff_L": flat_rel_L,
        "flat_speed_rel_diff_R": flat_rel_R,
        "contact_events": _contact_events(rows, first_contact, t_climb, is_step),
        "rows": rows,
    })
    return result


def _chassis_min_z(model, data, chassis_geoms) -> float:
    if not chassis_geoms:
        return None
    vals = []
    for g in chassis_geoms:
        vals.append(float(data.geom_xpos[g][2] - model.geom_rbound[g]))
    return min(vals)


def _contact_events(rows, first_contact, t_climb, is_step) -> list[dict]:
    if not is_step:
        return []
    events = []
    for side in ("L", "R"):
        if first_contact[side] is not None:
            events.append({"event": f"wheel_{side}_step_contact",
                           "t_s": first_contact[side]})
    if t_climb is not None:
        events.append({"event": "all_wheels_on_top", "t_s": t_climb})
    return sorted(events, key=lambda e: e["t_s"])


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def write_timeseries(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TIMESERIES_COLUMNS,
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = {}
            for key in TIMESERIES_COLUMNS:
                val = row.get(key)
                out[key] = "" if val is None else csv_num(val)
            writer.writerow(out)


def summary_row(result: dict, repeat: int, model_sha: str, cfg_sha: str,
                output_dir: str) -> dict:
    a1, a2, a3, a4 = result["A1"], result["A2"], result["A3"], result["A4"]
    return {
        "case_id": result["case_id"],
        "repeat": repeat,
        "config_id": result["config_id"],
        "heading_deg": result["heading_deg"],
        "step_height_m": result["step_height_m"],
        "v_impact_mps": result.get("v_impact_mps"),
        "v_approach_mean_mps": result.get("v_approach_mean_mps"),
        "outcome": result["outcome"],
        "failure_mode": result["failure_mode"],
        "failure_modes": ";".join(result["failure_modes"]),
        "A1": a1["result"], "A1_v_impact_mps": a1.get("measured"),
        "A1_limit_mps": a1.get("threshold"),
        "A2": a2["result"], "A2_max_dev_m": a2.get("measured"),
        "A2_limit_m": a2.get("threshold"),
        "A3": a3["result"], "A3_max_accel_mps2": a3.get("measured"),
        "A3_limit_mps2": a3.get("threshold"),
        "A4": a4["result"], "A4_steady_step_ratio": a4.get("steady_step_ratio"),
        "A4_transient_step_ratio": a4.get("transient_step_ratio"),
        "timestep_s": result["numerics"]["timestep_s"],
        "cone": result["numerics"]["cone"],
        "integrator": result["numerics"]["integrator"],
        "status": ("invalid" if result["outcome"] == INVALID else "ok"),
        "t_trigger_s": result.get("t_trigger_s"),
        "t_climb_s": result.get("t_climb_s"),
        "advance_m": result.get("advance_m"),
        "first_contact_wheel": result.get("first_contact_wheel"),
        "contact_dt_s": result.get("contact_dt_s"),
        "flat_speed_rel_diff_L": result.get("flat_speed_rel_diff_L"),
        "flat_speed_rel_diff_R": result.get("flat_speed_rel_diff_R"),
        "penetration_max_m": result.get("penetration_max_m"),
        "model_sha256": model_sha,
        "config_sha256": cfg_sha,
        "output_dir": output_dir,
    }


def write_summary(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_COLUMNS,
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else csv_num(row.get(k)))
                             for k in SUMMARY_COLUMNS})


def param_summary(params: list[dict]) -> tuple[dict, str]:
    counts = Counter(p.get("label", "缺失") for p in params)
    for label in LABELS:
        counts.setdefault(label, 0)
    labels = {k for k, v in counts.items() if v > 0}
    if labels & {"缺失", "待标定"}:
        level = "mechanism"
    elif labels & {"图纸推算", "公开参考", "工程假设"}:
        level = "sensitivity"
    else:
        level = "quantitative"
    return dict(counts), level


def heading_groups(results: list[dict]) -> dict:
    groups: dict[str, dict] = {}
    for r in results:
        hd = float(r["heading_deg"])
        key = f"{hd:+.0f}" if abs(hd) > 1e-9 else "0"
        abskey = f"{abs(hd):.0f}"
        groups.setdefault(abskey, {}).setdefault(key, {
            "signed_heading_deg": hd, "count": 0, "outcomes": Counter(),
            "case_ids": [],
        })
        g = groups[abskey][key]
        g["count"] += 1
        g["outcomes"][r["outcome"]] += 1
        g["case_ids"].append(r["case_id"])
    out = {}
    for abskey, sub in sorted(groups.items()):
        out[abskey] = {
            "merged": False,
            "signed_groups": {
                k: {"signed_heading_deg": v["signed_heading_deg"],
                    "count": v["count"],
                    "outcomes": dict(v["outcomes"]),
                    "case_ids": v["case_ids"]}
                for k, v in sorted(sub.items())
            },
        }
    return out


def mirror_checks(results: list[dict]) -> dict:
    by_key = {(abs(float(r["heading_deg"])), float(r["heading_deg"])): r for r in results}
    checks = {}
    for abs_h in sorted({abs(float(r["heading_deg"])) for r in results}):
        if abs_h < 1e-9:
            continue
        plus = by_key.get((abs_h, abs_h))
        minus = by_key.get((abs_h, -abs_h))
        if plus is None or minus is None:
            continue
        checks[f"{abs_h:.0f}"] = {
            "abs_heading_deg": abs_h,
            "plus_case_id": plus["case_id"],
            "minus_case_id": minus["case_id"],
            "plus_first_contact_wheel": plus.get("first_contact_wheel"),
            "minus_first_contact_wheel": minus.get("first_contact_wheel"),
            "mirrored": (plus.get("first_contact_wheel") == "L" and
                         minus.get("first_contact_wheel") == "R"),
            "merged_in_output": False,
        }
    return checks


def repeat_consistency(summary_rows: list[dict], key_columns: list[str]) -> dict:
    by_case: dict[str, list[dict]] = {}
    for row in summary_rows:
        by_case.setdefault(row["case_id"], []).append(row)
    diffs = {}
    consistent = True
    for case_id, items in by_case.items():
        if len(items) < 2:
            continue
        base = items[0]
        for other in items[1:]:
            for key in key_columns:
                if csv_num(base.get(key)) != csv_num(other.get(key)):
                    consistent = False
                    diffs.setdefault(case_id, []).append(
                        {"column": key, "first": base.get(key), "other": other.get(key)}
                    )
    return {
        "count": max((len(v) for v in by_case.values()), default=0),
        "consistent": consistent,
        "key_columns": key_columns,
        "differences": diffs,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="cases/baseline.json")
    parser.add_argument("--out", default="outputs/baseline")
    parser.add_argument("--cone", choices=("pyramidal", "elliptic"), default=None,
                        help="覆盖配置中的摩擦锥，并在 run.json 记录 override")
    parser.add_argument("--repeat", type=int, default=1,
                        help="每个 case 顺序重复次数；产物目录加 _r<k> 后缀")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    config_path = (repo / args.config).resolve() if not Path(args.config).is_absolute() \
        else Path(args.config)
    out_dir = (repo / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"output directory exists and is not empty: {out_dir}")
        return 3
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg_bytes = config_path.read_bytes()
    cfg = json.loads(cfg_bytes.decode("utf-8"))
    cfg_sha = sha256_bytes(cfg_bytes)

    template_path = (repo / cfg["model"]["template_path"]).resolve()
    params_path = (repo / cfg["model"]["params_path"]).resolve()
    template_sha = sha256_file(template_path)
    params_sha = sha256_file(params_path)
    if template_sha != cfg["model"]["template_sha256"]:
        raise SystemExit(
            f"template sha256 mismatch: config={cfg['model']['template_sha256']} actual={template_sha}"
        )
    if params_sha != cfg["model"]["params_sha256"]:
        raise SystemExit(
            f"params sha256 mismatch: config={cfg['model']['params_sha256']} actual={params_sha}"
        )

    params = bm.load_params(params_path)
    gen_path = repo / "build/models" / f"{params['config_id']}.xml"
    built = bm.build_from_files(template_path, params_path, out_path=gen_path, validate=False)
    model_xml = built["xml"]
    model_sha = built["manifest"]["xml_sha256"]
    if model_sha != sha256_bytes(model_xml.encode("utf-8")):
        raise SystemExit("generated model sha256 mismatch")

    # config_id 与 chassis/inertial 一致性：所有 case 必须用同一载荷配置
    model_config_id = params["config_id"]
    bad = [c["case_id"] for c in cfg["cases"] if c["config_id"] != model_config_id]
    if bad:
        raise SystemExit(
            f"config_id mismatch: params={model_config_id}, cases={bad}"
        )

    flat_case_for_validation = next(
        (c for c in cfg["cases"] if c["scenario"]["kind"] == "flat"), None)
    if flat_case_for_validation is None:
        raise SystemExit("config has no flat case for model validation")
    validation_xml = build_scenario_xml(model_xml, flat_case_for_validation, params)
    base_model = mujoco.MjModel.from_xml_string(validation_xml)
    model_meta = validate_model(base_model, params, template_path, model_sha)

    # 接触读数前置条件
    pre = run_verification(write_files=False, verbose=False)
    if not pre["ok"]:
        print("contact readout precondition not met; no summary.csv written")
        return 2

    def pval(key: str):
        return params["values"][key]["value"]

    cone_name = args.cone or str(pval("numerics.cone"))
    requested = {
        "timestep_s": float(pval("numerics.timestep_s")),
        "integrator": str(pval("numerics.integrator")),
        "solver": str(pval("numerics.solver")),
        "cone": cone_name,
        "iterations": int(pval("numerics.iterations")),
        "tolerance": float(pval("numerics.tolerance")),
    }

    # 蠕滑基线；2 ms 超限即降 1 ms 重跑
    flat_case = next((c for c in cfg["cases"] if c["scenario"]["kind"] == "flat"), None)
    if flat_case is None:
        raise SystemExit("config has no flat case for creep baseline")
    creep = creep_baseline(model_xml, flat_case, params, cfg, requested["timestep_s"], cone_name)
    downgraded = False
    reason = ""
    effective = dict(requested)
    if creep["over_limit"]:
        downgraded = True
        reason = (f"2 ms creep baseline over limit: mean_speed={creep['mean_speed_mps']:.6g} m/s "
                  f"(limit {creep['speed_limit_mps']}), drift={creep['drift_m']:.6g} m "
                  f"(limit {creep['drift_limit_m']})")
        effective["timestep_s"] = float(pval("numerics.timestep_downgrade_s"))
        creep = creep_baseline(model_xml, flat_case, params, cfg, effective["timestep_s"], cone_name)
    creep_over = bool(creep["over_limit"])
    effective["creep_over"] = creep_over

    started = _dt.datetime.now(_dt.timezone.utc).isoformat()
    print(f"batch: {out_dir}")
    print(f"git: {git_info(repo)['commit']}  model_sha256={model_sha[:12]}  cfg_sha256={cfg_sha[:12]}")
    print(f"timestep={effective['timestep_s']} s  cone={cone_name}  "
          f"integrator={effective['integrator']}  downgraded={downgraded}")
    print(f"creep baseline: mean_speed={creep['mean_speed_mps']:.6g} m/s  "
          f"drift={creep['drift_m']:.6g} m  over_limit={creep['over_limit']}")

    results: list[dict] = []
    summary_rows: list[dict] = []
    case_meta: list[dict] = []
    for case in cfg["cases"]:
        for rep in range(1, args.repeat + 1):
            result = run_case(model_xml, case, cfg, params, effective, cone_name)
            sub = case["case_id"] if args.repeat == 1 else f"{case['case_id']}_r{rep}"
            rel_out = sub
            write_timeseries(out_dir / sub / "timeseries.csv", result["rows"])
            row = summary_row(result, rep, model_sha, cfg_sha, rel_out)
            summary_rows.append(row)
            results.append(result)
            case_meta.append({
                "case_id": result["case_id"],
                "repeat": rep,
                "config_id": result["config_id"],
                "heading_deg": result["heading_deg"],
                "step_height_m": result["step_height_m"],
                "outcome": result["outcome"],
                "failure_mode": result["failure_mode"],
                "failure_modes": result["failure_modes"],
                "invalid_reason": result["invalid_reason"],
                "A1": result["A1"], "A2": result["A2"],
                "A3": result["A3"], "A4": result["A4"],
                "v_impact_mps": result["v_impact_mps"],
                "v_approach_mean_mps": result["v_approach_mean_mps"],
                "t_trigger_s": result["t_trigger_s"],
                "t_climb_s": result["t_climb_s"],
                "advance_m": result["advance_m"],
                "first_contact_wheel": result["first_contact_wheel"],
                "contact_dt_s": result["contact_dt_s"],
                "contact_events": result["contact_events"],
                "flat_speed_rel_diff_L": result["flat_speed_rel_diff_L"],
                "flat_speed_rel_diff_R": result["flat_speed_rel_diff_R"],
                "pitch_max_deg": result["pitch_max_deg"],
                "roll_max_deg": result["roll_max_deg"],
                "slip_max": result["slip_max"],
                "torque_peak_nm": result["torque_peak_nm"],
                "penetration_max_m": result["penetration_max_m"],
                "numerics": result["numerics"],
                "scenario_xml_sha256": result["scenario_xml_sha256"],
                "overrides": result["overrides"],
                "output_dir": rel_out,
            })
            print(f"  {result['case_id']} r{rep}: outcome={result['outcome']} "
                  f"mode={result['failure_mode'] or '-'} "
                  f"t_trigger={result['t_trigger_s']} t_climb={result['t_climb_s']}")

    write_summary(out_dir / "summary.csv", summary_rows)

    key_cols = ["outcome", "failure_mode", "v_impact_mps", "v_approach_mean_mps",
                "A1", "A2", "A3", "A4", "t_trigger_s", "t_climb_s", "advance_m",
                "timestep_s", "cone", "integrator", "step_height_m"]
    repeat_info = repeat_consistency(summary_rows, key_cols)

    # 实际生效的 <option>：用第一个 case 的模型回读
    numeric_effective = case_meta[0]["numerics"] if case_meta else {}
    condim_used = int(pval("contact.condim"))
    if condim_used > 3:
        condim_note = f"condim={condim_used}；需补专项校验"
    else:
        condim_note = f"condim={condim_used}；未升维"

    provenance = [{"param_id": k, **v} for k, v in params["values"].items()]
    labels, level = param_summary(provenance)
    finished = _dt.datetime.now(_dt.timezone.utc).isoformat()
    run_json = {
        "contract_version": cfg.get("contract_version", "1.7.1"),
        "schema_version": cfg["schema_version"],
        "batch_id": out_dir.name,
        "git": git_info(repo),
        "model": {
            "config_id": model_meta["config_id"],
            "machine": model_meta["machine"],
            "generated_path": str(gen_path.relative_to(repo)) if gen_path.is_relative_to(repo) else str(gen_path),
            "sha256": model_sha,
            "template": {
                "path": str(template_path.relative_to(repo)) if template_path.is_relative_to(repo) else str(template_path),
                "sha256": template_sha,
            },
            "params": {
                "path": str(params_path.relative_to(repo)) if params_path.is_relative_to(repo) else str(params_path),
                "sha256": params_sha,
                "source": params.get("source", {}),
                "missing": params.get("missing", []),
                "blockers": params.get("blockers", []),
            },
            **{k: v for k, v in model_meta.items() if k not in {"model_sha256", "config_id", "machine"}},
        },
        "config": {"path": str(config_path), "sha256": cfg_sha},
        "python": sys.version.split()[0],
        "mujoco": mujoco.__version__,
        "numpy": np.__version__,
        "os": os.name,
        "platform": platform.platform(),
        "numerics": {
            "requested": requested,
            "effective": numeric_effective,
            "timestep_initial_s": float(pval("numerics.timestep_s")),
            "timestep_effective_s": float(effective["timestep_s"]),
            "timestep_downgraded": downgraded,
            "downgrade_reason": reason,
            "creep_baseline": creep,
            "condim_note": condim_note,
        },
        "overrides": [o for c in case_meta for o in c["overrides"]],
        "seed": 0,
        "seed_used": False,
        "params": provenance,
        "param_labels": labels,
        "conclusion_level": level,
        "precondition": {
            "contact_readout_ok": bool(pre["ok"]),
            "cone_difference_pct": pre["cone_difference_pct"],
            "error_limit_pct": pre["error_limit_pct"],
            "cone_fn_error_pct": {k: v["fn_error_pct"] for k, v in pre["results"].items()},
        },
        "criteria": cfg["judge"],
        "repeat": repeat_info,
        "started_utc": started,
        "finished_utc": finished,
        "cases": case_meta,
        "heading_groups": heading_groups(results),
        "mirror_checks": mirror_checks(results),
        "columns": {
            "timeseries": {c: {"unit": _unit_of(c)} for c in TIMESERIES_COLUMNS},
            "summary": {c: {"unit": _unit_of(c)} for c in SUMMARY_COLUMNS},
            "contact_force_source": "mujoco.mj_contactForce only; contact frame; "
                                    "res[0]=normal, res[1:3]=tangential, res[3:6]=torque; "
                                    "efc_force excluded",
            "torque_joint": "wheel_L / wheel_R act on hinge wheel_L_spin / wheel_R_spin, N*m, forward positive",
            "empty_field": "no contact or invalid sample",
            "zero_literal": "active contact with measured force 0.0",
        },
        "data_quality": {
            "invalid_cases": [c["case_id"] for c in case_meta
                              if c["outcome"] == INVALID],
            "no_contact_cases": [c["case_id"] for c in case_meta
                                 if c["invalid_reason"] == "no_contact"],
            "penetration_max_m": max((c["penetration_max_m"] or 0.0) for c in case_meta),
            "empty_field": "no contact or invalid sample",
            "zero_literal": "active contact with measured force 0.0",
        },
        "notes": [
            "基准机型 oomwoo；结构来自 makerspet/oomwoo-one URDF，数值来自 params/oomwoo.json，逐项带来源标签。",
            "未做本机实测复核；本批结论封顶机理 + 参数敏感性，不是产品能力判定。",
            "力矩列为轮端执行器力（gear=1），关节 wheel_*_spin，单位 N*m，前进为正；"
            "同时给出原始 qvel 与 actuator_force 列。",
            "契约 v1.7.1 §1.1 将 wheel_*_speed 写成 -qvel；按 B 系右手定则，"
            "+x 前向、+y 左向时前进对应 +qvel。本批按物理前进为正输出，差异在此留痕。",
            "无接触/无效采样写空字段；0.0 只表示有接触且实测合力为零。",
            "outcome 只描述本次算例是否越过并恢复前进，不是验收判定。",
        ],
    }
    (out_dir / "run.json").write_text(
        json.dumps(jsonable(run_json), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    readme = [
        "本目录由 scripts/run_cases.py 生成。",
        "",
        "summary.csv: 一行 = 一个 case × 一次重复。outcome 取值 cleared / blocked / invalid；",
        "             invalid 表示本次数据不可用（no_contact / penetration_exceeded /",
        "             creep_baseline_exceeded / impact_frame_mismatch），不是物理结论。",
        "             failure_mode 是机理名（topple / belly_contact / slip_stall / lift_fail /",
        "             timeout / recover_fail / retreat / no_contact 等）。",
        "             A1–A4 取 met / not_met / na，阈值见 run.json 的 criteria。",
        "",
        "timeseries.csv: t=0 为第一次 mj_step 之前，t 为仿真时间；所有列共用同一时间基准。",
        "                wheel_*_torque_nm 是 wheel_*_spin 铰上的轮端执行器力矩，单位 N*m，前进为正；",
        "                原始 wheel_*_qvel_radps 与 wheel_*_actuator_force_nm 同时保留。",
        "                接触力只来自 mj_contactForce（接触帧；法向/切向取模长）。",
        "                contact_*_active=0 时力列为空；active=1 时力列非空，可以是 0.0。",
        "                data_valid=0 表示该行接触数据无效，相关力列为空而不是 0.0。",
        "",
        "run.json: 基准机型 oomwoo、生效的 <option>、版本、Git SHA、模板/参数/config sha256、",
        "           蠕滑基线、判据阈值与逐 case 结果；params 段逐项带来源标签。",
    ]
    (out_dir / "README.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"summary: {out_dir / 'summary.csv'}")
    print(f"run.json: {out_dir / 'run.json'}")
    return 0


def _unit_of(column: str) -> str:
    if column.endswith("_mps2"):
        return "m/s^2"
    if column.endswith("_mps"):
        return "m/s"
    if column.endswith("_radps"):
        return "rad/s"
    if column.endswith("_rad"):
        return "rad"
    if column.endswith("_deg"):
        return "deg"
    if column.endswith("_nm"):
        return "N*m"
    if column.endswith("_n"):
        return "N"
    if column.endswith("_m"):
        return "m"
    if column.endswith("_s"):
        return "s"
    if column.endswith("_kg"):
        return "kg"
    if column.endswith("_ratio") or column in {"slip_max", "A4_steady_step_ratio",
                                               "A4_transient_step_ratio"}:
        return "-"
    return "-"


if __name__ == "__main__":
    raise SystemExit(main())
