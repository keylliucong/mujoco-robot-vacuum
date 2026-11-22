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

CONTRACT_VERSION = "1.8.3"  # S14：等于契约文档版本；G2.5 另加 belly_contact 扩展
SCHEMA_VERSION = "1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge  # noqa: E402
import model_checks  # noqa: E402
import params_io  # noqa: E402

LEDGER_PATH = REPO_ROOT / "docs" / "参数溯源.csv"
RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner.json"

FAILURE_ENUM = {
    "topple",
    "belly_contact",
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

PAIR_GEOMS = {
    "wheel_L": ("wheel_L_tire",),
    "wheel_R": ("wheel_R_tire",),
    # G2.5：壳体前下缘是独立的 chassis_* geom；放进同一对名，pair 仍按
    # chassis--step / chassis--floor 取名，摩擦不从 geom 继承（S24）。
    "chassis": ("chassis_shell", "chassis_front_lip"),
    "caster": ("caster_wheel",),
    "floor": ("floor_plane",),
    "step": ("step", "step_edge"),
}

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


def batch_fingerprint(items):
    """v1.8.2 批次指纹：按 case_id 字典序排序后连接 `case_id:sha256` 再哈希。

    单 case 批次与该项自身的 sha256 相同；多 case 批次不依赖传入顺序。
    """
    ordered = sorted(items, key=lambda item: item[0])
    return sha256_text("\n".join(f"{case_id}:{sha}" for case_id, sha in ordered))


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
        if len(spec["friction"]) not in (4, 5):
            raise ContractError(
                f"{key}.friction 必须写满 pair 的 5 分量 [slide1 slide2 spin roll1 roll2]，"
                "或沿用旧的 4 值 [μ_s, μ_t, μ_r, μ_roll]（runner 把末项补成第 5 项）"
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
    a, _, b = key.partition("--")
    names_a = list(PAIR_GEOMS[a])
    names_b = list(PAIR_GEOMS[b])
    if obstacle_shape != "step":
        names_b = [n for n in names_b if not n.startswith("step")]
    return names_a, names_b


def contact_pair_attrs(params_document):
    def value(param_id):
        return params_io.get_param(params_document, param_id)[1]["value"]

    solref = "{} {}".format(
        params_io.format_number(value("contact.solref_timeconst_s")),
        params_io.format_number(value("contact.solref_dampratio")),
    )
    solimp = " ".join(
        params_io.format_number(value(f"contact.solimp_d{i}")) for i in range(5)
    )
    return {"solref": solref, "solimp": solimp}


def front_lip_pair_attrs(params_document):
    """前下缘 pair 的 solref/solimp。

    ``front_lip.compliance=0``（rigid）时与模型默认接触参数一致；
    ``=1``（soft）时用 ``front_lip.solref/solimp``，使 rigid/soft 的差异只来自
    前缘接触参数，而不是整个模型的接触刚度。
    """
    values = params_document["params"]
    compliance = values.get("front_lip.compliance", {}).get("value", 0.0)
    if float(compliance) < 0.5:  # contract-tolerance
        return contact_pair_attrs(params_document)
    keys = ("front_lip.solref_timeconst_s", "front_lip.solref_dampratio") + tuple(
        f"front_lip.solimp_d{i}" for i in range(5)
    )
    if not all(key in values for key in keys):
        return contact_pair_attrs(params_document)
    solref = "{} {}".format(
        params_io.format_number(values["front_lip.solref_timeconst_s"]["value"]),
        params_io.format_number(values["front_lip.solref_dampratio"]["value"]),
    )
    solimp = " ".join(
        params_io.format_number(values[f"front_lip.solimp_d{i}"]["value"]) for i in range(5)
    )
    return {"solref": solref, "solimp": solimp}


def check_front_lip_derived(params_document):
    """前缘派生量一致性：height/radius/overhang 是主参数，center_*/geom_radius 是派生。"""
    values = params_document["params"]
    required = (
        "front_lip.height_m",
        "front_lip.radius_m",
        "front_lip.overhang_m",
        "front_lip.geom_radius_m",
        "front_lip.center_x_m",
        "front_lip.center_z_m",
    )
    if not all(key in values for key in required):
        return False
    height = float(values["front_lip.height_m"]["value"])
    radius = float(values["front_lip.radius_m"]["value"])
    overhang = float(values["front_lip.overhang_m"]["value"])
    geom_radius = float(values["front_lip.geom_radius_m"]["value"])
    center_x = float(values["front_lip.center_x_m"]["value"])
    center_z = float(values["front_lip.center_z_m"]["value"])
    tolerance = 1e-9  # contract-tolerance
    min_radius = 0.0002  # contract-tolerance
    if abs(geom_radius - max(radius, min_radius)) > tolerance:
        raise ContractError(
            f"front_lip.geom_radius_m={geom_radius} != max(radius,0.2mm)={max(radius, min_radius)}"
        )
    if abs(center_x - overhang) > tolerance:
        raise ContractError(f"front_lip.center_x_m={center_x} != overhang={overhang}")
    if abs(center_z - (height + geom_radius)) > tolerance:
        raise ContractError(
            f"front_lip.center_z_m={center_z} != height+geom_radius={height + geom_radius}"
        )
    return True


def build_scenario_xml(model_text, config, chassis_front_m, defaults, params_document):
    root = ET.fromstring(model_text)
    kind = config["scenario"]["kind"]
    if kind == "step":
        obstacle = config["scenario"]["obstacle"]
        half_width = defaults["obstacle_half_width_m"]
        height = obstacle["height_m"]
        radius = obstacle["edge_radius_m"]
        width = obstacle["top_width_m"]
        heading = math.radians(config["scenario"]["heading_deg"])
        x_edge = chassis_front_m + config["scenario"]["approach"]["start_distance_m"]
        worldbody = root.find("worldbody")
        if worldbody is None:
            raise ContractError("模型缺 worldbody")
        quat = f"{math.cos(heading / 2.0)} 0 0 {math.sin(heading / 2.0)}"  # arithmetic
        body = ET.SubElement(
            worldbody, "body", {"name": "obstacle", "pos": f"{x_edge} 0 0", "quat": quat}
        )
        if obstacle["shape"] == "box":
            box_h = height - radius
            if box_h <= 0:
                raise ContractError("edge_radius_m 必须小于 height_m")
            ET.SubElement(
                body,
                "geom",
                {
                    "name": "step",
                    "type": "box",
                    "size": f"{width / 2.0} {half_width} {box_h / 2.0}",  # arithmetic
                    "pos": f"{width / 2.0} 0 {box_h / 2.0}",  # arithmetic
                    "material": "step",
                },
            )
            if radius > 0:
                ET.SubElement(
                    body,
                    "geom",
                    {
                        "name": "step_edge",
                        "type": "cylinder",
                        "size": f"{radius} {half_width}",
                        "pos": f"{radius} 0 {height - radius}",
                        "quat": "0.7071067811865476 0.7071067811865476 0 0",
                        "material": "step",
                    },
                )
        else:
            ET.SubElement(
                body,
                "geom",
                {
                    "name": "step",
                    "type": "cylinder",
                    "size": f"{height / 2.0} {half_width}",  # arithmetic
                    "pos": f"{height / 2.0} 0 {height / 2.0}",  # arithmetic
                    "quat": "0.7071067811865476 0.7071067811865476 0 0",
                    "material": "step",
                },
            )

    geom_names = {geom.get("name") for geom in root.iter("geom")}
    pair_elements = []
    for key, spec in config["environment"]["pairs"].items():
        names_a, names_b = pair_geom_names(key, kind)
        if not any(name in geom_names for name in names_a):
            raise ContractError(f"接触对 {key} 的侧 {names_a} 在模型里不存在")
        for name_a in names_a:
            for name_b in names_b:
                if name_a not in geom_names or name_b not in geom_names:
                    continue
                friction = list(spec["friction"])
                if len(friction) == 4:
                    # 旧 4 值写法：末项补成第 5 项（roll2）；新 case 建议直接写 5 值。
                    friction.append(friction[-1])
                attrs = {
                    "geom1": name_a,
                    "geom2": name_b,
                    "condim": str(spec["condim"]),
                    "friction": " ".join(str(v) for v in friction),
                }
                if name_a.startswith("chassis_front_lip") or name_b.startswith(
                    "chassis_front_lip"
                ):
                    attrs.update(front_lip_pair_attrs(params_document))
                else:
                    attrs.update(contact_pair_attrs(params_document))
                pair_elements.append(attrs)
    if pair_elements:
        contact = root.find("contact")
        if contact is None:
            contact = ET.SubElement(root, "contact")
        for attrs in pair_elements:
            ET.SubElement(contact, "pair", attrs)
    return ET.tostring(root, encoding="unicode")


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


PAIR_FRICTION_IDS = {
    ("wheel", "floor"): "contact.wheel_floor_friction_s",
    ("wheel", "step"): "contact.wheel_step_friction_s",
    ("chassis", "floor"): "contact.chassis_floor_friction_s",
    ("chassis", "step"): "contact.chassis_step_friction_s",
}


def pair_mu_id(key):
    side_a, _, side_b = key.partition("--")
    kind_a = "wheel" if side_a.startswith("wheel") else side_a
    kind_b = "step" if side_b.startswith("step") else "floor"
    try:
        return PAIR_FRICTION_IDS[(kind_a, kind_b)]
    except KeyError:
        raise ContractError(f"接触对 {key} 没有对应的台账摩擦行") from None


def config_friction_from_ledger(config, ledger):
    """配置里的接触对 μ 必须与台账一致（判据的 μ 只从台账取，不在代码里写死）。"""
    effective = {}
    for key, spec in config["environment"]["pairs"].items():
        expected = model_checks.ledger_value(ledger, pair_mu_id(key))
        actual = float(spec["friction"][0])
        if abs(actual - expected) > 1e-12:  # arithmetic
            raise ContractError(
                f"case 的 {key}.friction[0]={actual} 与台账 {pair_mu_id(key)}={expected} 不一致"
            )
        effective[key] = expected
    return effective


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


def friction_expectations(config, obstacle_shape):
    """S24：把每个 case 的 pair 摩擦解析成 {(geom1, geom2): spec}。"""
    expected = {}
    for key, spec in config["environment"]["pairs"].items():
        names_a, names_b = pair_geom_names(key, obstacle_shape)
        friction = list(spec["friction"])
        if len(friction) == 4:
            friction.append(friction[-1])
        for name_a in names_a:
            for name_b in names_b:
                expected[frozenset((name_a, name_b))] = {
                    "condim": int(spec["condim"]),
                    "friction": [float(v) for v in friction],
                }
    return expected


def check_s24_contact(contact, spec, pair_label):
    """S24 三条断言，真值只读 data.contact[i].friction（v1.8.3）。"""
    if int(contact.dim) != spec["condim"]:
        raise ContractError(
            f"S24 {pair_label}: contact.dim={int(contact.dim)} != 期望 condim={spec['condim']}"
        )
    friction = np.asarray(contact.friction, dtype=float).reshape(-1)
    if friction.size < 2 or abs(float(friction[0]) - float(friction[1])) > 1e-12:  # contract-tolerance
        raise ContractError(
            f"S24 {pair_label}: contact.friction[0]={friction[0]!r} != [1]={friction[1]!r}"
            "（各向同性；常见原因：把 geom 的 3 分量写法抄进 5 分量的 pair）"
        )
    if abs(float(friction[0]) - spec["friction"][0]) > 1e-9:  # contract-tolerance
        raise ContractError(
            f"S24 {pair_label}: contact.friction[0]={friction[0]!r} != pair slide1={spec['friction'][0]!r}"
        )


def sample_row(
    model, data, pair_lookup, ordered_pairs, geom_names, has_suspension, friction_specs=None, readback=None
):
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
    # 轴 +y、右手系：前进 +x 对应 +qvel（契约 §1.1 的负号与该轴定义不自洽，
    # 本实现按契约意图「前进为正」输出 +qvel / +actuator_force，差异已记入运行记录）
    spin_l = float(np.asarray(data.joint("wheel_L_spin").qvel).reshape(-1)[0])
    spin_r = float(np.asarray(data.joint("wheel_R_spin").qvel).reshape(-1)[0])
    row["wheel_L_speed_radps"] = spin_l
    row["wheel_R_speed_radps"] = spin_r
    row["wheel_L_torque_nm"] = float(np.asarray(data.actuator("wheel_L").force).reshape(-1)[0])
    row["wheel_R_torque_nm"] = float(np.asarray(data.actuator("wheel_R").force).reshape(-1)[0])
    if has_suspension:
        row["susp_L_travel_m"] = float(np.asarray(data.joint("susp_L").qpos).reshape(-1)[0])
        row["susp_R_travel_m"] = float(np.asarray(data.joint("susp_R").qpos).reshape(-1)[0])
    else:
        # v1.8.0 §1.2：没有该自由度时整列为空，不是 0
        row["susp_L_travel_m"] = None
        row["susp_R_travel_m"] = None

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
        if friction_specs is not None:
            spec = friction_specs.get(frozenset((name1, name2)))
            if spec is not None:
                check_s24_contact(contact, spec, f"{name1}--{name2}")
                if readback is not None:
                    readback[key] = [float(v) for v in contact.friction]
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


def set_drive(model, data, limits, kp, speed_cmd, ramp, yaw_damping):
    """机体速度闭环 + 偏航率阻尼。

    轮速伺服在台阶棱边会因轮子空转而卸扭，v1 用机体速度（稳态等价于轮心速度）。
    左右轮先后触台阶会产生偏航力矩；加偏航率阻尼模拟差速底盘的航向保持，
    k_yaw 为轮端差动扭矩增益（N·m·s/rad）。
    """
    target = speed_cmd * ramp
    qvel = np.asarray(data.joint("chassis_free").qvel, dtype=float)
    vx = float(qvel[0])
    wz = float(qvel[5])
    torque = kp * (target - vx)
    diff = yaw_damping * wz
    for name, sign in (("wheel_L", 1.0), ("wheel_R", -1.0)):
        limit = limits[name]
        value = torque + sign * diff / 2
        data.actuator(name).ctrl[:] = max(-limit, min(limit, value))


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


def run_case(model, data, config, defaults, limits, ordered_pairs, pair_lookup, geom_names, radius, has_suspension, friction_specs=None):
    approach = config["scenario"]["approach"]
    speed = approach["speed_mps"]
    window = config["judge"]["window_s"]
    step = float(model.opt.timestep)
    kp = defaults["drive"]["speed_kp_nm_per_mps"]
    yaw_damping = defaults["drive"]["yaw_damping_nm_per_radps"]
    reset_state(model, data)
    columns = make_columns(ordered_pairs)
    rows = []
    step_pairs = [k for k in ordered_pairs if k.endswith("--step")]
    friction_readback = {}
    trigger_time = 0.0 if config["scenario"]["kind"] == "flat" else None
    trigger_source = "flat" if config["scenario"]["kind"] == "flat" else ""
    cap_time = (
        approach["settle_s"]
        + approach["start_distance_m"] / speed
        + defaults["time"]["approach_margin_s"]
        + window
    )
    max_steps = int(round(defaults["time"]["max_sim_s"] / step))
    ramp_s = approach["settle_s"]
    for _ in range(max_steps):
        ramp = min(1.0, float(data.time) / ramp_s)
        set_drive(model, data, limits, kp, speed, ramp, yaw_damping)
        step_once(model, data)
        row = sample_row(
            model,
            data,
            pair_lookup,
            ordered_pairs,
            geom_names,
            has_suspension,
            friction_specs,
            friction_readback,
        )
        rows.append(row)
        if trigger_time is None:
            # v1.8.2：首次任一机体-台阶接触（轮或底盘），不再只认轮
            for key in step_pairs:
                if row[f"contact_{key}_active"] == 1:
                    trigger_time = row["t_s"]
                    trigger_source = key
                    break
        if trigger_time is not None and row["t_s"] >= trigger_time + window:
            break
        if trigger_time is None and row["t_s"] >= cap_time:
            break
    warning_numbers = [int(value) for value in np.asarray(data.warning.number)]
    return (
        {name: [row[name] for row in rows] for name in columns},
        columns,
        warning_numbers,
        {
            "trigger_source": trigger_source,
            "friction_readback": {
                key: value for key, value in sorted(friction_readback.items())
            },
        },
    )


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


def column_metadata(columns, has_suspension=True):
    meta = {}
    for column in columns:
        missing = column.endswith("_normal_n") or column.endswith("_tangent_n")
        if not has_suspension and column.endswith("_travel_m"):
            missing = True
        meta[column] = {"unit": unit_for(column), "missing": missing}
    return meta


def build_judge_params(
    config,
    defaults,
    model,
    limits,
    ordered_pairs,
    body_length_m,
    radius,
    has_suspension,
    pair_friction,
    platform_height_tol_m,
    step_front_m,
):
    approach = config["scenario"]["approach"]
    judge_cfg = config["judge"]
    kind = config["scenario"]["kind"]
    obstacle = config["scenario"]["obstacle"] if kind == "step" else {"height_m": 0.0, "top_width_m": 0.0}
    height = obstacle["height_m"]
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
        "platform_height_tol_m": platform_height_tol_m,
        "step_front_m": step_front_m,
        "step_half_width_m": obstacle["top_width_m"] / 2.0,  # arithmetic
        "heading_rad": math.radians(config["scenario"]["heading_deg"]),
        "com_offset_x_m": MODEL_CONSTANTS["com_offset_B_m"][0],
        "contact_gap_tol_s": defaults["tolerances"]["step_contact_gap_tol_s"],
        "has_suspension": bool(has_suspension),
        "susp_range_m": MODEL_CONSTANTS["susp_range_m"] if has_suspension else 0.0,
        "susp_bottom_rel": defaults["tolerances"]["susp_bottom_rel"],
        "torque_limit_L_nm": limits["wheel_L"],
        "torque_limit_R_nm": limits["wheel_R"],
        "torque_saturation_rel": defaults["tolerances"]["torque_saturation_rel"],
        "slip_eps_mps": defaults["tolerances"]["slip_eps_mps"],
        "climb_height_ratio": defaults["tolerances"]["climb_height_ratio"],
        "climb_hold_s": defaults["tolerances"]["climb_hold_s"],
        "pair_friction": {
            key: float(pair_friction[key]) for key in ordered_pairs
        },
        "wheel_step_pairs": [
            k for k in ordered_pairs if k.startswith("wheel_") and k.endswith("--step")
        ],
        "bottom_out_pairs": [k for k in ordered_pairs if k.startswith("chassis--")],
        "all_pairs": list(ordered_pairs),
    }


MODEL_CONSTANTS = {"wheel_radius_m": 0.0, "susp_range_m": 0.0, "com_offset_B_m": (0.0, 0.0, 0.0)}


def load_ledger_rows(machine):
    ledger = model_checks.load_ledger(LEDGER_PATH, machine=machine)
    # v1.7.6：结论等级只取绑定了 xpath 的行（真正进入模型/判定的那些）
    bound = {
        param_id: row["label"]
        for param_id, row in dict.items(ledger)
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


def path_for_report(path):
    try:
        return str(path.relative_to(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        return str(path).replace(os.sep, "/")


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
                    config_sha,
                    level,
                    row["output_dir"],
                ]
            )


def summary_signature(row):
    """summary.csv 一行的逐位签名：排除 repeat / output_dir（v1.8.2）。"""
    signature = []
    for column in SUMMARY_COLUMNS:
        if column in ("repeat", "output_dir"):
            continue
        if column in SUMMARY_METRIC_KEYS:
            value = row["metrics"][column]
        else:
            value = row[column]
        signature.append((column, "" if value is None else str(value)))
    return signature


def check_consistency(out_dir, repeat_results):
    if len(repeat_results) < 2:
        return True
    digests = set()
    summary = set()
    for item in repeat_results:
        digests.add(sha256_file(out_dir / item["output_dir"] / "timeseries.csv"))
        summary.add(tuple(item["summary_signature"]))
    return len(digests) == 1 and len(summary) == 1


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


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="G2 批运行入口")
    parser.add_argument("--config", required=True, help="单次运行的 case JSON")
    parser.add_argument("--out", required=True, help="批次输出目录")
    parser.add_argument("--repeat", type=int, default=1, help="同配置重复次数")
    parser.add_argument(
        "--params",
        default=None,
        help="覆盖参数集路径（默认取模型头 parameter_source）；用于同一模型扫多套参数",
    )
    parser.add_argument(
        "--tiers",
        default="",
        help="附加时步档（秒，逗号分隔），例如 0.001,0.0005；与 base 同批同报",
    )
    args = parser.parse_args(argv)

    if args.repeat < 1:
        raise ContractError("--repeat 必须 >= 1")
    extra_tiers = []
    for token in args.tiers.split(","):
        token = token.strip()
        if token:
            value = float(token)
            if value <= 0:
                raise ContractError("--tiers 的时步必须 > 0")
            extra_tiers.append(value)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    if out_dir.exists():
        raise ContractError(f"批次目录已存在，拒绝覆盖（S12）：{out_dir}")

    started = datetime.now(timezone.utc).isoformat()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    config = load_case(config_path)
    defaults = load_runner_defaults()
    config_sha = sha256_file(config_path)

    model_rel = config["model"]["path"]
    model_path = (REPO_ROOT / model_rel).resolve()
    model_sha = sha256_file(model_path)
    if model_sha != config["model"]["sha256"]:
        raise ContractError(f"模型 sha256 与配置不符：{model_sha} != {config['model']['sha256']}")

    rendered = params_io.load_and_render(model_path, args.params)
    params_document = rendered["params"]
    check_front_lip_derived(params_document)
    model_text = rendered["text"]

    ledger, labels = load_ledger_rows(params_document["machine"])
    radius = model_checks.ledger_value(ledger, "geom.wheel_radius_m")
    MODEL_CONSTANTS["wheel_radius_m"] = radius
    MODEL_CONSTANTS["susp_range_m"] = model_checks.ledger_value(ledger, "susp.travel_limit_m")
    MODEL_CONSTANTS["com_offset_B_m"] = model_checks.declared_com_offset(ledger)
    platform_tol = model_checks.ledger_value(ledger, "judge.platform_height_tol_m")
    pair_friction = config_friction_from_ledger(config, ledger)

    config_id = parse_config_id(config)
    if params_document["config_id"] != config_id:
        raise ContractError(
            f"case 的 config_id={config_id} 与参数集 {params_document['config_id']} 不一致（v1.4/S21）"
        )
    base_model = mujoco.MjModel.from_xml_string(model_text)
    base_data = mujoco.MjData(base_model)
    mujoco.mj_forward(base_model, base_data)
    model_root = ET.fromstring(model_text)
    model_checks.run_checks(base_model, base_data, ledger, model_root=model_root)
    has_suspension = model_checks.read_capability(base_model, "has_suspension")
    body_length_m = model_checks.body_length(base_model)
    chassis_front_m = chassis_front(base_model)
    stage = config["scenario"]
    step_front_m = (
        chassis_front_m + stage["approach"]["start_distance_m"]
        if stage["kind"] == "step"
        else 0.0
    )

    scenario_xml = build_scenario_xml(
        model_text, config, chassis_front_m, defaults, params_document
    )
    scenario_sha = sha256_text(scenario_xml)
    out_dir.mkdir(parents=True)

    print(f"batch_id: {out_dir.name}")
    print(f"contract_version: {CONTRACT_VERSION}")
    print(f"model: {model_rel} sha256={model_sha}")
    print(f"params: {params_document['config_id']} machine={params_document['machine']} missing={params_io.missing_ids(params_document)}")
    print(f"capabilities: has_suspension={has_suspension}")
    print(f"config: {config_path} sha256={config_sha}")
    print(f"scenario_xml_sha256: {scenario_sha}")
    print(f"git: {git_info()}")

    repeat_results = []
    summary_rows = []
    run_overrides = []
    effective_numerics = None
    actual_columns = None
    for repeat in range(1, args.repeat + 1):
        case_name = config["case_id"] if args.repeat == 1 else f"{config['case_id']}_r{repeat}"
        case_dir = out_dir / case_name
        case_dir.mkdir(parents=True)
        (case_dir / "scenario.xml").write_text(scenario_xml, encoding="utf-8")

        model = mujoco.MjModel.from_xml_string(scenario_xml)
        numerics = apply_numerics(
            model, config["numerics"], config["numerics"]["timestep_s"], run_overrides
        )
        effective_numerics = numerics
        limits = apply_torque_limits(model, config, run_overrides)
        data = mujoco.MjData(model)
        pair_lookup, ordered_pairs = build_pair_lookup(config, config["scenario"]["kind"])
        geom_names = geom_name_table(model)
        friction_specs = friction_expectations(config, config["scenario"]["kind"])
        actual_columns = make_columns(ordered_pairs)

        creep = run_creep(model, data, defaults, radius)
        print(
            f"[{config['case_id']} r{repeat}] creep: drift={creep['drift_m'] * 1000:.4f} mm "
            f"residual={creep['residual_speed_mps'] * 1000:.4f} mm/s redline={creep['redline']}"
        )

        tiers = [("base", float(config["numerics"]["timestep_s"]))]
        if creep["redline"]:
            tiers += [
                (f"downgrade_{t * 1000:g}ms", float(t))
                for t in defaults["creep"]["downgrade_tiers_s"]
            ]
        for value in extra_tiers:
            tiers.append((f"tier_{value * 1000:g}ms", float(value)))

        seen_tiers = set()
        tier_results = []
        for tier_name, tier_step in tiers:
            if tier_step in seen_tiers:
                continue
            seen_tiers.add(tier_step)
            if tier_step == float(config["numerics"]["timestep_s"]):
                tier_model, tier_data, tier_limits = model, data, limits
            else:
                tier_model = mujoco.MjModel.from_xml_string(scenario_xml)
                apply_numerics(tier_model, config["numerics"], tier_step, run_overrides)
                tier_limits = apply_torque_limits(tier_model, config, run_overrides)
                tier_data = mujoco.MjData(tier_model)
            tier_dir = case_dir if tier_name == "base" else case_dir / tier_name
            tier_dir.mkdir(parents=True, exist_ok=True)
            table, columns, warnings, run_meta = run_case(
                tier_model,
                tier_data,
                config,
                defaults,
                tier_limits,
                ordered_pairs,
                pair_lookup,
                geom_names,
                radius,
                has_suspension,
                friction_specs,
            )
            write_timeseries(tier_dir / "timeseries.csv", columns, table)
            judge_table = {
                column: [format_value(value) for value in table[column]] for column in columns
            }
            params = build_judge_params(
                config,
                defaults,
                tier_model,
                tier_limits,
                ordered_pairs,
                body_length_m,
                radius,
                has_suspension,
                pair_friction,
                platform_tol,
                step_front_m,
            )
            verdict = judge.judge_case(judge_table, params)
            verdict["timestep_s"] = float(tier_model.opt.timestep)
            verdict["warnings"] = {
                "numbers": warnings,
                "nonzero": sum(1 for value in warnings if value != 0),
            }
            tier_results.append(
                {
                    "tier": tier_name,
                    "timestep_s": float(tier_model.opt.timestep),
                    "verdict": verdict,
                    "dir": str(tier_dir.relative_to(out_dir)).replace(os.sep, "/"),
                    "trigger_source": run_meta["trigger_source"],
                    "friction_readback": run_meta["friction_readback"],
                }
            )
            print(
                f"[{config['case_id']} r{repeat} {tier_name}] status={verdict['status']} "
                f"passed={verdict['passed']} primary={verdict['failure_primary']} "
                f"flags={';'.join(verdict['failure_flags'])}"
            )

        base = tier_results[0]["verdict"]
        summary_rows.append(
            {
                "case_id": config["case_id"],
                "repeat": repeat,
                "status": base["status"],
                "passed": "" if base["passed"] is None else int(base["passed"]),
                "failure_primary": base["failure_primary"],
                "failure_flags": ";".join(base["failure_flags"]),
                "metrics": base["metrics"],
                "timestep_s": float(config["numerics"]["timestep_s"]),
                "integrator": config["numerics"]["integrator"],
                "cone": config["numerics"]["cone"],
                "seed": config["seed"],
                "model_sha256": model_sha,
                "config_sha256": config_sha,
                "conclusion_level": conclusion_level(labels),
                "output_dir": path_for_report(case_dir),
            }
        )
        repeat_results.append(
            {
                "repeat": repeat,
                "output_dir": case_name,
                "creep": creep,
                "summary_signature": summary_signature(summary_rows[-1]),
                "tiers": [
                    {
                        "tier": item["tier"],
                        "timestep_s": item["timestep_s"],
                        "dir": item["dir"],
                        "trigger_source": item["trigger_source"],
                        "friction_readback": item["friction_readback"],
                        "verdict": item["verdict"],
                    }
                    for item in tier_results
                ],
            }
        )

    consistent = check_consistency(out_dir, repeat_results)
    regression = check_regression(config, repeat_results)
    level = conclusion_level(labels)
    config_cases = [
        {"case_id": config["case_id"], "path": path_for_report(config_path), "sha256": config_sha}
    ]
    scenario_cases = [{"case_id": config["case_id"], "sha256": scenario_sha}]
    config_fingerprint = batch_fingerprint(
        [(item["case_id"], item["sha256"]) for item in config_cases]
    )
    scenario_fingerprint = batch_fingerprint(
        [(item["case_id"], item["sha256"]) for item in scenario_cases]
    )
    base_tier = repeat_results[0]["tiers"][0]

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
        "capabilities": {"has_suspension": has_suspension},
        "parameter_set": {
            "path": path_for_report(rendered["params_path"]),
            "sha256": sha256_file(rendered["params_path"]),
            "config_id": params_document["config_id"],
            "missing": params_io.missing_ids(params_document),
        },
        "config": {
            "path": sorted(item["path"] for item in config_cases),
            "sha256": config_fingerprint,
            "cases": config_cases,
        },
        "scenario_xml_sha256": scenario_fingerprint,
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
            "timestep_s": float(config["numerics"]["timestep_s"]),
            "integrator": config["numerics"]["integrator"],
            "solver": config["numerics"]["solver"],
            "cone": config["numerics"]["cone"],
            "iterations": config["numerics"]["iterations"],
            "effective": effective_numerics,
        },
        "overrides": dedupe_overrides(run_overrides),
        "seed": config["seed"],
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
        "conclusion_level": level,
        "repeat": {
            "consistent": consistent,
            "key_metrics_tol": defaults["repeat"]["key_metrics_tol"],
            "excluded_columns": ["repeat", "output_dir"],
        },
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "cases": [
            {
                "case_id": config["case_id"],
                "config": path_for_report(config_path),
                "config_sha256": config_sha,
                "scenario_xml_sha256": scenario_sha,
                "trigger_source": base_tier["trigger_source"],
                "friction_readback": base_tier["friction_readback"],
                "repeats": repeat_results,
                "regression": regression,
            }
        ],
        "columns": column_metadata(actual_columns, has_suspension),
        "data_quality": {
            "contact_force_readout": "mj_contactForce",
            "missing_representation": "empty_field",
            "condim_quoted": 3,
            "rolling_resistance": "not_modelled(condim=3)",
            "torque_axis": "wheel_end_-y_forward_positive",
            "frame": "B=world=chassis_local",
            "bottoming": {
                "criterion": "contact_only(chassis--step active)；未实现最小间隙时程，chassis_min_z_m 不作间隙判据",
                "applicability_max_step_height_m": model_checks.chassis_min_z(
                    base_model, base_data
                ),
            },
            "pair_friction_readback": base_tier["friction_readback"],
            "warnings": {
                "numbers": sorted(
                    {
                        value
                        for item in repeat_results
                        for tier in item["tiers"]
                        for value in tier["verdict"]["warnings"]["numbers"]
                    }
                ),
                "nonzero": sum(
                    tier["verdict"]["warnings"]["nonzero"]
                    for item in repeat_results
                    for tier in item["tiers"]
                ),
                "batch_valid": all(
                    tier["verdict"]["warnings"]["nonzero"] == 0
                    for item in repeat_results
                    for tier in item["tiers"]
                ),
            },
        },
    }
    validate_run_json(run_json)
    (out_dir / "run.json").write_text(
        json.dumps(run_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_summary(out_dir / "summary.csv", summary_rows, config, model_sha, config_sha, level)
    (out_dir / "stdout.log").write_text(
        "\n".join(
            [
                f"batch {out_dir.name}",
                f"contract {CONTRACT_VERSION}",
                f"git {git_info()}",
                f"model {model_rel} {model_sha}",
                f"config {config_path} {config_sha}",
                f"scenario_xml_sha256 {scenario_sha}",
                f"repeat_consistent {consistent}",
                f"conclusion_level {level}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    if regression.get("checked") and not regression.get("matched"):
        print(
            f"回归断言不符：期望 {regression['expected']}，实际 {regression['actual']}",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, params_io.ParamError, model_checks.ModelCheckError, judge.JudgeError) as error:
        print(f"CONTRACT ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
