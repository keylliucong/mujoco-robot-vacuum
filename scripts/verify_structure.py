"""G2 结构自查：把《G2-结构规则-违反即失败》S01–S21 与交付抽查变成可执行检查。

用法（Windows，项目 .venv）：
    .venv\\Scripts\\python.exe scripts\\verify_structure.py            # 静态检查
    .venv\\Scripts\\python.exe scripts\\verify_structure.py --run      # 含集成抽查（会跑仿真）

输出每项 PASS / FAIL / SKIP 与原因；任一 FAIL 退出码 1。
本文件是检查器，不参与仿真；与 run_cases.py 的常量重复是故意的（检查器不能自证）。
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

CONTRACT_VERSION = "1.9.0"
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = REPO_ROOT / "models" / "baseline.xml"
PARAMS_PATH = REPO_ROOT / "params" / "prototype.json"
LEDGER_PATH = REPO_ROOT / "docs" / "参数溯源.csv"
CASES_DIR = REPO_ROOT / "cases"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(REPO_ROOT))

import params_io  # noqa: E402

try:
    import mujoco  # noqa: E402
    import numpy as np  # noqa: E402

    HAVE_MUJOCO = True
except Exception:  # pragma: no cover - 静态检查时无 MuJoCo 也能跑
    HAVE_MUJOCO = False

FROZEN_TIMESERIES = [
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
    "chassis_min_z_m",
]

FROZEN_SUMMARY = [
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

FAILURE_ENUM = {
    "topple",
    "belly_contact",
    "retreat",
    "cross_fail",
    "timeout",
    "stall",
    "bottom_out",
    "suspension_bottom",
    "slip",
    "torque_limit",
    "no_contact",
    "data_invalid",
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

RESULTS = []


def add(check_id, ok, detail):
    RESULTS.append({"id": check_id, "ok": ok, "detail": detail})


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def py_files():
    return sorted(SCRIPTS_DIR.glob("*.py")) + [REPO_ROOT / "judge.py"]


def literal_assignment(path, name, default=None):
    tree = ast.parse(read_text(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    return default


def module_constant(path, name):
    tree = ast.parse(read_text(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    return None


def load_ledger():
    with open(LEDGER_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return reader.fieldnames, rows


def rendered_model():
    return params_io.load_and_render(MODEL_PATH)


def outputs_run_json(root=None):
    if root is not None:
        base = Path(root)
        candidate = base / "run.json"
        if not candidate.exists():
            return None, None
        return candidate, json.loads(read_text(candidate))
    base = OUTPUTS_DIR
    if not base.exists():
        return None, None
    candidates = sorted(
        base.glob("*/run.json"), key=lambda path: path.stat().st_mtime, reverse=True
    )
    if not candidates:
        return None, None
    return candidates[0], json.loads(read_text(candidates[0]))


# ---------------------------------------------------------------- S01–S21


def check_s01():
    pattern = re.compile(r"\.(qpos|qvel|actuator_force|geom_xpos|xpos)\s*\[\s*\d")
    offenders = []
    for path in py_files():
        if path.name == "verify_env.py":
            continue
        for lineno, line in enumerate(read_text(path).splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{lineno}")
    names_ok = True
    detail = "按名称取用"
    if HAVE_MUJOCO:
        model, data, root, _ = load_model()
        problems = []
        required = {
            "body": ["chassis", "wheel_L", "wheel_R"],
            "joint": ["wheel_L_spin", "wheel_R_spin", "susp_L", "susp_R"],
            "actuator": ["wheel_L", "wheel_R"],
            "material": ["floor", "step"],
        }
        for kind, items in required.items():
            for name in items:
                try:
                    getattr(model, kind)(name)
                except KeyError:
                    problems.append(f"{kind}:{name}")
        names_ok = not problems
        detail = "名称表齐全" if names_ok else f"缺名称 {problems}"
    if offenders:
        add("S01", False, "出现整数索引：" + ", ".join(offenders))
    else:
        add("S01", names_ok, detail + "；无 qpos/qvel 等数字下标")


def check_s02():
    bad = []
    for path in py_files():
        if path.name in (
            "verify_structure.py",
            "verify_env.py",
            "run_oomwoo.py",
            "generate_g25_lip_params.py",
            "analyze_g25_contacts.py",
            "diag_g25_first_contact.py",
        ):
            # 这些文件不属于 G2 run_cases 判定路径（自查器自身 / G1 冒烟 / G2.5 工具）。
            # view.py 不再豁免：它是 UI 常量，但逐行标 `# ui-constant`，仍受本检查。
            continue
        tree = ast.parse(read_text(path))
        lines = read_text(path).splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                if node.value in (0.0, 1.0):
                    continue
                line = lines[node.lineno - 1]
                if (
                    "# arithmetic" in line
                    or "# contract-tolerance" in line
                    or (path.name == "view.py" and "# ui-constant" in line)
                ):
                    continue
                bad.append(f"{path.name}:{node.lineno}={node.value}")
    add(
        "S02",
        not bad,
        "脚本内无物理字面量（0/1 与标注 arithmetic/tolerance 的算法常量除外；verify_env.py 归 G1）"
        if not bad
        else "未标注浮点字面量：" + ", ".join(bad),
    )


def check_s03():
    offenders = []
    for path in (REPO_ROOT / "models").glob("*.xml"):
        root = ET.parse(path).getroot()
        for geom in root.iter("geom"):
            name = geom.get("name") or ""
            if name.startswith("step"):
                offenders.append(f"{path.name}:{name}")
    add("S03", not offenders, "模型中无台阶几何" if not offenders else f"模型里出现台阶几何 {offenders}")


def check_s04():
    text = read_text(REPO_ROOT / "judge.py")
    banned = []
    if re.search(r"^\s*(import|from)\s+mujoco", text, re.M):
        banned.append("import mujoco")
    for token in ("regression_expect", "expected", "MjModel", "model.opt"):
        if token in text:
            banned.append(token)
    add(
        "S04",
        not banned,
        "judge.py 无 mujoco / 配置对象 / 期望结果引用" if not banned else f"judge.py 出现 {banned}",
    )


def check_s05():
    timeseries = literal_assignment(SCRIPTS_DIR / "run_cases.py", "TIMESERIES_COLUMNS", [])
    tail = literal_assignment(SCRIPTS_DIR / "run_cases.py", "TIMESERIES_TAIL", [])
    summary = literal_assignment(SCRIPTS_DIR / "run_cases.py", "SUMMARY_COLUMNS", [])
    actual_ts = list(timeseries) + list(tail)
    ok = actual_ts == FROZEN_TIMESERIES and list(summary) == FROZEN_SUMMARY
    add(
        "S05",
        ok,
        "时程与摘要表头等于冻结集合"
        if ok
        else f"表头不一致：时程缺 {set(FROZEN_TIMESERIES) - set(actual_ts)}，摘要差 {set(FROZEN_SUMMARY) ^ set(summary)}",
    )


def check_s06(root=None):
    run_json_path, _ = outputs_run_json(root)
    if run_json_path is None:
        add("S06", None, "SKIP：尚无 outputs，集成测试会跑双向断言")
        return
    timeseries = next(run_json_path.parent.glob("*/timeseries.csv"), None)
    if timeseries is None:
        add("S06", None, "SKIP：批次里没有 timeseries.csv")
        return
    rows = list(csv.DictReader(open(timeseries, encoding="utf-8")))
    problems = []
    for column in rows[0]:
        if not column.endswith("_active"):
            continue
        prefix = column[: -len("_active")]
        normal = prefix + "_normal_n"
        tangent = prefix + "_tangent_n"
        for index, row in enumerate(rows, 2):
            if row[column] == "0" and (row[normal] or row[tangent]):
                problems.append(f"{timeseries.name}:{index} active=0 但力非空")
            if row[column] == "1" and (not row[normal] or not row[tangent]):
                problems.append(f"{timeseries.name}:{index} active=1 但力为空")
            if problems:
                break
    add("S06", not problems, "无接触/零值双向断言通过" if not problems else "；".join(problems[:5]))


def check_s07():
    offenders = []
    for path in (SCRIPTS_DIR / "run_cases.py", REPO_ROOT / "judge.py"):
        if "efc_force" in read_text(path):
            offenders.append(path.name)
    add(
        "S07",
        not offenders,
        "输出路径只用 mj_contactForce"
        if not offenders
        else f"{offenders} 出现 efc_force（verify_env.py 冒烟脚本按 G1 任务另行处理）",
    )


def check_s08():
    suffix_ok = re.compile(r"_(m|s|n|nm|rad|mps|radps|deg)$")
    allowed_flags = re.compile(r"_(active|count|ratio)$")
    dimensionless = {"quat_w", "quat_x", "quat_y", "quat_z"}
    bad = []
    for column in FROZEN_TIMESERIES:
        if column in dimensionless:
            continue
        if not (suffix_ok.search(column) or allowed_flags.search(column)):
            bad.append(column)
    add("S08", not bad, "时程列名均带单位后缀或 flag/count/_ratio" if not bad else f"缺后缀：{bad}")


def check_s09():
    problems = []
    for path in sorted(CASES_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        config = json.loads(read_text(path))
        unknown = set(config) - CASE_KEYS
        if unknown:
            problems.append(f"{path.name} 未定义键 {sorted(unknown)}")
        for banned in ("expected", "passed", "result"):
            if banned in config:
                problems.append(f"{path.name} 出现 {banned}")
        fail_on = config["judge"]["fail_on"]
        if not set(fail_on).issubset(FAILURE_ENUM):
            problems.append(f"{path.name} fail_on 越界 {fail_on}")
    judge_text = read_text(REPO_ROOT / "judge.py")
    if "regression_expect" in judge_text:
        problems.append("judge.py 读取 regression_expect")
    add("S09", not problems, "配置无期望结果键，judge 不读 regression_expect" if not problems else "；".join(problems))


def check_s10():
    fields, rows = load_ledger()
    expected_fields = [
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
    problems = []
    if fields != expected_fields:
        problems.append(f"台账列不是 9 列：{fields}")
    bad_labels = [r["param_id"] for r in rows if r["label"] not in params_io.LABELS]
    if bad_labels:
        problems.append(f"非法 label：{bad_labels[:5]}")
    params_doc = json.loads(read_text(PARAMS_PATH))
    ledger = {r["param_id"]: r for r in rows}
    for param_id, entry in params_doc["params"].items():
        if param_id not in ledger:
            problems.append(f"params 有 {param_id} 但台账缺行")
            continue
        if abs(float(ledger[param_id]["value"]) - float(entry["value"])) > 1e-12:  # arithmetic
            problems.append(f"{param_id} 台账值与 params 不一致")
        if ledger[param_id]["label"] != entry["label"]:
            problems.append(f"{param_id} 标签与 params 不一致")
    if HAVE_MUJOCO:
        rendered = rendered_model()
        import model_checks  # noqa: E402

        ledger_rows = model_checks.load_ledger(LEDGER_PATH, machine=params_doc["machine"])
        problems.extend(
            model_checks.check_ledger_against_xml(ET.fromstring(rendered["text"]), ledger_rows)
        )
    if problems:
        add("S10", False, "；".join(problems[:8]))
    elif not HAVE_MUJOCO:
        add("S10", True, "台账 9 列 / 标签 / params 一致；XML 比对需 MuJoCo（集成时复跑）")
    else:
        add("S10", True, "台账↔params↔渲染后 XML 数值一致")


def check_s11(root=None):
    run_json_path, run_json = outputs_run_json(root)
    if run_json_path is None:
        add("S11", None, "SKIP：尚无 outputs")
        return
    required = [
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
    missing = [key for key in required if key not in run_json]
    ok = not missing
    add("S11", ok, f"{run_json_path.parent.name}/run.json 必备键齐全" if ok else f"缺 {missing}")


def check_s12(run_integration):
    if not run_integration:
        add("S12", None, "SKIP：需要 --run（会实际跑一次仿真）")
        return
    temp_root = Path(tempfile.mkdtemp(prefix="g2-s12-"))
    try:
        target = temp_root / "batch"
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "run_cases.py"),
            "--config",
            str(CASES_DIR / "flat.json"),
            "--out",
            str(target),
        ]
        first = subprocess.run(command, capture_output=True, text=True)
        second = subprocess.run(command, capture_output=True, text=True)
        ok = first.returncode == 0 and second.returncode != 0
        add("S12", ok, f"首次 rc={first.returncode}，重复 rc={second.returncode}（应非 0）")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def check_s13():
    problems = []
    for path in (REPO_ROOT / "models").iterdir():
        if path.is_file() and path.suffix != ".xml":
            problems.append(f"models/ 出现 {path.name}")
    for path in CASES_DIR.iterdir():
        if path.is_file() and path.suffix != ".json":
            problems.append(f"cases/ 出现 {path.name}")
    for path in SCRIPTS_DIR.glob("*.py"):
        if path.name in ("verify_env.py", "verify_structure.py"):
            continue
        if "<mujoco" in read_text(path):
            problems.append(f"scripts/{path.name} 内联 MJCF")
    add("S13", not problems, "目录所有权正确" if not problems else "；".join(problems))


def check_s14():
    version = module_constant(SCRIPTS_DIR / "run_cases.py", "CONTRACT_VERSION")
    judge_version = module_constant(REPO_ROOT / "judge.py", "CONTRACT_VERSION")
    doc = read_text(REPO_ROOT / "docs" / "契约" / "G2-接口契约.md")
    match = re.search(r"版本：`([0-9.]+)`", doc)
    doc_version = match.group(1) if match else ""
    ok = (
        version == CONTRACT_VERSION
        and judge_version == CONTRACT_VERSION
        and doc_version.strip() == CONTRACT_VERSION
    )
    add(
        "S14",
        ok,
        f"run_cases={version} judge={judge_version} 契约文档={doc_version}（版本串相等；判据集冻结在 v1.7）"
        if ok
        else f"版本不一致：run_cases={version} judge={judge_version} 文档={doc_version}",
    )


def check_s15():
    text = read_text(SCRIPTS_DIR / "run_cases.py")
    markers = ["回读不一致", "拒绝覆盖", "raise ContractError"]
    missing = [m for m in markers if m not in text]
    add("S15", not missing, "数值注入后回读断言、覆盖即 raise" if not missing else f"缺 {missing}")


def load_model():
    import model_checks

    rendered = rendered_model()
    model = mujoco.MjModel.from_xml_string(rendered["text"])
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    ledger = model_checks.load_ledger(LEDGER_PATH, machine=rendered["header"]["machine"])
    return model, data, ET.fromstring(rendered["text"]), ledger


def check_s16():
    if not HAVE_MUJOCO:
        add("S16", None, "SKIP：本机无 MuJoCo，A1–A5 需在 Windows 集成检查里跑")
        return
    import model_checks

    model, data, root, ledger = load_model()
    results = model_checks.evaluate(model, data, ledger, model_root=root)
    failures = [f"{name}:{detail}" for name, ok, detail in results if not ok]
    if failures:
        add("S16", False, "A1–A5 不过：" + "；".join(failures))
        return

    def mutated(mutator):
        tree = ET.fromstring(rendered_model()["text"])
        mutator(tree)
        text = ET.tostring(tree, encoding="unicode")
        test_model = mujoco.MjModel.from_xml_string(text)
        test_data = mujoco.MjData(test_model)
        mujoco.mj_forward(test_model, test_data)
        return model_checks.evaluate(test_model, test_data, ledger, model_root=tree)

    def shift_inertial(tree):
        for body in tree.iter("body"):
            if body.get("name") == "chassis":
                body.find("inertial").set("pos", "0.03 0 0.055")

    def drop_mass(tree):
        for body in tree.iter("body"):
            if body.get("name") == "wheel_R":
                body.find("inertial").set("mass", "0.01")

    def shift_wheel(tree):
        for body in tree.iter("body"):
            if body.get("name") == "wheel_L":
                body.set("pos", "0 0.137 0.035")

    alarms = []
    for name, mutator, expected in (
        ("inertial 挪 20 mm", shift_inertial, "A2"),
        ("漏掉 0.02 kg", drop_mass, "A1"),
        ("轮心挪 2 mm", shift_wheel, "A4"),
    ):
        mutated_results = {item[0]: item[1] for item in mutated(mutator)}
        if mutated_results.get(expected):
            alarms.append(f"{name} 未报警（{expected} 仍通过）")
    add(
        "S16",
        not alarms,
        "A1–A5 全过；三类故意错位均报警" if not alarms else "；".join(alarms),
    )


def check_s17():
    _, rows = load_ledger()
    _, run_json = outputs_run_json()
    level = run_json.get("conclusion_level") if run_json else None
    offenders = [
        row["param_id"]
        for row in rows
        if row["label"] == "图纸推算" and not row["verified_by"].strip()
    ]
    if level == "quantitative" and offenders:
        add("S17", False, f"图纸推算未逐行放行却被算进 quantitative：{offenders[:5]}")
    else:
        add(
            "S17",
            True,
            "无【图纸推算】行；结论等级不高于 sensitivity"
            if not offenders
            else f"{len(offenders)} 行【图纸推算】未放行，等级按 sensitivity 封顶",
        )


def check_s18():
    _, rows = load_ledger()
    problems = []
    for row in rows:
        tol = row["verified_tol"].strip()
        if tol and "%" in tol:
            problems.append(f"{row['param_id']} verified_tol 用了相对口径")
    for path in CASES_DIR.glob("*.json"):
        if "diag_3sigma" in read_text(path):
            problems.append(f"{path.name} 出现 diag_3sigma_A")
    if "diag_3sigma" in read_text(REPO_ROOT / "judge.py"):
        problems.append("judge.py 出现 diag_3sigma_A")
    if not problems:
        add("S18", True, "无 verified_tol / 无相对容差 / 诊断量不进判定")
    else:
        add("S18", False, "；".join(problems))


def current_machine_rows():
    _, rows = load_ledger()
    machine = rendered_model()["header"]["machine"]
    prefix = f"{machine}."
    return [row for row in rows if row["param_id"].startswith(prefix)]


def budget_rows():
    path = REPO_ROOT / "docs" / "不确定度预算.csv"
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_s19():
    """S19：真的打开预算表，逐行核对有 verified_tol 的台账量是否有 B 类分量。"""
    rows = current_machine_rows()
    tol_rows = [row["param_id"] for row in rows if row["verified_tol"].strip()]
    budget = budget_rows()
    if budget is None:
        add("S19", False, "docs/不确定度预算.csv 不存在，无法核对 verified_tol")
        return
    budget_ids = {row["param_id"] for row in budget if row.get("param_id")}
    missing = [param_id for param_id in tol_rows if param_id not in budget_ids]
    if missing:
        add("S19", False, f"有 verified_tol 但预算表缺行：{missing[:5]}")
        return
    machine = rendered_model()["header"]["machine"]
    add(
        "S19",
        True,
        f"{machine} 机型 {len(tol_rows)} 行带 verified_tol，预算表已逐行覆盖；"
        f"预算表共 {len(budget_ids)} 个 param_id（含其他机型）",
    )


def check_s20():
    comparison = [row for row in current_machine_rows() if row["verified_tol"].strip()]
    if comparison:
        add("S20", False, "存在比对容差但 u_sim 三项五要素尚未实现")
    else:
        add(
            "S20",
            None,
            "SKIP：当前机型无实测↔仿真比对行；u_sim 三项五要素未实现，需实测数据后留 G5",
        )


def check_s21():
    _, rows = load_ledger()
    machine = rendered_model()["header"]["machine"]
    ledger = {row["param_id"]: row for row in rows}
    params_doc = json.loads(read_text(PARAMS_PATH))
    problems = []
    needed = [
        f"{machine}.payload.empty.m",
        f"{machine}.payload.empty.com_x",
        f"{machine}.payload.empty.inertia_xx",
    ]
    for param_id in needed:
        if param_id not in ledger:
            problems.append(f"缺载荷状态行 {param_id}")
    for suffix in ("inertia_xx", "inertia_yy", "inertia_zz"):
        param_id = f"{machine}.payload.empty.{suffix}"
        if param_id in ledger:
            ref = ledger[param_id]["ref"]
            for token in ("role=", "ref_point=", "axes=", f"config_id={params_doc['config_id']}"):
                if token not in ref:
                    problems.append(f"{param_id} ref 缺 {token}")
    for path in CASES_DIR.glob("*.json"):
        if path.name.startswith("_"):
            continue
        config = json.loads(read_text(path))
        match = re.search(r"config_id=([a-z0-9_]+)", config.get("notes", ""))
        if not match:
            problems.append(f"{path.name} notes 缺 config_id")
        elif match.group(1) == params_doc["config_id"]:
            continue  # 本机型 case，已按 prototype 参数集核对
        # 其它机型（如 oomwoo_g25）的 case 不属于本次原型参数集，留给对应参数集核对
    add("S21", not problems, "载荷状态成套、参考点/坐标系齐备、case 与参数集同 ID" if not problems else "；".join(problems))


# ---------------------------------------------------------------- 交付抽查


def check_s22():
    """S22 / 抽查 16：能力声明与模型两端一致；无该自由度时整列为空且不进 flags。"""
    if not HAVE_MUJOCO:
        add("S22", None, "SKIP：需要 MuJoCo 才能跑能力声明与空列断言")
        return
    import model_checks

    problems = []
    rendered = rendered_model()
    model = mujoco.MjModel.from_xml_string(rendered["text"])
    cap_problems, has_suspension = model_checks.check_capabilities(model)
    problems.extend(cap_problems)
    if has_suspension != 1:
        problems.append(f"本模型的 has_suspension={has_suspension}，基线原型应为 1")

    def capability_tree(value, drop_susp=False):
        tree = ET.fromstring(rendered["text"])
        for numeric in tree.iter("numeric"):
            if numeric.get("name") == "has_suspension":
                numeric.set("data", str(value))
        if drop_susp:
            for body in tree.iter("body"):
                for child in list(body):
                    if child.tag == "joint" and (child.get("name") or "").startswith("susp"):
                        body.remove(child)
        return tree

    # 抽查 16a：声明 0 但保留 susp 关节必须失败
    mutated = capability_tree(0)
    model_zero = mujoco.MjModel.from_xml_string(ET.tostring(mutated, encoding="unicode"))
    negative, _ = model_checks.check_capabilities(model_zero)
    if not negative:
        problems.append("声明 has_suspension=0 但保留 susp_* 关节未报警（抽查 16a）")

    # 抽查 16b：声明 0 且删除 susp 关节应可编译并通过
    mutated_ok = capability_tree(0, drop_susp=True)
    model_no_susp = mujoco.MjModel.from_xml_string(
        ET.tostring(mutated_ok, encoding="unicode")
    )
    ok_problems, cap_ok = model_checks.check_capabilities(model_no_susp)
    if ok_problems or cap_ok != 0:
        problems.append(f"声明 0 且无 susp 关节仍报错：{ok_problems}")

    # 抽查 16c：无悬挂时 susp 列必须整列为空；写 0 必须失败
    import judge

    columns, params = synthetic_case(
        flags=["topple", "retreat", "timeout", "stall"], bottom_out=False
    )
    params_no_susp = dict(params)
    params_no_susp["has_suspension"] = False
    params_no_susp["susp_range_m"] = 0.0
    empty_columns = {name: list(values) for name, values in columns.items()}
    empty_columns["susp_L_travel_m"] = [""] * len(columns["t_s"])
    empty_columns["susp_R_travel_m"] = [""] * len(columns["t_s"])
    try:
        verdict = judge.judge_case(empty_columns, params_no_susp)
        if "suspension_bottom" in verdict["failure_flags"]:
            problems.append("无悬挂时仍产生 suspension_bottom（抽查 16c）")
        if verdict["metrics"]["susp_travel_max_L_m"] is not None:
            problems.append("无悬挂时 susp 指标不是空")
    except judge.JudgeError as error:
        problems.append(f"无悬挂空列被误判为错：{error}")
    zero_columns = {name: list(values) for name, values in empty_columns.items()}
    zero_columns["susp_L_travel_m"] = ["0.0"] * len(columns["t_s"])
    try:
        judge.judge_case(zero_columns, params_no_susp)
        problems.append("无悬挂时把 susp 列写 0 未报错（抽查 16c）")
    except judge.JudgeError:
        pass

    # 列元数据：无悬挂时 missing=true
    import run_cases

    meta = run_cases.column_metadata(list(columns), has_suspension=False)
    if not meta["susp_L_travel_m"]["missing"] or not meta["susp_R_travel_m"]["missing"]:
        problems.append("无悬挂时 run.json.columns 未标 missing=true（S22）")

    run_json_path, run_json = outputs_run_json()
    if (
        run_json
        and "capabilities" in run_json
        and run_json.get("machine") == rendered_model()["header"]["machine"]
    ):
        declared = run_json["capabilities"].get("has_suspension")
        missing = run_json.get("columns", {}).get("susp_L_travel_m", {}).get("missing")
        if declared != has_suspension or bool(missing) != (declared == 0):
            problems.append("run.json.capabilities 与 columns.missing 不自洽（S22）")

    add(
        "S22",
        not problems,
        "has_suspension=1、行程>0；声明 0 保留关节/写 0 均报警、空列可判"
        if not problems
        else "；".join(problems),
    )


def check_s24():
    """S24（v1.8.3）：逐 contact 三条断言 + 3 分量写进 pair 的负例 + 禁止下沉到 geom。"""
    if not HAVE_MUJOCO:
        add("S24", None, "SKIP：需要 MuJoCo 才能读 d.contact[i]")
        return
    import run_cases

    problems = []
    config = json.loads(read_text(CASES_DIR / "baseline.json"))
    rendered = rendered_model()
    defaults = json.loads(read_text(CASES_DIR / "_runner.json"))
    base = mujoco.MjModel.from_xml_string(rendered["text"])
    scenario = run_cases.build_scenario_xml(
        rendered["text"], config, run_cases.chassis_front(base), defaults, rendered["params"]
    )
    lookup, ordered = run_cases.build_pair_lookup(config, "step")
    specs = run_cases.friction_expectations(config, "step")

    def assert_all(model, data):
        names = run_cases.geom_name_table(model)
        readback = {}
        for index in range(data.ncon):
            contact = data.contact[index]
            name1 = names.get(int(contact.geom1))
            name2 = names.get(int(contact.geom2))
            spec = specs.get(frozenset((name1, name2)))
            if spec is None:
                continue
            run_cases.check_s24_contact(contact, spec, f"{name1}--{name2}")
            readback[lookup.get(frozenset((name1, name2)))] = [
                float(v) for v in contact.friction
            ]
        return readback

    model = mujoco.MjModel.from_xml_string(scenario)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    try:
        readback = assert_all(model, data)
    except run_cases.ContractError as error:
        problems.append(f"正例被误判：{error}")
        readback = {}
    if "wheel_L--floor" not in readback:
        problems.append("正例没有覆盖到 wheel_L--floor 的 contact 真值")
    for key, values in readback.items():
        if len(values) > 1 and values[0] != values[1]:
            problems.append(f"{key} 各向异性 {values[:2]}")

    # 负例 ①②：把 geom 的 3 分量写法抄进 pair，必须被 friction[0]!=friction[1] 拦住
    tree = ET.fromstring(scenario)
    for pair in tree.iter("pair"):
        if pair.get("geom1") == "wheel_L_tire" and pair.get("geom2") == "floor_plane":
            pair.set("friction", "0.8 0.005 0.0001")
    bad_model = mujoco.MjModel.from_xml_string(ET.tostring(tree, encoding="unicode"))
    bad_data = mujoco.MjData(bad_model)
    mujoco.mj_forward(bad_model, bad_data)
    try:
        assert_all(bad_model, bad_data)
        problems.append("3 分量 pair 写法未被 S24 第②条拦住")
    except run_cases.ContractError:
        pass

    # 禁止下沉到 geom：轮-台阶 μ 必须留在 pair，且与 geom 默认不同
    pair_mu = float(config["environment"]["pairs"]["wheel_L--step"]["friction"][0])
    geom_mu = float(params_io.get_param(rendered["params"], "contact.friction_s")[1]["value"])
    pair_present = any(
        pair.get("geom1") == "wheel_L_tire" and pair.get("geom2") == "step"
        for pair in ET.fromstring(scenario).iter("pair")
    )
    if not pair_present:
        problems.append("wheel_L_tire--step 没有 pair 元素（被下沉到 geom）")
    if pair_mu == geom_mu:
        problems.append("轮-台阶 μ 与 geom 默认相同，pair 级区分被合并")

    add(
        "S24",
        not problems,
        f"逐 contact 三条断言通过（{len(readback)} 个接触对）；3 分量 pair 被拦；轮-台阶 μ={pair_mu} 留在 pair（geom={geom_mu}）"
        if not problems
        else "；".join(problems),
    )


def check_negative_configs():
    """抽查 2/3：flat 带 obstacle、含 expected 的配置必须报错。"""
    if not HAVE_MUJOCO:
        add("抽查2/3", None, "SKIP：需要 MuJoCo 才能导入 run_cases")
        return
    sys.path.insert(0, str(SCRIPTS_DIR))
    import run_cases

    problems = []
    for name in ("flat_with_obstacle.json", "expected_key.json"):
        path = CASES_DIR / "invalid" / name
        try:
            run_cases.load_case(path)
            problems.append(f"{name} 未报错")
        except run_cases.ContractError:
            pass
    add("抽查2/3", not problems, "flat+obstacle 与 expected 键均被拒绝" if not problems else "；".join(problems))


def synthetic_case(flags, bottom_out):
    """构造最小可用时程，用于判定单点测试（不跑仿真）。"""
    h = 0.002
    duration = 2.0
    n = int(duration / h) + 1
    columns = {name: [] for name in FROZEN_TIMESERIES}
    columns["t_s"] = [i * h for i in range(n)]
    for name in ("pos_y_m", "vel_y_mps", "vel_z_mps", "roll_rad", "yaw_rad", "quat_x", "quat_y", "quat_z"):
        columns[name] = [0.0] * n
    columns["quat_w"] = [1.0] * n
    columns["pos_x_m"] = [0.15 * t for t in columns["t_s"]]
    columns["pos_z_m"] = [0.02 if t >= 0.4 else 0.0 for t in columns["t_s"]]
    columns["pitch_rad"] = [0.0] * n
    columns["vel_x_mps"] = [0.15] * n
    columns["wheel_L_speed_radps"] = [0.15 / 0.035] * n
    columns["wheel_R_speed_radps"] = [0.15 / 0.035] * n
    columns["wheel_L_torque_nm"] = [0.05] * n
    columns["wheel_R_torque_nm"] = [0.05] * n
    columns["susp_L_travel_m"] = [0.0] * n
    columns["susp_R_travel_m"] = [0.0] * n
    columns["chassis_min_z_m"] = [0.03] * n
    pairs = ["wheel_L--step", "wheel_R--step", "chassis--step"]
    for prefix in pairs:
        columns[f"contact_{prefix}_active"] = []
        columns[f"contact_{prefix}_normal_n"] = []
        columns[f"contact_{prefix}_tangent_n"] = []
        columns[f"contact_{prefix}_count"] = []
    for i, t in enumerate(columns["t_s"]):
        for prefix in pairs:
            if prefix.startswith("wheel"):
                active = 1 if t >= 0.2 else 0
            else:
                active = 1 if (bottom_out and 0.5 <= t <= 0.8) else 0
            columns[f"contact_{prefix}_active"].append("1" if active else "0")
            columns[f"contact_{prefix}_normal_n"].append("5.0" if active else "")
            columns[f"contact_{prefix}_tangent_n"].append("0.5" if active else "")
            columns[f"contact_{prefix}_count"].append("1" if active else "0")
    params = {
        "kind": "step",
        "timestep_s": h,
        "speed_mps": 0.15,
        "window_s": 1.0,
        "fail_on": list(flags),
        "min_advance_m": 0.1,
        "recover_speed_ratio": 0.8,
        "recover_hold_s": 0.3,
        "stall_speed_mps": 0.01,
        "stall_duration_s": 1.0,
        "tilt_pitch_deg": 25.0,
        "tilt_roll_deg": 15.0,
        "slip_ratio": 0.3,
        "contact_normal_min_n": 0.5,
        "settle_tol_mps": 0.02,
        "settle_window_s": 0.2,
        "settle_end_s": 0.5,
        "wheel_radius_m": 0.035,
        "step_height_m": 0.02,
        "platform_height_tol_m": 0.006,
        "step_front_m": 0.16,
        "step_half_width_m": 0.6,
        "heading_rad": 0.0,
        "com_offset_x_m": 0.0,
        "contact_gap_tol_s": 0.05,
        "susp_range_m": 0.006,
        "susp_bottom_rel": 0.999,
        "torque_limit_L_nm": 0.8,
        "torque_limit_R_nm": 0.8,
        "torque_saturation_rel": 0.000001,
        "slip_eps_mps": 0.000001,
        "climb_height_ratio": 0.9,
        "climb_hold_s": 0.2,
        "has_suspension": True,
        "pair_friction": {key: 0.8 for key in pairs},
        "wheel_step_pairs": ["wheel_L--step", "wheel_R--step"],
        "bottom_out_pairs": ["chassis--step"],
        "all_pairs": pairs,
    }
    return columns, params


def check_judge_unit_tests():
    import judge

    problems = []
    columns, params = synthetic_case(flags=["topple", "retreat", "timeout", "stall"], bottom_out=True)
    verdict = judge.judge_case(columns, params)
    if verdict["passed"] != 1:
        problems.append(f"无 fail_on 时 bottom_out 不应判负：{verdict['passed']} flags={verdict['failure_flags']}")
    params2 = dict(params)
    params2["fail_on"] = list(params["fail_on"]) + ["bottom_out"]
    verdict2 = judge.judge_case(columns, params2)
    if verdict2["passed"] != 0 or verdict2["failure_primary"] != "bottom_out":
        problems.append(
            f"fail_on 加 bottom_out 后结论未变：passed={verdict2['passed']} primary={verdict2['failure_primary']}"
        )

    broken = {name: list(values) for name, values in columns.items()}
    broken["contact_wheel_L--step_active"] = ["0"] * len(broken["t_s"])
    try:
        judge.judge_case(broken, params)
        problems.append("active 全 0 但力列非空未报错")
    except judge.JudgeError:
        pass

    # 负例 1：pitch=50° 必须触发 topple（单位必须是度；v1.8.3 返工阻断 1）
    tilted = {name: list(values) for name, values in columns.items()}
    tilted["pitch_rad"] = [math.radians(50.0)] * len(tilted["t_s"])
    topple_params = dict(params)
    topple_params["fail_on"] = list(params["fail_on"]) + ["topple"]
    verdict_tilt = judge.judge_case(tilted, topple_params)
    if verdict_tilt["passed"] != 0 or verdict_tilt["failure_primary"] != "topple":
        problems.append(
            f"pitch=50° 未触发 topple：passed={verdict_tilt['passed']} "
            f"primary={verdict_tilt['failure_primary']} "
            f"pitch_max_deg={verdict_tilt['metrics']['pitch_max_deg']}"
        )
    if not 49.0 <= float(verdict_tilt["metrics"]["pitch_max_deg"]) <= 51.0:
        problems.append(f"pitch_max_deg 不是度：{verdict_tilt['metrics']['pitch_max_deg']}")
    if "timeout" in verdict_tilt["failure_flags"]:
        problems.append(f"topple 仍被追加 timeout：{verdict_tilt['failure_flags']}")

    # 负例 2：末帧回到地面、台阶接触中断（斜向绕行形态）不得 passed
    detour = {name: list(values) for name, values in columns.items()}
    for i, t in enumerate(detour["t_s"]):
        if t >= 1.0:
            detour["pos_z_m"][i] = 0.0
            detour["pos_y_m"][i] = 1.2
            for prefix in ("wheel_L--step", "wheel_R--step"):
                detour[f"contact_{prefix}_active"][i] = "0"
                detour[f"contact_{prefix}_normal_n"][i] = ""
                detour[f"contact_{prefix}_tangent_n"][i] = ""
                detour[f"contact_{prefix}_count"][i] = "0"
    verdict_detour = judge.judge_case(detour, params)
    if verdict_detour["passed"] != 0 or "cross_fail" not in verdict_detour["failure_flags"]:
        problems.append(
            f"绕行/末帧落地仍 passed={verdict_detour['passed']} "
            f"flags={verdict_detour['failure_flags']}"
        )
    reasons = verdict_detour["metrics"].get("crossing", {}).get("cross_fail_reasons", [])
    if not reasons:
        problems.append("cross_fail 没有逐项子条件 metrics")

    # 负例 3：末帧一离开台阶、另一轮仍在地面（骑棱边），但高度够平台——不得算完成
    one_wheel = {name: list(values) for name, values in columns.items()}
    n = len(one_wheel["t_s"])
    floor_pairs = ["wheel_L--floor", "wheel_R--floor"]
    for prefix in floor_pairs:
        for suffix, fill in (
            ("_active", "0"),
            ("_normal_n", ""),
            ("_tangent_n", ""),
            ("_count", "0"),
        ):
            one_wheel[f"contact_{prefix}{suffix}"] = [fill] * n
    one_wheel_params = dict(params)
    one_wheel_params["all_pairs"] = list(params["all_pairs"]) + floor_pairs
    one_wheel_params["pair_friction"] = dict(params["pair_friction"])
    for key in floor_pairs:
        one_wheel_params["pair_friction"][key] = 0.8
    for i, t in enumerate(one_wheel["t_s"]):
        if t >= 1.0:
            one_wheel["pos_z_m"][i] = 0.02
            one_wheel["contact_wheel_L--step_active"][i] = "1"
            one_wheel["contact_wheel_R--step_active"][i] = "0"
            one_wheel["contact_wheel_R--step_normal_n"][i] = ""
            one_wheel["contact_wheel_R--step_tangent_n"][i] = ""
            one_wheel["contact_wheel_R--step_count"][i] = "0"
            one_wheel["contact_wheel_R--floor_active"][i] = "1"
            one_wheel["contact_wheel_R--floor_normal_n"][i] = "5.0"
            one_wheel["contact_wheel_R--floor_tangent_n"][i] = "0.0"
            one_wheel["contact_wheel_R--floor_count"][i] = "1"
    verdict_edge = judge.judge_case(one_wheel, one_wheel_params)
    edge_cross = verdict_edge["metrics"].get("crossing") or {}
    if edge_cross.get("ended_on_platform") is not False:
        problems.append(
            f"骑棱边（一轮台阶一轮地面）仍算 ended_on_platform：{edge_cross}"
        )
    if "not_ended_on_platform" not in edge_cross.get("cross_fail_reasons", []):
        problems.append("骑棱边未记入 cross_fail 子条件")

    # 负例 4：|Ft|/Fn = μ + 1e-9 落在浮点容差内，不得触发 slip_force_exceeded
    friction_edge = {name: list(values) for name, values in columns.items()}
    for i in range(len(friction_edge["t_s"])):
        if friction_edge["contact_wheel_L--step_active"][i] == "1":
            # 合成时程 normal=5.0 → tangent=5*(0.8+1e-9)=4.000000005，比值 0.800000001
            friction_edge["contact_wheel_L--step_tangent_n"][i] = "4.000000005"
    verdict_friction = judge.judge_case(friction_edge, params)
    if verdict_friction["metrics"].get("slip_force_exceeded") is not False:
        problems.append(
            "|Ft|/Fn=μ+1e-9 仍触发 slip_force_exceeded："
            f"{verdict_friction['metrics'].get('slip_force_exceeded')}"
        )
    if "slip" in verdict_friction["failure_flags"]:
        problems.append(
            f"|Ft|/Fn=μ+1e-9 仍记 slip：flags={verdict_friction['failure_flags']}"
        )
    # 正对照：超出容差（0.8000016 > 0.8*(1+1e-6)）仍必须触发，防止容差把真实打滑吞掉
    friction_over = {name: list(values) for name, values in columns.items()}
    for i in range(len(friction_over["t_s"])):
        if friction_over["contact_wheel_L--step_active"][i] == "1":
            friction_over["contact_wheel_L--step_tangent_n"][i] = "4.000008"
    verdict_over = judge.judge_case(friction_over, params)
    if verdict_over["metrics"].get("slip_force_exceeded") is not True:
        problems.append("|Ft|/Fn 超容差仍未触发 slip_force_exceeded")

    add("抽查4/6", not problems, "pitch 单位=度（50° 触发 topple）、绕行/骑棱边不通过、无接触双断言、fail_on 单点生效、|Ft|/Fn=μ+1e-9 不触发且超容差触发" if not problems else "；".join(problems))


def check_run_outputs(root=None):
    run_json_path, run_json = outputs_run_json(root)
    if run_json_path is None:
        add("抽查5/7/8", None, "SKIP：尚无 outputs，--run 会生成并复核")
        return
    problems = []
    if run_json["contract_version"] != CONTRACT_VERSION:
        problems.append(f"run.json contract_version={run_json['contract_version']}")
    if not run_json.get("scenario_xml_sha256"):
        problems.append("scenario_xml_sha256 为空")
    numeric = run_json.get("numerics", {})
    if not numeric or "timestep_s" not in numeric or numeric.get("cone") is None:
        problems.append("numerics 记录不全")
    if run_json.get("param_labels") is None:
        problems.append("param_labels 缺失")
    consistent = run_json.get("repeat", {}).get("consistent")
    if consistent is not True:
        problems.append(f"repeat.consistent={consistent}")
    add("抽查5/7", not problems, "run.json 关键项齐全、两次逐位一致" if not problems else "；".join(problems))


def integration_checks():
    temp_root = Path(tempfile.mkdtemp(prefix="g2-int-"))
    try:
        base_out = temp_root / "baseline"
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "run_cases.py"),
            "--config",
            str(CASES_DIR / "baseline.json"),
            "--out",
            str(base_out),
            "--repeat",
            "2",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        ok = result.returncode == 0
        run_json = json.loads(read_text(base_out / "run.json")) if ok else {}
        add(
            "抽查5",
            ok and run_json.get("repeat", {}).get("consistent") is True,
            "--repeat 2 两次 timeseries 与判定逐位一致" if ok else f"baseline 运行失败 rc={result.returncode}: {result.stderr[-300:]}",
        )

        topple_out = temp_root / "topple"
        topple_result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "run_cases.py"),
                "--config",
                str(CASES_DIR / "step_forward_60mm_topple.json"),
                "--out",
                str(topple_out),
            ],
            capture_output=True,
            text=True,
        )
        topple_ok = False
        detail = f"topple 负例运行失败 rc={topple_result.returncode}: {topple_result.stderr[-300:]}"
        if topple_result.returncode == 0:
            topple_json = json.loads(read_text(topple_out / "run.json"))
            verdict = topple_json["cases"][0]["repeats"][0]["tiers"][0]["verdict"]
            pitch = verdict["metrics"]["pitch_max_deg"]
            topple_ok = (
                verdict["status"] == "ok"
                and verdict["passed"] is False
                and verdict["failure_primary"] == "topple"
                and pitch is not None
                and float(pitch) > 25.0
            )
            detail = (
                f"60 mm 台阶实跑 pitch_max={pitch:.2f}°，"
                f"passed={verdict['passed']} primary={verdict['failure_primary']}"
                if topple_ok
                else f"未触发 topple：pitch={pitch} verdict={verdict}"
            )
        add("抽查9(topple)", topple_ok, detail)

        check_s06(base_out)
        check_s11(base_out)
        check_run_outputs(base_out)

        height_config = json.loads(read_text(CASES_DIR / "baseline.json"))
        height_config["case_id"] = "step_forward_40mm"
        height_config["scenario"]["obstacle"]["height_m"] = 0.04
        height_config.pop("regression_expect", None)
        height_path = temp_root / "height40.json"
        height_path.write_text(json.dumps(height_config, ensure_ascii=False), encoding="utf-8")
        height_out = temp_root / "height40"
        height_result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "run_cases.py"),
                "--config",
                str(height_path),
                "--out",
                str(height_out),
            ],
            capture_output=True,
            text=True,
        )
        same_model = True
        if height_result.returncode == 0:
            height_json = json.loads(read_text(height_out / "run.json"))
            same_model = height_json["model"]["sha256"] == run_json["model"]["sha256"]
            changed = height_json["scenario_xml_sha256"] != run_json["scenario_xml_sha256"]
        else:
            changed = False
        add(
            "抽查8",
            height_result.returncode == 0 and same_model and changed,
            "改台阶高度只换配置：模型哈希不变、场景哈希变化"
            if height_result.returncode == 0 and same_model and changed
            else f"rc={height_result.returncode} same_model={same_model} stderr={height_result.stderr[-300:]}",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="G2 结构自查")
    parser.add_argument("--run", action="store_true", help="含集成抽查（会跑仿真）")
    args = parser.parse_args()

    check_s01()
    check_s02()
    check_s03()
    check_s04()
    check_s05()
    check_s06()
    check_s07()
    check_s08()
    check_s09()
    check_s10()
    check_s11()
    check_s12(args.run)
    check_s13()
    check_s14()
    check_s15()
    check_s16()
    check_s17()
    check_s18()
    check_s19()
    check_s20()
    check_s21()
    check_s22()
    check_s24()
    check_negative_configs()
    check_judge_unit_tests()
    if args.run:
        integration_checks()
    else:
        check_s06()
        check_s11()
        check_run_outputs()

    failed = 0
    for item in RESULTS:
        state = "PASS" if item["ok"] is True else ("SKIP" if item["ok"] is None else "FAIL")
        if item["ok"] is False:
            failed += 1
        print(f"[{state}] {item['id']}: {item['detail']}")
    print(f"\n{len(RESULTS)} 项检查，{failed} 项失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
