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

def read_capability(model, name):
    """读 MJCF <custom><numeric name="has_*">（契约 v1.8.0 §1.2）。"""
    nid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_NUMERIC, name)
    if nid < 0:
        raise ModelCheckError(
            f"模型缺少能力声明 <custom><numeric name=\"{name}\">（契约 v1.8.0 §1.2）"
        )
    data = np.asarray(model.numeric_data[nid], dtype=float).reshape(-1)
    if data.size < 1:
        raise ModelCheckError(f"能力声明 {name} 没有数值")
    value = float(data[0])
    if value not in (0.0, 1.0):
        raise ModelCheckError(f"能力声明 {name}={value}，只允许 0 或 1")
    return int(value)


def joint_travel(model, joint_name):
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if jid < 0:
        raise ModelCheckError(f"缺关节：{joint_name}")
    if model.jnt_limited[jid]:
        return float(model.jnt_range[jid][1] - model.jnt_range[jid][0])
    return float("inf")


def check_capabilities(model):
    """S22：声明与模型两端一致；有悬挂时行程必须 > 0（不得用 0/占位值蒙混）。"""
    problems = []
    has_suspension = read_capability(model, "has_suspension")
    joint_names = [model.joint(i).name for i in range(model.njnt)]
    actuator_names = [model.actuator(i).name for i in range(model.nu)]
    susp_joints = [n for n in joint_names if n.startswith("susp")]
    susp_actuators = [n for n in actuator_names if n.startswith("susp")]
    if has_suspension == 0:
        if susp_joints or susp_actuators:
            problems.append(
                f"has_suspension=0 但模型仍有悬挂关节/执行器：{susp_joints + susp_actuators}（S22）"
            )
    else:
        for name in ("susp_L", "susp_R"):
            if name not in joint_names:
                problems.append(f"has_suspension=1 但缺关节 {name}（S22）")
                continue
            travel = joint_travel(model, name)
            if travel <= 0.0:
                problems.append(f"{name} 行程 {travel} 不为正；不得用 0 行程假铰（S22/抽查 16）")
    return problems, has_suspension


def required_names(model):
    names = {kind: list(values) for kind, values in REQUIRED_NAMES.items()}
    if read_capability(model, "has_suspension") == 0:
        names["joint"] = [n for n in names["joint"] if not n.startswith("susp")]
    return names



class ModelCheckError(AssertionError):
    """A1–A5 任一不过。"""


class Ledger(dict):
    """台账行视图：param_id 在 v1.8.4 起为 `<machine>.<config_id>.<量名>`。

    脚本内部一律按裸量名（如 `mass.assembly`）取用；前缀解析只在读取层做一次，
    调用点不再重复拼前缀。裸 id 本身若存在则优先；否则依次试当前机型+配置、
    旧两段式机型前缀，最后只在后缀全局唯一时回退，避免把 other 机型/配置的
    同名行混进来。
    """

    def __init__(self, rows, machine=None, config_id=None):
        super().__init__(rows)
        self.machine = machine
        self.config_id = config_id

    def resolve(self, key):
        if dict.__contains__(self, key):
            return key
        if self.machine:
            prefixed = [f"{self.machine}.{key}"]
            if self.config_id:
                prefixed.insert(0, f"{self.machine}.{self.config_id}.{key}")
            for candidate in prefixed:
                if dict.__contains__(self, candidate):
                    return candidate
        suffix = "." + key
        candidates = [name for name in dict.keys(self) if name.endswith(suffix)]
        if len(candidates) == 1:
            return candidates[0]
        return key

    def __getitem__(self, key):
        return dict.__getitem__(self, self.resolve(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.resolve(key))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


def load_ledger(path, machine=None, config_id=None):
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
    return Ledger(rows, machine, config_id)


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
    for kind, names in required_names(model).items():
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
    capability_problems, _ = check_capabilities(model)
    problems.extend(capability_problems)
    if model_root is not None:
        problems.extend(check_ledger_against_xml(model_root, ledger))
    results = evaluate(model, data, ledger, model_root=model_root)
    failed = [name for name, ok, _ in results if not ok]
    if problems or failed:
        detail = "；".join(problems + [f"{name} 失败" for name in failed])
        raise ModelCheckError(f"A1–A5、名称表、能力声明或台账比对不过：{detail}")
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
    """chassis_* 几何在 x 方向的长度（判据用的车身长）。

    box / cylinder / sphere / ellipsoid 取 2×size[0]，capsule 取 2×(半径+半长)，
    其它 geom 用包围球直径兜底。OOMWOO 的圆柱壳体不再需要 wrapper 补丁。
    """
    lengths = []
    for gid in range(model.ngeom):
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        size = model.geom_size[gid]
        geom_type = int(model.geom_type[gid])
        if geom_type in (
            int(mujoco.mjtGeom.mjGEOM_BOX),
            int(mujoco.mjtGeom.mjGEOM_CYLINDER),
            int(mujoco.mjtGeom.mjGEOM_SPHERE),
            int(mujoco.mjtGeom.mjGEOM_ELLIPSOID),
        ):
            lengths.append(2.0 * float(size[0]))  # arithmetic
        elif geom_type == int(mujoco.mjtGeom.mjGEOM_CAPSULE):
            lengths.append(2.0 * (float(size[0]) + float(size[1])))  # arithmetic
        else:
            lengths.append(2.0 * float(model.geom_rbound[gid]))  # arithmetic
    if not lengths:
        raise ModelCheckError("chassis_* 中没有可求 x 向长度的几何")
    return max(lengths)


def chassis_min_z(model, data):
    """chassis_* 几何在 world z 方向的实际下界（契约 §3 的壳体最低点）。

    按 geom 类型与姿态求支撑映射，不再用包围球近似：圆柱/胶囊的竖直半高随
    轴向倾斜变化，box/ellipsoid 按旋转矩阵投影。OOMWOO 圆柱壳体因此得到真实
    底面，不需要 wrapper 补丁。
    """
    lows = []
    for gid in range(model.ngeom):
        model.geom(gid)  # 名称必须存在，缺名即失败
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        center_z = float(np.asarray(data.geom_xpos[gid], dtype=float)[2])
        size = np.asarray(model.geom_size[gid], dtype=float)
        geom_type = int(model.geom_type[gid])
        if geom_type == int(mujoco.mjtGeom.mjGEOM_SPHERE):
            lows.append(center_z - float(size[0]))
        elif geom_type == int(mujoco.mjtGeom.mjGEOM_CYLINDER):
            rot = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)
            axis_z = abs(float(rot[2, 2]))
            vertical = float(size[1]) * axis_z + float(size[0]) * math.sqrt(
                max(0.0, 1.0 - axis_z * axis_z)
            )
            lows.append(center_z - vertical)
        elif geom_type == int(mujoco.mjtGeom.mjGEOM_CAPSULE):
            rot = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)
            axis_z = abs(float(rot[2, 2]))
            lows.append(center_z - (float(size[0]) + float(size[1]) * axis_z))
        elif geom_type == int(mujoco.mjtGeom.mjGEOM_BOX):
            rot = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)
            half = sum(abs(float(rot[2, i])) * float(size[i]) for i in range(3))
            lows.append(center_z - half)
        elif geom_type == int(mujoco.mjtGeom.mjGEOM_ELLIPSOID):
            rot = np.asarray(data.geom_xmat[gid], dtype=float).reshape(3, 3)
            half = math.sqrt(
                sum((float(rot[2, i]) * float(size[i])) ** 2 for i in range(3))
            )
            lows.append(center_z - half)
        else:
            lows.append(center_z - float(model.geom_rbound[gid]))
    if not lows:
        raise ModelCheckError("chassis_* 中没有几何")
    return min(lows)


def euler_zyx(quat):
    w, x, y, z = quat
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))  # arithmetic
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))  # arithmetic
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))  # arithmetic
    return pitch, roll, yaw
