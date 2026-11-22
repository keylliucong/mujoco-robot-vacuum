"""G2 模型自检断言 A1–A5（契约 v1.7 §1.1、S16）。

A1 质量求和、A2 整机 CoM、A3 惯量平行轴搬移到 B 原点、A4 两轮心对称且 z=R、
A5 chassis 在 t=0 的 world 位姿为单位位姿。全部与 docs/参数溯源.csv 比对。
runner 启动时直接调用，verify_structure.py 用它跑「故意挪 20 mm / 2 mm」的报警测试。
"""

from __future__ import annotations

import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

# 契约 §1.1 表 A1–A5 明文容差（不是本项目的测量容差，不得改）
A1_REL_TOL = 0.01  # contract-tolerance A1
A2_ABS_TOL_M = 0.001  # contract-tolerance A2
A3_REL_TOL = 0.02  # contract-tolerance A3
A4_ABS_TOL_M = 0.001  # contract-tolerance A4
A3_ABS_TOL_ZERO = 1e-6  # contract-tolerance A3（对称积应为 0 的绝对门）

REQUIRED_NAMES = {
    "body": ["chassis", "wheel_L", "wheel_R"],
    "joint": ["wheel_L_spin", "wheel_R_spin", "susp_L", "susp_R"],
    "actuator": ["wheel_L", "wheel_R"],
    "material": ["floor", "step"],
}
REQUIRED_GEOM_PREFIXES = ("chassis_", "wheel_L_", "wheel_R_")


class ModelCheckError(AssertionError):
    """A1–A5 任一不过。"""


def load_ledger(path):
    rows = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = [
            "param_id",
            "xpath",
            "value",
            "unit",
            "label",
            "ref",
            "verified_by",
            "verified_delta",
            "verified_tol",
        ]
        if reader.fieldnames != expected:
            raise ModelCheckError(f"台账列不是契约 9 列：{reader.fieldnames}")
        for row in reader:
            rows[row["param_id"]] = row
    return rows


def ledger_value(ledger, param_id):
    if param_id not in ledger:
        raise ModelCheckError(f"台账缺行：{param_id}")
    return float(ledger[param_id]["value"])


def xml_attr(root, xpath):
    """解析 `模型:/a/b[@name='x']/c@attr` 形式的路径。"""
    if xpath.strip() in ("", "-"):
        raise ModelCheckError(f"台账行没有 XML 归宿：{xpath!r}")
    _, _, path = xpath.partition(":")
    parts = [p for p in path.split("/") if p]
    node = root
    for part in parts[:-1]:
        tag, _, predicate = part.partition("[")
        if predicate:
            name = predicate.split("'")[1]
            found = None
            for child in node.findall(tag):
                if child.get("name") == name:
                    found = child
                    break
            if found is None:
                raise ModelCheckError(f"XML 路径不存在：{xpath}")
            node = found
        else:
            node = node.find(tag)
            if node is None:
                raise ModelCheckError(f"XML 路径不存在：{xpath}")
    last = parts[-1]
    tag_part, _, attr_part = last.rpartition("@")
    if tag_part:
        tag, _, predicate = tag_part.partition("[")
        if predicate:
            name = predicate.split("'")[1]
            for child in node.findall(tag):
                if child.get("name") == name:
                    node = child
                    break
            else:
                raise ModelCheckError(f"XML 路径不存在：{xpath}")
        else:
            child = node.find(tag)
            if child is None:
                raise ModelCheckError(f"XML 路径不存在：{xpath}")
            node = child
    index = None
    if "[" in attr_part:
        attr_part, _, idx = attr_part.partition("[")
        index = int(idx.rstrip("]"))
    raw = node.get(attr_part)
    if raw is None:
        raise ModelCheckError(f"XML 属性不存在：{xpath}")
    values = raw.split()
    if index is not None:
        return float(values[index])
    if len(values) == 1:
        return float(values[0])
    raise ModelCheckError(f"多值属性请带下标：{xpath}")


def check_required_names(model):
    problems = []
    for kind, names in REQUIRED_NAMES.items():
        obj = getattr(model, kind)
        for name in names:
            try:
                obj(name)
            except KeyError:
                problems.append(f"缺 {kind} 名称：{name}")
    geom_names = [model.geom(i).name for i in range(model.ngeom)]
    for prefix in REQUIRED_GEOM_PREFIXES:
        if not any(n.startswith(prefix) for n in geom_names):
            problems.append(f"缺 geom 前缀：{prefix}")
    return problems


def body_metrics(model, data):
    masses = np.asarray(model.body_mass, dtype=float)
    total = float(masses.sum())
    com = np.zeros(3)
    for bid in range(model.nbody):
        if masses[bid] == 0.0:
            continue
        com += masses[bid] * np.asarray(data.xipos[bid], dtype=float)
    com /= total

    inertia = np.zeros((3, 3))
    for bid in range(model.nbody):
        mass = masses[bid]
        if mass == 0.0:
            continue
        # body_inertia 是主轴矩（MuJoCo 降序排列），配 body_iquat 才是 body 系张量；
        # 用 ximat（惯性主轴系在 world 的朝向）搬到 world，不能用 xmat。
        rot = np.asarray(data.ximat[bid], dtype=float).reshape(3, 3)
        diag = np.diag(np.asarray(model.body_inertia[bid], dtype=float))
        inertia += rot @ diag @ rot.T
        r = np.asarray(data.xipos[bid], dtype=float) - np.zeros(3)
        inertia += mass * (np.dot(r, r) * np.eye(3) - np.outer(r, r))
    return total, com, inertia


def evaluate(model, data, ledger, model_root=None):
    """返回 [(断言, 通过, 说明)]，不做 raise，方便负例测试。"""
    results = []
    total, com, inertia = body_metrics(model, data)

    expected_mass = ledger_value(ledger, "mass.assembly")
    rel = abs(total - expected_mass) / expected_mass
    results.append(("A1", rel <= A1_REL_TOL, f"质量 {total:.6f} vs 台账 {expected_mass:.6f}，相对偏差 {rel:.2e}"))

    expected_com = np.array(
        [
            ledger_value(ledger, "com_B_m.x"),
            ledger_value(ledger, "com_B_m.y"),
            ledger_value(ledger, "com_B_m.z"),
        ]
    )
    delta_com = float(np.linalg.norm(com - expected_com))
    results.append(
        (
            "A2",
            delta_com <= A2_ABS_TOL_M,
            f"CoM {np.round(com, 6)} vs 台账 {np.round(expected_com, 6)}，范数差 {delta_com * 1000:.3f} mm",
        )
    )

    diag_ok = True
    notes = []
    for axis, idx in (("xx", 0), ("yy", 1), ("zz", 2)):
        expected = ledger_value(ledger, f"inertia_B.{axis}")
        rel_i = abs(inertia[idx, idx] - expected) / expected
        diag_ok = diag_ok and rel_i <= A3_REL_TOL
        notes.append(f"{axis}={inertia[idx, idx]:.6f}/{expected:.6f}({rel_i:.2e})")
    zero_ok = True
    for (i, j, axis) in ((0, 1, "xy"), (0, 2, "xz"), (1, 2, "yz")):
        expected = ledger_value(ledger, f"inertia_B.{axis}")
        zero_ok = zero_ok and abs(inertia[i, j] - expected) <= A3_ABS_TOL_ZERO
    results.append(("A3", diag_ok and zero_ok, "惯量 " + "，".join(notes)))

    radius = ledger_value(ledger, "geom.wheel_radius_m")
    left = np.asarray(data.body("wheel_L").xpos, dtype=float)
    right = np.asarray(data.body("wheel_R").xpos, dtype=float)
    checks = {
        "x 对称": abs(left[0] - right[0]),
        "y 对称": abs(left[1] + right[1]),
        "轴心 x≈0": abs((left[0] + right[0]) * 0.5),  # arithmetic
        "z=R": max(abs(left[2] - radius), abs(right[2] - radius)),
        "左右共面": abs(left[2] - right[2]),
    }
    a4_ok = all(v <= A4_ABS_TOL_M for v in checks.values())
    results.append(
        ("A4", a4_ok, "；".join(f"{k}={v * 1000:.3f} mm" for k, v in checks.items()))
    )

    a5_ok = True
    a5_notes = []
    if model_root is not None:
        chassis = None
        for body in model_root.iter("body"):
            if body.get("name") == "chassis":
                chassis = body
                break
        if chassis is None:
            a5_ok = False
            a5_notes.append("XML 无 chassis body")
        else:
            pos = chassis.get("pos")
            quat = chassis.get("quat")
            if pos is None or [float(v) for v in pos.split()] != [0.0, 0.0, 0.0]:
                a5_ok = False
                a5_notes.append(f"chassis pos={pos!r}")
            if quat is None or [float(v) for v in quat.split()] != [1.0, 0.0, 0.0, 0.0]:
                a5_ok = False
                a5_notes.append(f"chassis quat={quat!r}")
    xpos = np.asarray(data.body("chassis").xpos, dtype=float)
    xquat = np.asarray(data.body("chassis").xquat, dtype=float)
    if np.linalg.norm(xpos) > 0.0 or np.linalg.norm(xquat - np.array([1.0, 0.0, 0.0, 0.0])) > 0.0:
        a5_ok = False
        a5_notes.append(f"t=0 位姿 xpos={np.round(xpos, 9)} xquat={np.round(xquat, 9)}")
    if not a5_notes:
        a5_notes.append("XML 与 t=0 位姿均为单位位姿")
    results.append(("A5", a5_ok, "；".join(a5_notes)))

    return results


def run_checks(model, data, ledger, model_root=None):
    problems = check_required_names(model)
    if model_root is not None:
        problems.extend(check_ledger_against_xml(model_root, ledger))
    results = evaluate(model, data, ledger, model_root=model_root)
    failed = [name for name, ok, _ in results if not ok]
    if problems or failed:
        detail = "；".join(problems + [f"{name} 失败" for name in failed])
        raise ModelCheckError(f"A1–A5、名称表或台账比对不过：{detail}")
    return results


def check_ledger_against_xml(root, ledger):
    """S10：台账里指向模型的每一行必须与渲染后的 XML 数值一致。"""
    problems = []
    for param_id, row in ledger.items():
        xpath = row["xpath"]
        if not xpath.startswith("models/"):
            continue
        try:
            value = xml_attr(root, xpath)
        except ModelCheckError as error:
            problems.append(f"{param_id}: {error}")
            continue
        expected = float(row["value"])
        scale = max(1.0, abs(expected))
        if abs(value - expected) > scale * 1e-9:  # arithmetic
            problems.append(
                f"{param_id}: XML {value!r} != 台账 {expected!r}（{xpath}）"
            )
    return problems


def load_and_check(model_text, ledger_path):
    root = ET.fromstring(model_text)
    model = mujoco.MjModel.from_xml_string(model_text)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    ledger = load_ledger(ledger_path)
    return model, data, root, run_checks(model, data, ledger, model_root=root)


def declared_com_offset(ledger):
    return (
        ledger_value(ledger, "com_B_m.x"),
        ledger_value(ledger, "com_B_m.y"),
        ledger_value(ledger, "com_B_m.z"),
    )


def body_length(model):
    """chassis_* 几何沿 x 的包围盒长度（判据用的车身长）。

    box: 2*half_x；cylinder（轴 +z）: 2*radius。两者都是 chassis_* 前缀，
    不允许用未带前缀的几何充数。
    """
    lengths = []
    for gid in range(model.ngeom):
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        size = model.geom_size[gid]
        if model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_BOX:
            lengths.append(2 * float(size[0]))
        elif model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_CYLINDER:
            lengths.append(2 * float(size[0]))
    if not lengths:
        raise ModelCheckError("chassis_* 中没有 box/cylinder 几何，无法取车身长")
    return max(lengths)


def chassis_min_z(model, data):
    """chassis_* 几何包围球下界（近似值，契约 §3）。"""
    lows = []
    for gid in range(model.ngeom):
        model.geom(gid)  # 名称必须存在，缺名即失败
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        center = np.asarray(data.geom_xpos[gid], dtype=float)
        lows.append(float(center[-1]) - float(model.geom_rbound[gid]))
    return min(lows)


def euler_zyx(quat):
    w, x, y, z = quat
    yaw = math.atan2(2 * (w * z + x * y), 1.0 - 2 * (y * y + z * z))  # arithmetic
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))  # arithmetic
    roll = math.atan2(2 * (w * x + y * z), 1.0 - 2 * (x * x + y * y))  # arithmetic
    return pitch, roll, yaw
