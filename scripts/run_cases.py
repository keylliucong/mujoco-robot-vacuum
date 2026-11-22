"""G2 批运行入口：模型 + case JSON → outputs/<batch_id>/{run.json,summary.csv,<case>/timeseries.csv}。

契约 v1.7（文档版本 1.7.1）。要点：
- 台阶不写进 MJCF，由本文件按 scenario.obstacle 注入，记 scenario_xml_sha256；
- 每批次先跑「静置蠕滑基线」，红线（>1 mm/s 或 10 s 漂移 >0.5 mm）触发 1 ms / 0.5 ms
  降档重跑，双档同报（run.json.cases[].repeats[].tiers[]）；
- 数值设置从 JSON 注入并回读断言（S15）；批次目录已存在即退出（S12）；
- 判定只在 judge.py（不 import mujoco），本文件不算 passed。

用法（Windows，项目 .venv）：
    .venv\\Scripts\\python.exe scripts\\run_cases.py --config cases\\baseline.json --out outputs\\baseline --repeat 2
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import mujoco
import numpy as np

CONTRACT_VERSION = "1.7.7"  # S14：等于契约文档版本；判据集仍冻结在 v1.7
SCHEMA_VERSION = "1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge  # noqa: E402
import model_checks  # noqa: E402
import obstacle  # noqa: E402
import params_io  # noqa: E402

LEDGER_PATH = REPO_ROOT / "docs" / "参数溯源.csv"
RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner.json"

FAILURE_ENUM = {
    "topple",
    "retreat",
    "timeout",
    "stall",
    "bottom_out",
    "suspension_bottom",
    "slip",
    "torque_limit",
    "no_contact",
    "data_invalid",
}

PAIR_GEOMS = obstacle.PAIR_GEOMS

CASE_KEYS = {
    "schema_version",
    "case_id",
    "model",
    "scenario",
    "environment",
    "drive",
    "numerics",
    "judge",
    "seed",
    "regression_expect",
    "notes",
}

SCENARIO_KEYS = {"kind", "obstacle", "heading_deg", "approach"}
APPROACH_KEYS = {"speed_mps", "start_distance_m", "settle_s", "settle_tol_mps"}
OBSTACLE_KEYS = {"shape", "height_m", "edge_radius_m", "top_width_m"}
NUMERICS_KEYS = {"timestep_s", "integrator", "solver", "cone", "iterations"}
JUDGE_KEYS = {
    "window_s",
    "fail_on",
    "min_advance_body_lengths",
    "recover_speed_ratio",
    "recover_hold_s",
    "stall",
    "tilt",
    "slip_ratio",
    "contact_normal_min_n",
}

TIMESERIES_COLUMNS = [
    "t_s",
    "pos_x_m",
    "pos_y_m",
    "pos_z_m",
    "quat_w",
    "quat_x",
    "quat_y",
    "quat_z",
    "pitch_rad",
    "roll_rad",
    "yaw_rad",
    "vel_x_mps",
    "vel_y_mps",
    "vel_z_mps",
    "wheel_L_speed_radps",
    "wheel_R_speed_radps",
    "wheel_L_torque_nm",
    "wheel_R_torque_nm",
    "susp_L_travel_m",
    "susp_R_travel_m",
]

TIMESERIES_TAIL = ["chassis_min_z_m"]

SUMMARY_COLUMNS = [
    "case_id",
    "repeat",
    "status",
    "passed",
    "failure_primary",
    "failure_flags",
    "t_trigger_s",
    "t_climb_s",
    "t_recover_s",
    "advance_m",
    "v_recover_mps",
    "pitch_max_deg",
    "roll_max_deg",
    "slip_max_L",
    "slip_max_R",
    "torque_max_L_nm",
    "torque_max_R_nm",
    "susp_travel_max_L_m",
    "susp_travel_max_R_m",
    "contact_normal_max_n",
    "timestep_s",
    "integrator",
    "cone",
    "seed",
    "model_sha256",
    "config_sha256",
    "conclusion_level",
    "output_dir",
]

SUMMARY_METRIC_KEYS = [
    "t_trigger_s",
    "t_climb_s",
    "t_recover_s",
    "advance_m",
    "v_recover_mps",
    "pitch_max_deg",
    "roll_max_deg",
    "slip_max_L",
    "slip_max_R",
    "torque_max_L_nm",
    "torque_max_R_nm",
    "susp_travel_max_L_m",
    "susp_travel_max_R_m",
    "contact_normal_max_n",
]

UNIT_SUFFIXES = [
    ("_radps", "rad/s"),
    ("_mps", "m/s"),
    ("_deg", "deg"),
    ("_rad", "rad"),
    ("_nm", "N*m"),
    ("_m", "m"),
    ("_s", "s"),
    ("_n", "N"),
]

DIMENSIONLESS_COLUMNS = {"quat_w", "quat_x", "quat_y", "quat_z"}

INTEGRATORS = {
    "implicitfast": mujoco.mjtIntegrator.mjINT_IMPLICITFAST,
    "implicit": mujoco.mjtIntegrator.mjINT_IMPLICIT,
    "euler": mujoco.mjtIntegrator.mjINT_EULER,
    "rk4": mujoco.mjtIntegrator.mjINT_RK4,
}
SOLVERS = {
    "Newton": mujoco.mjtSolver.mjSOL_NEWTON,
    "CG": mujoco.mjtSolver.mjSOL_CG,
    "PGS": mujoco.mjtSolver.mjSOL_PGS,
}
CONES = {
    "pyramidal": mujoco.mjtCone.mjCONE_PYRAMIDAL,
    "elliptic": mujoco.mjtCone.mjCONE_ELLIPTIC,
}


class ContractError(RuntimeError):
    """契约违规：一律 raise，不静默降级。"""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel_to_repo(path):
    """仓库内路径写相对路径；临时目录里的配置（负例/高度扫描）写绝对路径。"""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        return str(Path(path).resolve())


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def require_keys(obj, allowed, where):
    unknown = set(obj).difference(allowed)
    if unknown:
        raise ContractError(f"{where} 出现未定义键：{sorted(unknown)}")


def forbid_expectation_keys(obj, where):
    banned = {"expected", "passed", "result", "expect"}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in banned:
                raise ContractError(f"{where} 出现期望结果键 {key!r}（S09）")
            if key == "regression_expect":
                continue
            forbid_expectation_keys(value, f"{where}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            forbid_expectation_keys(value, f"{where}[{index}]")


def load_case(path):
    config = read_json(path)
    require_keys(config, CASE_KEYS, "case")
    forbid_expectation_keys(config, "case")
    case_id = config.get("case_id", "")
    if not re.fullmatch(r"[a-z0-9_]+", case_id):
        raise ContractError(f"case_id 非法：{case_id!r}")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"schema_version 必须是 {SCHEMA_VERSION}")
    require_keys(config["scenario"], SCENARIO_KEYS, "scenario")
    require_keys(config["scenario"]["approach"], APPROACH_KEYS, "scenario.approach")
    require_keys(config["numerics"], NUMERICS_KEYS, "numerics")
    require_keys(config["judge"], JUDGE_KEYS, "judge")
    require_keys(config["judge"]["stall"], {"speed_mps", "duration_s"}, "judge.stall")
    require_keys(config["judge"]["tilt"], {"pitch_deg", "roll_deg"}, "judge.tilt")
    if config["scenario"]["kind"] not in ("flat", "step"):
        raise ContractError("scenario.kind 只能是 flat 或 step")
    if config["scenario"]["kind"] == "flat":
        if "obstacle" in config["scenario"]:
            raise ContractError("flat 工况禁止出现 obstacle 块（抽查 2）")
    else:
        if "obstacle" not in config["scenario"]:
            raise ContractError("step 工况缺 scenario.obstacle")
        require_keys(config["scenario"]["obstacle"], OBSTACLE_KEYS, "scenario.obstacle")
        obstacle = config["scenario"]["obstacle"]
        if obstacle["shape"] not in ("box", "cylinder"):
            raise ContractError("obstacle.shape 只能是 box 或 cylinder")
        if obstacle["height_m"] <= 0:
            raise ContractError("obstacle.height_m 必须 > 0")
        if obstacle["edge_radius_m"] < 0:
            raise ContractError("obstacle.edge_radius_m 必须 >= 0")
        if obstacle["shape"] == "box" and obstacle["top_width_m"] <= 0:
            raise ContractError("obstacle.top_width_m 必须 > 0")
    heading = config["scenario"]["heading_deg"]
    if abs(heading) > 60:
        raise ContractError("heading_deg 超出 ±60")
    approach = config["scenario"]["approach"]
    if approach["speed_mps"] <= 0:
        raise ContractError("approach.speed_mps 必须 > 0")
    if approach["start_distance_m"] < 0.3:  # contract-tolerance
        raise ContractError("approach.start_distance_m 必须 >= 0.3")
    if approach["settle_s"] < 0.5:  # contract-tolerance
        raise ContractError("approach.settle_s 必须 >= 0.5")
    if approach["settle_tol_mps"] <= 0:
        raise ContractError("approach.settle_tol_mps 必须 > 0")
    if config["numerics"]["timestep_s"] <= 0:
        raise ContractError("numerics.timestep_s 必须 > 0")
    if config["numerics"]["integrator"] not in INTEGRATORS:
        raise ContractError(f"未知 integrator：{config['numerics']['integrator']}")
    if config["numerics"]["solver"] not in SOLVERS:
        raise ContractError(f"未知 solver：{config['numerics']['solver']}")
    if config["numerics"]["cone"] not in CONES:
        raise ContractError(f"未知 cone：{config['numerics']['cone']}")
    if not isinstance(config["numerics"]["iterations"], int):
        raise ContractError("numerics.iterations 必须是整数")
    fail_on = config["judge"]["fail_on"]
    if not isinstance(fail_on, list) or not set(fail_on).issubset(FAILURE_ENUM):
        raise ContractError(f"judge.fail_on 不是失败类别枚举的子集：{fail_on}")
    if config["judge"]["window_s"] <= 0:
        raise ContractError("judge.window_s 必须 > 0")
    if not isinstance(config["seed"], int):
        raise ContractError("seed 必须是整数")
    for key, spec in config["environment"]["pairs"].items():
        if "--" not in key:
            raise ContractError(f"接触对名必须形如 a--b：{key}")
        side_a, _, side_b = key.partition("--")
        for side in (side_a, side_b):
            if side not in PAIR_GEOMS:
                raise ContractError(f"未知接触对成员：{side}")
        if set(spec) != {"friction", "condim"}:
            raise ContractError(f"{key} 只允许 friction/condim")
        if len(spec["friction"]) != 5:
            raise ContractError(
                f"{key}.friction 必须是 5 分量 [slide1, slide2, spin, roll1, roll2]；"
                f"实际 {len(spec['friction'])} 个。单值/3 分量会让其余分量回落默认，禁止"
            )
        if float(spec["friction"][0]) != float(spec["friction"][1]):
            raise ContractError(
                f"{key}.friction 非各向同性：slide1={spec['friction'][0]} "
                f"slide2={spec['friction'][1]}（S24 要求相等）"
            )
        if spec["condim"] not in (1, 3, 4, 6):
            raise ContractError(f"{key}.condim 非法：{spec['condim']}")
        if side_a.startswith("wheel") and spec["condim"] in (4, 6):
            raise ContractError(
                f"{key} 打开 condim={spec['condim']}：res[3..5] 的扭转/滚阻读数须先做专项校验，"
                "未校验不得引用；v1 拒绝运行（物理侧硬约束 3）"
            )
    for channel in ("wheel_L", "wheel_R"):
        if channel not in config["drive"]["channels"]:
            raise ContractError(f"缺 drive.channels.{channel}")
        if config["drive"]["channels"][channel]["torque_limit_nm"] <= 0:
            raise ContractError(f"{channel}.torque_limit_nm 必须 > 0")
    return config


def load_runner_defaults():
    defaults = read_json(RUNNER_DEFAULTS)
    if defaults.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("cases/_runner.json schema_version 不匹配")
    return defaults


def parse_config_id(config):
    match = re.search(r"config_id=([a-z0-9_]+)", config.get("notes", ""))
    if not match:
        raise ContractError("case.notes 必须写 config_id=...（模型参数集与本 case 同 ID，S21）")
    return match.group(1)


def pair_geom_names(key, obstacle_shape):
    return obstacle.pair_geom_names(key, obstacle_shape)


def build_scenario_xml(model_text, config, chassis_front_m, defaults):
    return obstacle.inject(model_text, config, chassis_front_m, defaults)


def apply_numerics(model, numerics, timestep_s, overrides):
    model.opt.timestep = float(timestep_s)
    model.opt.integrator = int(INTEGRATORS[numerics["integrator"]])
    model.opt.solver = int(SOLVERS[numerics["solver"]])
    model.opt.cone = int(CONES[numerics["cone"]])
    model.opt.iterations = int(numerics["iterations"])
    effective = {
        "timestep_s": float(model.opt.timestep),
        "integrator": int(model.opt.integrator),
        "solver": int(model.opt.solver),
        "cone": int(model.opt.cone),
        "iterations": int(model.opt.iterations),
    }
    if effective["timestep_s"] != float(timestep_s):
        raise ContractError("timestep 回读不一致")
    if effective["integrator"] != int(INTEGRATORS[numerics["integrator"]]):
        raise ContractError("integrator 回读不一致")
    if effective["solver"] != int(SOLVERS[numerics["solver"]]):
        raise ContractError("solver 回读不一致")
    if effective["cone"] != int(CONES[numerics["cone"]]):
        raise ContractError("cone 回读不一致")
    if effective["iterations"] != int(numerics["iterations"]):
        raise ContractError("iterations 回读不一致")
    if float(timestep_s) != float(numerics["timestep_s"]):
        overrides.append(
            {
                "path": "numerics.timestep_s",
                "requested": float(timestep_s),
                "source": "creep_downgrade",
            }
        )
    return effective


def apply_torque_limits(model, config, overrides):
    limits = {}
    for name in ("wheel_L", "wheel_R"):
        limit = float(config["drive"]["channels"][name]["torque_limit_nm"])
        aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        if aid < 0:
            raise ContractError(f"模型缺执行器 {name}")
        if float(model.actuator_forcerange[aid][1]) != limit:
            model.actuator_forcerange[aid][:] = np.array([-limit, limit])
            model.actuator_ctrlrange[aid][:] = np.array([-limit, limit])
            model.actuator_forcelimited[aid] = 1
            model.actuator_ctrllimited[aid] = 1
            overrides.append(
                {
                    "path": f"drive.channels.{name}.torque_limit_nm",
                    "requested": limit,
                    "source": "case_json",
                }
            )
        readback = float(model.actuator_forcerange[aid][1])
        if readback != limit:
            raise ContractError(f"{name} forcerange 回读 {readback} != {limit}")
        limits[name] = limit
    return limits


def geom_name_table(model):
    return {gid: model.geom(gid).name for gid in range(model.ngeom)}


def build_pair_lookup(config, obstacle_shape):
    lookup = {}
    ordered = []
    for key in config["environment"]["pairs"]:
        names_a, names_b = pair_geom_names(key, obstacle_shape)
        found = False
        for name_a in names_a:
            for name_b in names_b:
                if name_b.startswith("step") and obstacle_shape != "step":
                    continue
                lookup[frozenset((name_a, name_b))] = key
                found = True
        if found:
            ordered.append(key)
    return lookup, ordered


def _expand_friction(values, where):
    """把 geom 的 3 分量 friction 展开成 pair 的 5 分量。

    MuJoCo 的 pair friction 是 [slide1, slide2, spin, roll1, roll2]；geom friction
    是 [slide, spin, roll]。无 pair 时接触 friction 由两侧 geom 逐分量取最大，
    因此先把 geom 侧展开成 slide1=slide2、roll1=roll2。
    """
    vals = [float(v) for v in values]
    if len(vals) == 5:
        return tuple(vals)
    if len(vals) == 3:
        slide, spin, roll = vals
        return (slide, slide, spin, roll, roll)
    raise ContractError(f"{where} friction 必须是 3 或 5 分量，实际 {len(vals)}")


def build_contact_spec(root, config, obstacle_shape):
    """从注入后的 XML 与 case JSON 建期望接触表；断言只读 d.contact[i].friction。"""
    default_geom = root.find("./default/geom")
    default_friction = None
    default_condim = 3
    if default_geom is not None:
        if default_geom.get("friction"):
            default_friction = _expand_friction(
                default_geom.get("friction").split(), "default/geom"
            )
        if default_geom.get("condim"):
            default_condim = int(default_geom.get("condim"))
    geom_spec = {}
    for geom in root.iter("geom"):
        name = geom.get("name")
        if not name:
            continue
        raw = geom.get("friction")
        friction = (
            _expand_friction(raw.split(), f"geom {name}")
            if raw
            else default_friction
        )
        if friction is None:
            raise ContractError(f"geom {name} 无 friction 且无 default 可继承")
        geom_spec[name] = (
            int(geom.get("condim", default_condim)),
            friction,
        )

    pair_spec = {}
    for key, spec in config["environment"]["pairs"].items():
        names_a, names_b = pair_geom_names(key, obstacle_shape)
        friction = tuple(float(v) for v in spec["friction"])
        for name_a in names_a:
            for name_b in names_b:
                if name_a in geom_spec and name_b in geom_spec:
                    pair_spec[frozenset((name_a, name_b))] = (
                        int(spec["condim"]),
                        friction,
                    )
    return {"pairs": pair_spec, "geoms": geom_spec}


def assert_contact_friction(data, geom_names, contact_spec, where):
    """S24：dim、各向同性、期望 slide 三条逐接触断言；真值只读 d.contact.friction。"""
    for i in range(data.ncon):
        contact = data.contact[i]
        name1 = geom_names.get(int(contact.geom1))
        name2 = geom_names.get(int(contact.geom2))
        key = frozenset((name1, name2))
        if key in contact_spec["pairs"]:
            expected_dim, expected_friction = contact_spec["pairs"][key]
            source = "pair"
        else:
            g1 = contact_spec["geoms"].get(name1)
            g2 = contact_spec["geoms"].get(name2)
            if g1 is None or g2 is None:
                raise ContractError(f"{where}: 接触 geom {name1}/{name2} 不在期望表")
            expected_dim = max(g1[0], g2[0])
            expected_friction = tuple(
                max(g1[1][j], g2[1][j]) for j in range(5)
            )
            source = "geom-max"
        actual = tuple(float(v) for v in contact.friction)
        if int(contact.dim) != expected_dim:
            raise ContractError(
                f"{where}: {name1}/{name2} dim={contact.dim} != 期望 {expected_dim}"
            )
        if abs(actual[0] - actual[1]) > 1e-12:  # arithmetic
            raise ContractError(
                f"{where}: {name1}/{name2} friction 非各向同性 "
                f"slide1={actual[0]} slide2={actual[1]}"
            )
        for j, (got, exp) in enumerate(zip(actual, expected_friction)):
            if abs(got - exp) > 1e-12:  # arithmetic
                raise ContractError(
                    f"{where}: {name1}/{name2} friction[{j}]={got} != {exp}（{source}）"
                )


def contact_columns(ordered_pairs):
    columns = []
    for key in ordered_pairs:
        columns.extend(
            [
                f"contact_{key}_active",
                f"contact_{key}_normal_n",
                f"contact_{key}_tangent_n",
                f"contact_{key}_count",
            ]
        )
    return columns


def make_columns(ordered_pairs):
    return TIMESERIES_COLUMNS + contact_columns(ordered_pairs) + TIMESERIES_TAIL


def sample_row(model, data, pair_lookup, ordered_pairs, geom_names):
    xpos = np.array(data.body("chassis").xpos, dtype=float)
    xquat = np.array(data.body("chassis").xquat, dtype=float)
    qvel = np.array(data.joint("chassis_free").qvel, dtype=float)
    pitch, roll, yaw = model_checks.euler_zyx(xquat)
    row = {
        "t_s": float(data.time),
        "pos_x_m": float(xpos[0]),
        "pos_y_m": float(xpos[1]),
        "pos_z_m": float(xpos[2]),
        "quat_w": float(xquat[0]),
        "quat_x": float(xquat[1]),
        "quat_y": float(xquat[2]),
        "quat_z": float(xquat[3]),
        "pitch_rad": pitch,
        "roll_rad": roll,
        "yaw_rad": yaw,
        "vel_x_mps": float(qvel[0]),
        "vel_y_mps": float(qvel[1]),
        "vel_z_mps": float(qvel[2]),
    }
    spin_l = float(np.asarray(data.joint("wheel_L_spin").qvel).reshape(-1)[0])
    spin_r = float(np.asarray(data.joint("wheel_R_spin").qvel).reshape(-1)[0])
    # 契约 §1.1 同时写了「前进为正」和 speed=-qvel；在 +y 轮轴、右手系下
    # 前进 +x 对应 qvel 为正，二者不可同时成立。干跑按「前进为正」落列，
    # 取 +qvel；该契约内部矛盾见 docs/干跑/抽查报告.md。
    row["wheel_L_speed_radps"] = spin_l
    row["wheel_R_speed_radps"] = spin_r
    row["wheel_L_torque_nm"] = float(np.asarray(data.actuator("wheel_L").force).reshape(-1)[0])
    row["wheel_R_torque_nm"] = float(np.asarray(data.actuator("wheel_R").force).reshape(-1)[0])
    row["susp_L_travel_m"] = float(np.asarray(data.joint("susp_L").qpos).reshape(-1)[0])
    row["susp_R_travel_m"] = float(np.asarray(data.joint("susp_R").qpos).reshape(-1)[0])

    counts = {key: 0 for key in ordered_pairs}
    normals = {key: 0.0 for key in ordered_pairs}
    shear_x = {key: 0.0 for key in ordered_pairs}
    shear_y = {key: 0.0 for key in ordered_pairs}
    force = np.zeros(6)
    for i in range(data.ncon):
        contact = data.contact[i]
        name1 = geom_names.get(int(contact.geom1))
        name2 = geom_names.get(int(contact.geom2))
        key = pair_lookup.get(frozenset((name1, name2)))
        if key is None:
            continue
        mujoco.mj_contactForce(model, data, i, force)
        counts[key] += 1
        normals[key] += float(force[0])
        shear_x[key] += float(force[1])
        shear_y[key] += float(force[2])
    for key in ordered_pairs:
        active = 1 if counts[key] > 0 else 0
        row[f"contact_{key}_active"] = active
        row[f"contact_{key}_normal_n"] = normals[key] if active else None
        row[f"contact_{key}_tangent_n"] = (
            math.hypot(shear_x[key], shear_y[key]) if active else None
        )
        row[f"contact_{key}_count"] = counts[key]
    row["chassis_min_z_m"] = model_checks.chassis_min_z(model, data)
    return row


def reset_state(model, data):
    mujoco.mj_resetData(model, data)
    qpos = data.joint("chassis_free").qpos
    qpos[:] = np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    mujoco.mj_forward(model, data)


def step_once(model, data):
    mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)


def zero_drive(data):
    for name in ("wheel_L", "wheel_R"):
        data.actuator(name).ctrl[:] = 0.0


def set_drive(model, data, limits, kp, ki, integral, speed_cmd, radius, dt):
    """轮速 PI：P 项 + 积分项；积分限幅来自 cases/_runner.json（有台账行）。

    只有 P 项时，关节阻尼 0.02 N·m·s/rad 会造成稳态转速跌落，
    低速工况永远到不了指令速度；积分项补上这个跌落。
    """
    clamp = float(load_runner_defaults()["drive"]["integral_clamp_nm"])
    for name in ("wheel_L", "wheel_R"):
        speed_rad = float(np.asarray(data.joint(f"{name}_spin").qvel).reshape(-1)[0])
        v_wheel = speed_rad * radius
        error = speed_cmd - v_wheel
        integral[name] = max(-clamp, min(clamp, integral[name] + ki * error * dt))
        torque = kp * error + integral[name]
        limit = limits[name]
        torque = max(-limit, min(limit, torque))
        data.actuator(name).ctrl[:] = torque


def run_creep(model, data, defaults, wheel_radius_m):
    creep_cfg = defaults["creep"]
    step = float(model.opt.timestep)
    reset_state(model, data)
    for _ in range(int(round(creep_cfg["settle_s"] / step))):
        zero_drive(data)
        step_once(model, data)
    start = np.array(data.body("chassis").xpos, dtype=float)
    speeds = []
    for _ in range(int(round(creep_cfg["window_s"] / step))):
        zero_drive(data)
        step_once(model, data)
        speed = float(
            np.linalg.norm(np.asarray(data.joint("chassis_free").qvel, dtype=float)[:3])
        )
        speeds.append(speed)
    end = np.array(data.body("chassis").xpos, dtype=float)
    tail = max(1, int(round(creep_cfg["residual_tail_s"] / step)))
    drift = float(np.linalg.norm(end - start))
    residual = float(max(speeds[-tail:])) if speeds else 0.0
    redline = residual > creep_cfg["max_residual_speed_mps"] or drift > creep_cfg["max_drift_m"]
    return {
        "settle_s": creep_cfg["settle_s"],
        "window_s": creep_cfg["window_s"],
        "drift_m": drift,
        "residual_speed_mps": residual,
        "max_residual_speed_mps": creep_cfg["max_residual_speed_mps"],
        "max_drift_m": creep_cfg["max_drift_m"],
        "redline": redline,
        "wheel_radius_m": wheel_radius_m,
    }


def run_case(
    model,
    data,
    config,
    defaults,
    limits,
    ordered_pairs,
    pair_lookup,
    geom_names,
    radius,
    contact_spec,
):
    approach = config["scenario"]["approach"]
    speed = approach["speed_mps"]
    window = config["judge"]["window_s"]
    step = float(model.opt.timestep)
    kp = defaults["drive"]["speed_kp_nm_per_mps"]
    ki = defaults["drive"]["speed_ki_nm_per_mps_s"]
    integral = {"wheel_L": 0.0, "wheel_R": 0.0}
    reset_state(model, data)
    assert_contact_friction(data, geom_names, contact_spec, "t=0")
    columns = make_columns(ordered_pairs)
    rows = []
    wheel_step = [k for k in ordered_pairs if k.startswith("wheel_") and k.endswith("--step")]
    trigger_time = 0.0 if config["scenario"]["kind"] == "flat" else None
    cap_time = (
        approach["settle_s"]
        + approach["start_distance_m"] / speed
        + defaults["time"]["approach_margin_s"]
        + window
    )
    max_steps = int(round(defaults["time"]["max_sim_s"] / step))
    for _ in range(max_steps):
        set_drive(model, data, limits, kp, ki, integral, speed, radius, step)
        step_once(model, data)
        assert_contact_friction(
            data, geom_names, contact_spec, f"{config['case_id']} t={data.time:.6f}"
        )
        row = sample_row(model, data, pair_lookup, ordered_pairs, geom_names)
        rows.append(row)
        if trigger_time is None:
            for key in wheel_step:
                if row[f"contact_{key}_active"] == 1:
                    trigger_time = row["t_s"]
                    break
        if trigger_time is not None and row["t_s"] >= trigger_time + window:
            break
        if trigger_time is None and row["t_s"] >= cap_time:
            break
    return {name: [row[name] for row in rows] for name in columns}, columns


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return f"{value:.9f}"


def write_timeseries(path, columns, table):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        count = len(table[columns[0]])
        for i in range(count):
            writer.writerow([format_value(table[col][i]) for col in columns])


def read_timeseries(path):
    """把已落盘的 CSV 按字符串读回，交给 judge（保证判定吃的是输出契约本身）。"""
    table = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for column in reader.fieldnames or []:
            table[column] = []
        for row in reader:
            for column in table:
                table[column].append(row[column])
    return table


def unit_for(column):
    if column in DIMENSIONLESS_COLUMNS:
        return "-"
    if column.endswith("_active"):
        return "flag"
    if column.endswith("_count"):
        return "count"
    if column.endswith("_ratio"):
        return "-"
    for suffix, unit in UNIT_SUFFIXES:
        if column.endswith(suffix):
            return unit
    return "-"


def column_metadata(columns):
    meta = {}
    for column in columns:
        meta[column] = {
            "unit": unit_for(column),
            "missing": column.endswith("_normal_n") or column.endswith("_tangent_n"),
        }
    return meta


def build_judge_params(config, defaults, model, limits, ordered_pairs, body_length_m, radius):
    approach = config["scenario"]["approach"]
    judge_cfg = config["judge"]
    kind = config["scenario"]["kind"]
    height = config["scenario"]["obstacle"]["height_m"] if kind == "step" else 0.0
    return {
        "kind": kind,
        "timestep_s": float(model.opt.timestep),
        "speed_mps": approach["speed_mps"],
        "window_s": judge_cfg["window_s"],
        "fail_on": list(judge_cfg["fail_on"]),
        "min_advance_m": judge_cfg["min_advance_body_lengths"] * body_length_m,
        "recover_speed_ratio": judge_cfg["recover_speed_ratio"],
        "recover_hold_s": judge_cfg["recover_hold_s"],
        "stall_speed_mps": judge_cfg["stall"]["speed_mps"],
        "stall_duration_s": judge_cfg["stall"]["duration_s"],
        "tilt_pitch_deg": judge_cfg["tilt"]["pitch_deg"],
        "tilt_roll_deg": judge_cfg["tilt"]["roll_deg"],
        "slip_ratio": judge_cfg["slip_ratio"],
        "contact_normal_min_n": judge_cfg["contact_normal_min_n"],
        "settle_tol_mps": approach["settle_tol_mps"],
        "settle_window_s": defaults["time"]["settle_check_window_s"],
        "settle_end_s": approach["settle_s"],
        "wheel_radius_m": radius,
        "step_height_m": height,
        "susp_range_m": MODEL_CONSTANTS["susp_range_m"],
        "susp_bottom_rel": defaults["tolerances"]["susp_bottom_rel"],
        "torque_limit_L_nm": limits["wheel_L"],
        "torque_limit_R_nm": limits["wheel_R"],
        "torque_saturation_rel": defaults["tolerances"]["torque_saturation_rel"],
        "slip_eps_mps": defaults["tolerances"]["slip_eps_mps"],
        "climb_height_ratio": defaults["tolerances"]["climb_height_ratio"],
        "climb_hold_s": defaults["tolerances"]["climb_hold_s"],
        "wheel_step_pairs": [
            k for k in ordered_pairs if k.startswith("wheel_") and k.endswith("--step")
        ],
        "bottom_out_pairs": [k for k in ordered_pairs if k.startswith("chassis--")],
        "all_pairs": list(ordered_pairs),
    }


MODEL_CONSTANTS = {"wheel_radius_m": 0.0, "susp_range_m": 0.0, "com_offset_B_m": (0.0, 0.0, 0.0)}


def load_ledger_rows():
    ledger = model_checks.load_ledger(LEDGER_PATH)
    # v1.7.6：结论等级只取绑定了 xpath 的行（真正进入模型/判定的那些）
    bound = {
        param_id: row["label"]
        for param_id, row in ledger.items()
        if row["xpath"].strip() not in ("", "-")
    }
    return ledger, bound


def conclusion_level(labels):
    if any(label in ("缺失", "待标定") for label in labels.values()):
        return "mechanism"
    if any(label in ("图纸推算", "公开参考", "工程假设") for label in labels.values()):
        return "sensitivity"
    return "quantitative"


def chassis_front(model):
    front = None
    for gid in range(model.ngeom):
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        edge = float(model.geom_pos[gid][0] + model.geom_size[gid][0])
        front = edge if front is None else max(front, edge)
    if front is None:
        raise ContractError("chassis_* 中没有几何")
    return front


def git_info():
    import subprocess

    def run(*cmd):
        try:
            return subprocess.check_output(cmd, cwd=REPO_ROOT, text=True).strip()
        except Exception:
            return ""

    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(run("git", "status", "--porcelain")),
    }


def label_counts(labels):
    counts = {}
    for label in labels.values():
        counts[label] = counts.get(label, 0) + 1
    return counts


def dedupe_overrides(overrides):
    seen = []
    for item in overrides:
        if item not in seen:
            seen.append(item)
    return seen


def write_summary(path, rows, config, model_sha, config_sha, level):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SUMMARY_COLUMNS)
        for row in rows:
            metrics = row["metrics"]
            writer.writerow(
                [row["case_id"], row["repeat"], row["status"], row["passed"], row["failure_primary"], row["failure_flags"]]
                + [format_value(metrics[key]) for key in SUMMARY_METRIC_KEYS]
                + [
                    format_value(row["timestep_s"]),
                    config["numerics"]["integrator"],
                    config["numerics"]["cone"],
                    config["seed"],
                    model_sha,
                    row.get("config_sha256", config_sha),
                    level,
                    row["output_dir"],
                ]
            )


def check_consistency(out_dir, repeat_results):
    if len(repeat_results) < 2:
        return True
    digests = set()
    metrics = set()
    for item in repeat_results:
        digests.add(sha256_file(out_dir / item["output_dir"] / "timeseries.csv"))
        base = item["tiers"][0]["verdict"]
        metrics.add(
            (
                base["status"],
                base["passed"],
                base["failure_primary"],
                tuple(sorted(base["failure_flags"])),
                tuple((k, base["metrics"][k]) for k in SUMMARY_METRIC_KEYS),
            )
        )
    return len(digests) == 1 and len(metrics) == 1


def check_regression(config, repeat_results):
    expected = config.get("regression_expect")
    if not expected:
        return {"checked": False}
    base = repeat_results[0]["tiers"][0]["verdict"]
    actual = {"passed": bool(base["passed"]), "failure_primary": base["failure_primary"]}
    matched = actual["passed"] == expected["passed"] and (
        not expected.get("failure_primary")
        or actual["failure_primary"] == expected["failure_primary"]
    )
    return {"checked": True, "expected": expected, "actual": actual, "matched": matched}


REQUIRED_RUN_KEYS = [
    "contract_version",
    "schema_version",
    "batch_id",
    "git",
    "model",
    "config",
    "scenario_xml_sha256",
    "com_offset_B_m",
    "frame",
    "python",
    "mujoco",
    "numpy",
    "os",
    "platform",
    "numerics",
    "overrides",
    "seed",
    "seed_used",
    "params",
    "param_labels",
    "conclusion_level",
    "repeat",
    "started_utc",
    "finished_utc",
    "cases",
    "columns",
    "data_quality",
]


def validate_run_json(run_json):
    missing = [key for key in REQUIRED_RUN_KEYS if key not in run_json]
    if missing:
        raise ContractError(f"run.json 缺必备键，拒绝产出 summary.csv（S11）：{missing}")
    for key in ("commit", "branch", "dirty"):
        if key not in run_json["git"]:
            raise ContractError(f"run.json.git 缺 {key}")
    if not run_json["scenario_xml_sha256"]:
        raise ContractError("run.json.scenario_xml_sha256 为空")


def _case_name(case_id, repeat, total_repeats):
    return case_id if total_repeats == 1 else f"{case_id}_r{repeat}"


def _combined_config_sha(config_paths):
    payload = "\n".join(f"{path}:{sha256_file(path)}" for path in config_paths)
    return sha256_text(payload)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="G2 批运行入口")
    parser.add_argument("--cases", nargs="+", required=True, help="一个或多个 case JSON")
    parser.add_argument("--batch-id", default=None, help="批次目录名；缺省用时间戳")
    parser.add_argument("--out", default=None, help="批次输出根目录（默认 outputs/<batch_id>）")
    parser.add_argument("--repeat", type=int, default=1, help="每个 case 的重复次数")
    args = parser.parse_args(argv)

    if args.repeat < 1:
        raise ContractError("--repeat 必须 >= 1")
    if args.batch_id:
        batch_id = args.batch_id
    else:
        batch_id = "oomwoo_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", batch_id):
        raise ContractError(f"batch_id 非法：{batch_id!r}")
    out_dir = Path(args.out) if args.out else REPO_ROOT / "outputs" / batch_id
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    if out_dir.exists():
        raise ContractError(f"批次目录已存在，拒绝覆盖（S12）：{out_dir}")

    started = datetime.now(timezone.utc).isoformat()
    config_paths = []
    for raw in args.cases:
        path = Path(raw)
        if not path.is_absolute():
            path = REPO_ROOT / path
        config_paths.append(path)
    configs = [load_case(path) for path in config_paths]
    case_ids = [config["case_id"] for config in configs]
    if len(set(case_ids)) != len(case_ids):
        raise ContractError(f"同批次 case_id 必须唯一：{case_ids}")
    defaults = load_runner_defaults()

    model_rel = configs[0]["model"]["path"]
    model_path = (REPO_ROOT / model_rel).resolve()
    model_sha = sha256_file(model_path)
    for config in configs:
        if config["model"]["path"] != model_rel:
            raise ContractError("同批次只允许一个模型路径（多机型请分批次）")
        if config["model"]["sha256"] != model_sha:
            raise ContractError(
                f"模型 sha256 与配置不符：{model_sha} != {config['model']['sha256']}"
            )

    ledger, labels = load_ledger_rows()
    radius = model_checks.ledger_value(ledger, "geom.wheel_radius_m")
    MODEL_CONSTANTS["wheel_radius_m"] = radius
    MODEL_CONSTANTS["susp_range_m"] = model_checks.ledger_value(ledger, "susp.travel_limit_m")
    MODEL_CONSTANTS["com_offset_B_m"] = model_checks.declared_com_offset(ledger)

    rendered = params_io.load_and_render(model_path)
    params_document = rendered["params"]
    model_text = rendered["text"]
    config_ids = {parse_config_id(config) for config in configs}
    if config_ids != {params_document["config_id"]}:
        raise ContractError(
            f"case 的 config_id={sorted(config_ids)} 与参数集 "
            f"{params_document['config_id']} 不一致（v1.4/S21）"
        )
    base_model = mujoco.MjModel.from_xml_string(model_text)
    base_data = mujoco.MjData(base_model)
    mujoco.mj_forward(base_model, base_data)
    model_root = ET.fromstring(model_text)
    model_checks.run_checks(base_model, base_data, ledger, model_root=model_root)
    body_length_m = model_checks.body_length(base_model)
    chassis_front_m = chassis_front(base_model)

    out_dir.mkdir(parents=True)
    print(f"batch_id: {out_dir.name}")
    print(f"contract_version: {CONTRACT_VERSION}")
    print(f"model: {model_rel} sha256={model_sha}")
    print(
        f"params: {params_document['config_id']} machine={params_document['machine']} "
        f"missing={params_io.missing_ids(params_document)}"
    )
    print(f"git: {git_info()}")

    summary_rows = []
    case_entries = []
    run_overrides = []
    all_columns = {}
    scenario_shas = []
    effective_numerics = []

    for config, config_path in zip(configs, config_paths):
        config_sha = sha256_file(config_path)
        scenario_xml = build_scenario_xml(model_text, config, chassis_front_m, defaults)
        scenario_sha = sha256_text(scenario_xml)
        scenario_shas.append(scenario_sha)
        contact_spec = build_contact_spec(
            ET.fromstring(scenario_xml), config, config["scenario"]["kind"]
        )
        print(f"[{config['case_id']}] config: {config_path} sha256={config_sha}")
        print(f"[{config['case_id']}] scenario_xml_sha256: {scenario_sha}")

        repeat_results = []
        case_summary = []
        for repeat in range(1, args.repeat + 1):
            case_name = _case_name(config["case_id"], repeat, args.repeat)
            case_dir = out_dir / case_name
            case_dir.mkdir(parents=True)
            (case_dir / "scenario.xml").write_text(scenario_xml, encoding="utf-8")

            model = mujoco.MjModel.from_xml_string(scenario_xml)
            numerics = apply_numerics(
                model, config["numerics"], config["numerics"]["timestep_s"], run_overrides
            )
            effective_numerics.append(numerics)
            limits = apply_torque_limits(model, config, run_overrides)
            data = mujoco.MjData(model)
            pair_lookup, ordered_pairs = build_pair_lookup(config, config["scenario"]["kind"])
            geom_names = geom_name_table(model)
            actual_columns = make_columns(ordered_pairs)
            for column in actual_columns:
                all_columns.setdefault(column, column_metadata(actual_columns)[column])

            creep = run_creep(model, data, defaults, radius)
            print(
                f"[{config['case_id']} r{repeat}] creep: drift={creep['drift_m'] * 1000:.4f} mm "
                f"residual={creep['residual_speed_mps'] * 1000:.4f} mm/s redline={creep['redline']}"
            )

            tiers = [("base", float(config["numerics"]["timestep_s"]))]
            if creep["redline"]:
                tiers += [
                    (f"downgrade_{int(round(t * 1000))}ms", float(t))
                    for t in defaults["creep"]["downgrade_tiers_s"]
                ]

            tier_results = []
            for tier_name, tier_step in tiers:
                if tier_step == float(config["numerics"]["timestep_s"]):
                    tier_model, tier_data, tier_limits = model, data, limits
                else:
                    tier_model = mujoco.MjModel.from_xml_string(scenario_xml)
                    apply_numerics(tier_model, config["numerics"], tier_step, run_overrides)
                    tier_limits = apply_torque_limits(tier_model, config, run_overrides)
                    tier_data = mujoco.MjData(tier_model)
                tier_dir = case_dir if tier_name == "base" else case_dir / tier_name
                tier_dir.mkdir(parents=True, exist_ok=True)
                table, columns = run_case(
                    tier_model,
                    tier_data,
                    config,
                    defaults,
                    tier_limits,
                    ordered_pairs,
                    pair_lookup,
                    geom_names,
                    radius,
                    contact_spec,
                )
                write_timeseries(tier_dir / "timeseries.csv", columns, table)
                params = build_judge_params(
                    config,
                    defaults,
                    tier_model,
                    tier_limits,
                    ordered_pairs,
                    body_length_m,
                    radius,
                )
                verdict = judge.judge_case(
                    read_timeseries(tier_dir / "timeseries.csv"), params
                )
                verdict["timestep_s"] = float(tier_model.opt.timestep)
                tier_results.append(
                    {
                        "tier": tier_name,
                        "timestep_s": float(tier_model.opt.timestep),
                        "verdict": verdict,
                        "dir": str(tier_dir.relative_to(out_dir)).replace(os.sep, "/"),
                    }
                )
                print(
                    f"[{config['case_id']} r{repeat} {tier_name}] status={verdict['status']} "
                    f"passed={verdict['passed']} primary={verdict['failure_primary']} "
                    f"flags={';'.join(verdict['failure_flags'])}"
                )

            base = tier_results[0]["verdict"]
            row = {
                "case_id": config["case_id"],
                "repeat": repeat,
                "status": base["status"],
                "passed": "" if base["passed"] is None else int(base["passed"]),
                "failure_primary": base["failure_primary"],
                "failure_flags": ";".join(base["failure_flags"]),
                "metrics": base["metrics"],
                "timestep_s": float(config["numerics"]["timestep_s"]),
                "config_sha256": config_sha,
                "output_dir": case_name,
            }
            summary_rows.append(row)
            case_summary.append(row)
            repeat_results.append(
                {
                    "repeat": repeat,
                    "output_dir": case_name,
                    "creep": creep,
                    "tiers": [
                        {
                            "tier": item["tier"],
                            "timestep_s": item["timestep_s"],
                            "dir": item["dir"],
                            "verdict": item["verdict"],
                        }
                        for item in tier_results
                    ],
                }
            )

        consistent = check_consistency(out_dir, repeat_results)
        regression = check_regression(config, repeat_results)
        case_entries.append(
            {
                "case_id": config["case_id"],
                "config": rel_to_repo(config_path),
                "config_sha256": config_sha,
                "scenario_xml_sha256": scenario_sha,
                "numerics": config["numerics"],
                "repeats": repeat_results,
                "regression": regression,
            }
        )

    consistent = all(check_consistency(out_dir, entry["repeats"]) for entry in case_entries)
    levels = conclusion_level(labels)
    config_list = [
        rel_to_repo(path) for path in config_paths
    ]
    combined_config_sha = _combined_config_sha(config_paths)
    combined_scenario_sha = sha256_text("\n".join(scenario_shas))
    run_json = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "batch_id": out_dir.name,
        "command": [sys.executable] + (sys.argv if argv is None else list(argv)),
        "cwd": str(REPO_ROOT),
        "host": platform.node(),
        "git": git_info(),
        "model": {
            "path": model_rel,
            "sha256": model_sha,
            "rendered_sha256": sha256_text(model_text),
            "structure_only": True,
        },
        "machine": params_document["machine"],
        "params": {
            "path": rel_to_repo(rendered["params_path"]),
            "sha256": sha256_file(rendered["params_path"]),
            "config_id": params_document["config_id"],
            "missing": params_io.missing_ids(params_document),
        },
        "config": {
            "path": ",".join(config_list),
            "sha256": combined_config_sha,
            "sha256_scope": "按 --cases 顺序对 'path:sha256' 连接串取 sha256",
            "items": [
                {
                    "path": rel_to_repo(path),
                    "sha256": sha256_file(path),
                }
                for path in config_paths
            ],
        },
        "scenario_xml_sha256": combined_scenario_sha,
        "scenario_xml_sha256_scope": "按 --cases 顺序对每个 case 注入后 XML 的 sha256 连接串再取 sha256；逐 case 值见 cases[]",
        "com_offset_B_m": {
            "x": MODEL_CONSTANTS["com_offset_B_m"][0],
            "y": MODEL_CONSTANTS["com_offset_B_m"][1],
            "z": MODEL_CONSTANTS["com_offset_B_m"][2],
        },
        "frame": {
            "cad_to_B": {
                "yaw_deg": float(ledger["frame.cad_to_B.yaw_deg"]["value"]),
                "origin_B_m": {
                    "x": float(ledger["frame.cad_to_B.origin_x_m"]["value"]),
                    "y": float(ledger["frame.cad_to_B.origin_y_m"]["value"]),
                    "z": float(ledger["frame.cad_to_B.origin_z_m"]["value"]),
                },
            }
        },
        "python": sys.version.split()[0],
        "mujoco": mujoco.__version__,
        "numpy": np.__version__,
        "os": os.name,
        "platform": platform.platform(),
        "numerics": {
            "timestep_s": float(configs[0]["numerics"]["timestep_s"]),
            "integrator": configs[0]["numerics"]["integrator"],
            "solver": configs[0]["numerics"]["solver"],
            "cone": configs[0]["numerics"]["cone"],
            "iterations": configs[0]["numerics"]["iterations"],
            "effective": effective_numerics[0],
            "per_case": [
                {"case_id": config["case_id"], **config["numerics"]} for config in configs
            ],
        },
        "overrides": dedupe_overrides(run_overrides),
        "seed": configs[0]["seed"],
        "seed_used": False,
        "params": [
            {"id": param_id, "label": row["label"], "verified_by": row["verified_by"]}
            for param_id, row in sorted(ledger.items())
        ],
        "param_labels": label_counts(labels),
        "conclusion_level_inputs": {
            "rule": "v1.7.6：只取绑定 xpath 的台账行；v1.7.4：本字段是结论等级，参数等级见 params[].label",
            "rows_bound_to_xpath": len(labels),
        },
        "conclusion_level": levels,
        "repeat": {
            "consistent": consistent,
            "key_metrics_tol": defaults["repeat"]["key_metrics_tol"],
        },
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "cases": case_entries,
        "columns": all_columns,
        "data_quality": {
            "contact_force_readout": "mj_contactForce",
            "missing_representation": "empty_field",
            "condim_quoted": 3,
            "rolling_resistance": "not_modelled(condim=3)",
            "torque_axis": "wheel_end_-y_forward_positive",
            "frame": "B=world=chassis_local",
        },
    }
    validate_run_json(run_json)
    (out_dir / "run.json").write_text(
        json.dumps(run_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_summary(out_dir / "summary.csv", summary_rows, configs[0], model_sha, combined_config_sha, levels)
    (out_dir / "stdout.log").write_text(
        "\n".join(
            [
                f"batch {out_dir.name}",
                f"contract {CONTRACT_VERSION}",
                f"git {git_info()}",
                f"model {model_rel} {model_sha}",
                f"configs {config_list} {combined_config_sha}",
                f"scenario_xml_sha256 {combined_scenario_sha}",
                f"repeat_consistent {consistent}",
                f"conclusion_level {levels}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    mismatches = [
        entry["case_id"]
        for entry in case_entries
        if entry["regression"].get("checked") and not entry["regression"].get("matched")
    ]
    if mismatches:
        print(f"回归断言不符：{mismatches}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        print(f"CONTRACT ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
