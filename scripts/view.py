#!/usr/bin/env python
"""交互式 MuJoCo 查看器：工况 + 参数集 → 实时 HUD + 叠加层，不开截图、不改模型文件。

为什么单独一个入口
------------------
``scripts/run_cases.py`` 是批运行入口，跑完才出 CSV；看接触瞬间、看轮子是否真的
咬住台阶棱边，需要人在 MuJoCo viewer 里盯着看。本文件只做"看"，不改任何物理：

- 台阶仍由 ``run_cases.build_scenario_xml`` 注入（同一个函数，不另写一份）；
- 数值仍由 ``cases/*.json`` 的 ``numerics`` 与 ``params/<config_id>.json`` 注入；
- 判定仍由 ``judge.judge_case`` + ``run_cases.build_judge_params``（同一个判定函数）；
- 接触力仍按 G1 纸上签过的口径读取（见下）。

接触力口径（G1，违反即作废）
----------------------------
1. 只从 ``mujoco.mj_contactForce(model, data, i, res)`` 读，``res[0]`` 法向、``res[1:3]``
   切向，单位 N。**不用** ``efc_force`` 行相加当力。
2. ``data.contact[i].frame`` 是 3×3 行主序矩阵，三行依次为世界坐标下的法向与两个切向；
   ``res`` 在接触帧内，世界分量必须按 ``f_world = frame.T @ res[0:3]`` 旋转。
3. 正方向：力由 ``geom1`` 指向 ``geom2``，即**对 geom2 为正**；输出永远带 geom1/geom2 名称。

两种模式
--------
- ``--mode live``（默认）：按墙钟实时推进，``--speed 0.25/1/4`` 调速；
- ``--mode step``：暂停起跑，按空格一帧一帧推进（默认 1 个时间步 = 2 ms），
  用来看轮子刚碰到台阶棱边的那一下。

键盘：拖拽旋转 / 滚轮缩放 / 空格（live 暂停恢复、step 单步）/ Esc 退出。

用法（Mac，launch_passive 在 macOS 必须走 mjpython；``scripts/view.sh`` 已封装）::

    ./scripts/view.sh --case step_20mm --config oomwoo --speed 0.25
    ./scripts/view.sh --case flat --mode step

Windows 用 ``scripts\\view.bat``，参数一样。``--headless`` 只跑物理不开窗口，
用来在 CI/远端自检 HUD 与判定链路。
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge  # noqa: E402
import model_checks  # noqa: E402
import params_io  # noqa: E402
import run_cases  # noqa: E402

# 上游 run_cases 的默认口径（原型机 baseline.xml + docs/参数溯源.csv），
# 先存下来：下面 import run_oomwoo 会把这两项改成试跑口径。
PLAIN_LEDGER_PATH = run_cases.LEDGER_PATH
PLAIN_RUNNER_DEFAULTS = run_cases.RUNNER_DEFAULTS

import run_oomwoo  # noqa: E402  试跑级补丁：台账路径、runner 常量、圆柱底盘几何

OOMWOO_RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner_oomwoo.json"
_RUNNER_MACHINE = None

CONTACT_READOUT = (
    "mj_contactForce + contact.frame（G1：res 在接触帧内，世界分量 = frame.T @ res[0:3]，对 geom2 为正）"
)

# 工况预设：名字 → 仓库里已有的 case JSON（不新增、不修改 cases/）。
# step_30mm 没有现成 case，只在本进程内把 20 mm 的 obstacle.height_m 改掉，
# 再交给同一个 build_scenario_xml 注入，因此仍然只有一份台阶注入代码。
CASE_PRESETS = {
    "flat": {
        "case": "cases/oomwoo_flat.json",
        "help": "平地直行（工况 A，无台阶）",
    },
    "step_10mm": {
        "case": "cases/oomwoo_step10.json",
        "help": "正向台阶 10 mm（低于 12.5 mm 壳体离地）",
    },
    "step_20mm": {
        "case": "cases/oomwoo_step20_casterblock.json",
        "help": "正向台阶 20 mm（高于壳体离地，暴露未建模的壳体前下缘接触）",
    },
    "step_30mm": {
        "case": "cases/oomwoo_step20_casterblock.json",
        "height_m": 0.030,
        "help": "正向台阶 30 mm（由 20 mm case 在内存里改高度注入）",
    },
    "step_10mm_lowtorque": {
        "case": "cases/oomwoo_step10_lowtorque.json",
        "help": "10 mm + 限扭 0.15 N·m（预期失败算例）",
    },
    "oblique_30deg": {
        "case": "cases/step_oblique_plus30.json",
        "help": "斜向 30° 接近 20 mm 台阶（baseline 原型，proto_v1）",
    },
    "slope_30deg": {
        "case": "cases/oomwoo_flat.json",
        "slope_deg": 30.0,
        "help": "30° 等效斜面静置观测（slope_hold.py 口径，重力绕 +y 旋转，不驱动）",
    },
}

WHEEL_BODIES = ("wheel_L", "wheel_R", "caster_front")
CHASSIS_BODIES = ("chassis",)


class ViewError(RuntimeError):
    """查看器输入不合法（工况/参数集/模型不匹配）。"""


# ---------------------------------------------------------------- 工况与模型


def load_case(case_arg: str):
    """返回 (config, case_path, preset, label)。

    ``--case`` 既认预设名，也认直接给的 case JSON 路径。
    """
    preset = {}
    if case_arg in CASE_PRESETS:
        preset = dict(CASE_PRESETS[case_arg])
        case_path = (REPO_ROOT / preset["case"]).resolve()
        label = case_arg
    else:
        candidate = Path(case_arg)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.exists():
            known = ", ".join(sorted(CASE_PRESETS))
            raise ViewError(f"--case 不认 {case_arg!r}；可用预设：{known}；或给一个 case JSON 路径")
        case_path = candidate
        label = candidate.stem
    config = run_cases.load_case(case_path)  # 契约校验，与 runner 同一套
    height = preset.get("height_m")
    if height is not None:
        config["scenario"]["obstacle"]["height_m"] = float(height)
        if config["scenario"]["kind"] != "step":
            raise ViewError("height_m 覆盖只能用于 step 工况")
    return config, case_path, preset, label


def resolve_config_id(args_config, config):
    """参数集 ID：显式 --config 必须与 case 声明的 config_id 一致（S21）。"""
    declared = run_cases.parse_config_id(config)
    if args_config is None:
        return declared, (declared == "oomwoo")
    if args_config != declared:
        raise ViewError(
            f"--config {args_config} 与 case 声明的 config_id={declared} 不一致（S21）；"
            f"本工况请用 --config {declared}"
        )
    return args_config, True


def select_runner(machine):
    """按机型选 runner 口径。

    - machine=oomwoo：用试跑包装层 run_oomwoo 的补丁（独立台账、圆柱底盘几何、
      susp_range 占位），与 ``scripts/run_oomwoo.py`` 跑批时完全一致；
    - 其它机型：回到上游 ``scripts/run_cases.py`` 原样（原型机 baseline.xml +
      ``docs/参数溯源.csv``）。

    两种情况都靠 importlib.reload 复位共享模块，不在仓库里另存一份补丁。
    """
    global _RUNNER_MACHINE
    if _RUNNER_MACHINE == machine:
        return
    import importlib

    importlib.reload(model_checks)
    importlib.reload(run_cases)
    if machine == "oomwoo":
        importlib.reload(run_oomwoo)
    else:
        run_cases.LEDGER_PATH = PLAIN_LEDGER_PATH
        run_cases.RUNNER_DEFAULTS = PLAIN_RUNNER_DEFAULTS
    _RUNNER_MACHINE = machine


def load_model_stack(config, config_id, skip_checks):
    """按 runner 的顺序建模型：渲染参数 → 注入台阶/接触对 → 数值 → 限扭。"""
    model_rel = config["model"]["path"]
    model_path = (REPO_ROOT / model_rel).resolve()
    model_sha = run_cases.sha256_file(model_path)
    if model_sha != config["model"]["sha256"]:
        raise ViewError(f"模型 sha256 与 case 不符：{model_sha} != {config['model']['sha256']}")

    rendered = params_io.load_and_render(model_path)
    params_document = rendered["params"]
    if params_document["config_id"] != config_id:
        raise ViewError(
            f"参数集 {params_document['config_id']} != case 的 config_id={config_id}（S21）"
        )
    select_runner(params_document["machine"])
    model_text = rendered["text"]
    defaults = run_cases.load_runner_defaults()

    base_model = mujoco.MjModel.from_xml_string(model_text)
    base_data = mujoco.MjData(base_model)
    mujoco.mj_forward(base_model, base_data)

    ledger, _labels = run_cases.load_ledger_rows(params_document["machine"])
    if skip_checks:
        print("[view] 已跳过 A1–A5 与台账比对（--skip-checks）")
    else:
        import xml.etree.ElementTree as ET

        model_checks.run_checks(base_model, base_data, ledger, model_root=ET.fromstring(model_text))
        print("[view] 模型自检 A1–A5 + 台账比对：通过")

    run_cases.MODEL_CONSTANTS["wheel_radius_m"] = model_checks.ledger_value(
        ledger, "geom.wheel_radius_m"
    )
    run_cases.MODEL_CONSTANTS["susp_range_m"] = model_checks.ledger_value(
        ledger, "susp.travel_limit_m"
    )
    run_cases.MODEL_CONSTANTS["com_offset_B_m"] = model_checks.declared_com_offset(ledger)

    chassis_front_m = run_cases.chassis_front(base_model)
    scenario_xml = run_cases.build_scenario_xml(
        model_text, config, chassis_front_m, defaults, params_document
    )
    model = mujoco.MjModel.from_xml_string(scenario_xml)
    run_cases.apply_numerics(model, config["numerics"], config["numerics"]["timestep_s"], [])
    limits = run_cases.apply_torque_limits(model, config, [])
    data = mujoco.MjData(model)

    return {
        "model": model,
        "data": data,
        "base_model": base_model,
        "base_data": base_data,
        "defaults": defaults,
        "limits": limits,
        "params": params_document,
        "model_path": model_path,
        "model_sha": model_sha,
        "body_length_m": model_checks.body_length(base_model),
        "wheel_radius_m": run_cases.MODEL_CONSTANTS["wheel_radius_m"],
        "scenario_xml": scenario_xml,
    }


def floor_clearance_m(model, data, params_document):
    """壳体离地间隙：按模型静置时的 chassis_* 最低点算（OOMWOO = 12.5 mm）。

    几何算不出来时才退回参数集的 pos_z - half_height，再退回 0.0125 m，
    并在 HUD 里标明来源，避免把默认值当成实测。
    """
    try:
        return float(run_oomwoo.chassis_min_z(model, data)), "geom"
    except Exception:
        pass
    try:
        pos_z = float(params_io.get_param(params_document, "geom.chassis.pos_z")[1]["value"])
        half = float(
            params_io.get_param(params_document, "geom.chassis.half_height")[1]["value"]
        )
        return pos_z - half, "params"
    except (KeyError, TypeError, ValueError, params_io.ParamError):
        return 0.0125, "default"


# ------------------------------------------------------------------ 接触读数


def contact_forces(model, data):
    """按 G1 口径逐接触读力，返回世界量 + 接触帧 + geom1/geom2。

    每一项：
      {"geom1", "geom2", "frame"(3x3), "normal"(世界法向), "fn", "ft", "pos"(世界),
       "force_world"(geom2 受力的世界分量), "robot_body"(机器人侧 body 名或 "")}
    """
    out = []
    res = np.zeros(6, dtype=np.float64)
    for i in range(data.ncon):
        contact = data.contact[i]
        mujoco.mj_contactForce(model, data, i, res)
        frame = np.asarray(contact.frame, dtype=np.float64).reshape(3, 3)
        # res 在接触帧内，世界分量 = frame.T @ res[0:3]（G1 §5.2）
        force_world = frame.T @ np.asarray(res[0:3], dtype=np.float64)
        bodyids = []
        names = []
        for gid in (int(contact.geom1), int(contact.geom2)):
            bodyid = int(model.geom_bodyid[gid])
            bodyids.append(bodyid)
            names.append(model.body(bodyid).name if bodyid > 0 else "")
        robot_side = names[1] if bodyids[1] > 0 else names[0]
        out.append(
            {
                "index": i,
                "geom1": model.geom(int(contact.geom1)).name,
                "geom2": model.geom(int(contact.geom2)).name,
                "frame": frame,
                "normal": frame[0].copy(),
                "fn": float(res[0]),
                "ft": float(math.hypot(res[1], res[2])),
                "pos": np.asarray(contact.pos, dtype=np.float64).copy(),
                "force_world": force_world,
                "robot_body": robot_side,
            }
        )
    return out


def load_table(contacts):
    """按机器人侧 body 汇总 Fn / Ft / 接触数。"""
    table = {}
    for item in contacts:
        name = item["robot_body"]
        if not name:
            continue
        row = table.setdefault(name, {"fn": 0.0, "ft": 0.0, "count": 0})
        row["fn"] += item["fn"]
        row["ft"] += item["ft"]
        row["count"] += 1
    return table


def com_world(model, data):
    """整机质心（世界系）：只统计 chassis 运动树，不把注入的台阶 body 算进来。"""
    chassis_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    if chassis_id < 0:
        raise ViewError("模型缺 body chassis，无法算整机质心")
    masses = np.asarray(model.body_mass, dtype=np.float64)
    total = 0.0
    com = np.zeros(3)
    for bid in range(model.nbody):
        if masses[bid] == 0.0 or int(model.body_rootid[bid]) != chassis_id:
            continue
        total += masses[bid]
        com += masses[bid] * np.asarray(data.xipos[bid], dtype=np.float64)
    if total <= 0.0:
        raise ViewError("chassis 运动树质量为 0，无法算整机质心")
    return com / total


# ------------------------------------------------------------------ 会话状态


class Session:
    """一个工况的完整查看会话：物理、采样、HUD、判定。"""

    def __init__(self, args, config, case_path, preset, label):
        self.args = args
        self.config = config
        self.case_path = case_path
        self.preset = preset
        self.label = label
        self.slope_deg = preset.get("slope_deg")

        self.config_id, _ = resolve_config_id(args.config, config)
        stack = load_model_stack(config, self.config_id, args.skip_checks)
        self.model = stack["model"]
        self.data = stack["data"]
        self.defaults = stack["defaults"]
        self.limits = stack["limits"]
        self.params_document = stack["params"]
        self.body_length_m = stack["body_length_m"]
        self.wheel_radius_m = stack["wheel_radius_m"]

        self.clearance_m, self.clearance_source = floor_clearance_m(
            stack["base_model"], stack["base_data"], self.params_document
        )
        self.gravity = abs(
            float(params_io.get_param(self.params_document, "gravity.z")[1].get("value", -9.81))
        )
        kind = config["scenario"]["kind"]
        obstacle = config["scenario"].get("obstacle", {})
        self.step_height_m = float(obstacle.get("height_m", 0.0))
        self.kind = kind
        # 台阶高于壳体离地间隙且模型没有参数化前下缘时，才判"未覆盖此机理"。
        # G2.5 起 oomwoo.xml 带 chassis_front_lip，h > 12.5 mm 的接触机理已被建模。
        self.has_front_lip = any(
            self.model.geom(gid).name == "chassis_front_lip"
            for gid in range(self.model.ngeom)
        )
        self.unsupported = bool(
            self.step_height_m > self.clearance_m + 1e-12 and not self.has_front_lip
        )

        self.pair_lookup, self.ordered_pairs = run_cases.build_pair_lookup(config, kind)
        self.geom_names = run_cases.geom_name_table(self.model)
        self.columns = run_cases.make_columns(self.ordered_pairs)
        self.rows = []

        self.approach = config["scenario"]["approach"]
        self.window_s = float(config["judge"]["window_s"])
        self.speed_cmd = float(self.approach["speed_mps"])
        self.ramp_s = float(self.approach["settle_s"])
        self.cap_time = (
            self.approach["settle_s"]
            + self.approach["start_distance_m"] / self.speed_cmd
            + self.defaults["time"]["approach_margin_s"]
            + self.window_s
        )
        self.max_sim_s = float(args.max_sim_s or self.defaults["time"]["max_sim_s"])
        self.timestep = float(self.model.opt.timestep)

        self.trigger_time = None if kind == "step" else 0.0
        self.verdict = None
        self.verdict_at = -1.0
        self.max_fn = (0.0, "", -1.0)
        self.start_pos = None
        self.max_speed = 0.0
        self.finish_reason = ""
        self.paused = args.mode == "step"
        press_s = args.step_size_s if args.step_size_s and args.step_size_s > 0 else self.timestep
        self.steps_per_press = max(1, int(round(press_s / self.timestep)))

    # -- 物理 ---------------------------------------------------------

    def reset(self):
        run_cases.reset_state(self.model, self.data)
        if self.slope_deg is not None:
            theta = math.radians(self.slope_deg)
            self.model.opt.gravity[:] = np.array(
                [
                    self.gravity * math.sin(theta),
                    0.0,
                    -self.gravity * math.cos(theta),
                ]
            )
        mujoco.mj_forward(self.model, self.data)
        self.start_pos = np.asarray(self.data.body("chassis").xpos, dtype=np.float64).copy()

    def control(self):
        if self.slope_deg is not None:
            run_cases.zero_drive(self.data)  # 斜面静置观测，按 slope_hold 口径不驱动
            return
        ramp = min(1.0, float(self.data.time) / self.ramp_s)
        run_cases.set_drive(
            self.model,
            self.data,
            self.limits,
            self.defaults["drive"]["speed_kp_nm_per_mps"],
            self.speed_cmd,
            ramp,
            self.defaults["drive"]["yaw_damping_nm_per_radps"],
        )

    def advance(self):
        """推进一个时间步并采样；返回是否已经可以停。"""
        self.control()
        run_cases.step_once(self.model, self.data)
        row = run_cases.sample_row(
            self.model, self.data, self.pair_lookup, self.ordered_pairs, self.geom_names
        )
        self.rows.append(row)

        if self.trigger_time is None:
            for key in self.ordered_pairs:
                if key.startswith("wheel_") and key.endswith("--step"):
                    if row.get(f"contact_{key}_active") == 1:
                        self.trigger_time = row["t_s"]
                        break

        contacts = contact_forces(self.model, self.data)
        for item in contacts:
            if item["fn"] > self.max_fn[0]:
                self.max_fn = (
                    item["fn"],
                    f"{item['geom1']}→{item['geom2']}",
                    float(self.data.time),
                )

        # 全程最大机体线速度：斜面观测的红线用它与 drift 两个量（slope_hold 口径）
        qvel = np.asarray(self.data.joint("chassis_free").qvel, dtype=np.float64)
        self.max_speed = max(self.max_speed, float(np.linalg.norm(qvel[:3])))
        self.last_contacts = contacts
        return self.stop_reason()

    def stop_reason(self):
        t = float(self.data.time)
        if t >= self.max_sim_s - 1e-12:
            return "到达 max_sim_s"
        if self.slope_deg is not None and self.args.slope_max_drift > 0:
            if self.drift() >= self.args.slope_max_drift:
                return f"滚出可视范围（drift ≥ {self.args.slope_max_drift:g} m）"
        if self.trigger_time is None:
            return "未接触（到达时间上限）" if t >= self.cap_time else None
        return "判定窗口结束" if t >= self.trigger_time + self.window_s else None

    # -- 判定（复用 judge） --------------------------------------------

    def window_complete(self):
        if self.trigger_time is None:
            return False
        return float(self.data.time) >= self.trigger_time + self.window_s

    def evaluate(self, force=False):
        """跑 judge.judge_case（同一套判定），返回 verdict 或 None。"""
        if self.slope_deg is not None:
            return None  # 契约没有 slope 工况，judge 不适用
        if not (force or self.window_complete()):
            return None
        if len(self.rows) < 2:
            return None
        if not force and float(self.data.time) - self.verdict_at < 0.25:
            return self.verdict
        table = {
            column: [run_cases.format_value(row[column]) for row in self.rows]
            for column in self.columns
        }
        params = run_cases.build_judge_params(
            self.config,
            self.defaults,
            self.model,
            self.limits,
            self.ordered_pairs,
            self.body_length_m,
            self.wheel_radius_m,
        )
        try:
            self.verdict = judge.judge_case(table, params)
        except judge.JudgeError as error:
            self.verdict = {
                "status": "invalid",
                "invalid_reason": f"judge_error: {error}",
                "passed": None,
                "failure_primary": "",
                "failure_flags": [],
                "metrics": {},
            }
        self.verdict_at = float(self.data.time)
        return self.verdict

    def outcome(self):
        """cleared / blocked / invalid；不适用时给明原因，不给通过/失败结论。"""
        if self.slope_deg is not None:
            return "观测", "slope 无判定口径（judge 只覆盖 flat/step）"
        if self.unsupported:
            return "未覆盖此机理", (
                f"h={self.step_height_m * 1000:.1f} mm > 壳体离地 "
                f"{self.clearance_m * 1000:.1f} mm"
            )
        verdict = self.verdict
        if verdict is None:
            return "pending", "判定中，时程未跑满判定窗口"
        if verdict["status"] != "ok":
            return "invalid", verdict.get("invalid_reason") or "judge invalid"
        if verdict["passed"]:
            return "cleared", ""
        return "blocked", verdict.get("failure_primary") or "judge passed=False"

    # -- HUD ----------------------------------------------------------

    def hud_lines(self):
        data = self.data
        xpos = np.asarray(data.body("chassis").xpos, dtype=np.float64)
        qvel = np.asarray(data.joint("chassis_free").qvel, dtype=np.float64)
        pitch, roll, _yaw = model_checks.euler_zyx(
            np.asarray(data.body("chassis").xquat, dtype=np.float64)
        )
        com = com_world(self.model, data)
        clearance = run_oomwoo.chassis_min_z(self.model, data)
        contacts = getattr(self, "last_contacts", [])
        table = load_table(contacts)
        height = self.step_height_m

        lines = []
        lines.append(
            f"[{self.label}] t={data.time:6.2f} s  x={xpos[0]:7.4f} m  "
            f"v={qvel[0]:+6.3f} m/s  h={height * 1000:5.1f} mm  "
            f"mode={'step' if self.args.mode == 'step' else 'live'}"
            f"{'/paused' if self.paused else ''}  speed={self.args.speed:g}x"
        )
        for body in WHEEL_BODIES + CHASSIS_BODIES:
            row = table.get(body)
            if body in WHEEL_BODIES:
                if body == "caster_front":
                    label = "从动轮  "
                else:
                    label = f"驱动轮{body[-1]}"
                if row and row["count"]:
                    load = f"Fn={row['fn']:7.3f} N  Ft={row['ft']:6.3f} N  (n={row['count']})"
                else:
                    load = "Fn=—        Ft=—     (n=0 无接触)"
            else:
                label = "底盘壳体"
                if row and row["count"]:
                    load = f"Fn={row['fn']:7.3f} N  Ft={row['ft']:6.3f} N  (n={row['count']}) ← 托底"
                else:
                    load = "Fn=—        Ft=—     (n=0 无接触)"
            if body in WHEEL_BODIES and body != "caster_front":
                joint = f"{body}_spin"
                spin = float(np.asarray(data.joint(joint).qvel).reshape(-1)[0])
                torque = float(np.asarray(data.actuator(body).force).reshape(-1)[0])
                load += f"  ω={spin:+7.3f} rad/s  τ={torque:+6.3f} N·m"
            elif body == "caster_front":
                spin = float(np.asarray(data.joint("caster_roll").qvel).reshape(-1)[0])
                load += f"  ω={spin:+7.3f} rad/s"
            lines.append(f"  {label}: {load}")

        lines.append(
            f"  z_cg={com[2]:.4f} m  离地间隙={clearance * 1000:6.2f} mm   "
            f"pitch={math.degrees(pitch):+5.2f}°  roll={math.degrees(roll):+5.2f}°"
        )

        if contacts:
            pairs = {}
            for item in contacts:
                row = pairs.setdefault(
                    (item["geom1"], item["geom2"]),
                    {"fn": 0.0, "ft": 0.0, "n": 0, "normal": item["normal"]},
                )
                row["fn"] += item["fn"]
                row["ft"] += item["ft"]
                row["n"] += 1
            ordered = sorted(pairs.items(), key=lambda kv: -kv[1]["fn"])
            for (geom1, geom2), row in ordered[:4]:
                normal = row["normal"]
                lines.append(
                    f"  接触 {geom1}→{geom2}: Fn={row['fn']:+.3f} N  Ft={row['ft']:.3f} N  "
                    f"(n={row['n']})  n=[{normal[0]:+.2f} {normal[1]:+.2f} {normal[2]:+.2f}]"
                )
            lines.append("  （Fn 正方向：geom1→geom2，对 geom2 为正；世界分量 = frame.T @ res[0:3]）")
        else:
            lines.append("  接触：无")

        status, reason = self.outcome()
        if self.trigger_time is None and self.kind == "step":
            window = "等待轮-台阶接触"
        elif self.window_complete():
            window = "窗口已满"
        else:
            remain = max(0.0, self.trigger_time + self.window_s - float(data.time))
            window = f"窗口剩 {remain:4.1f} s"
        lines.append(f"  状态: {status}{('（' + reason + '）') if reason else ''}   {window}")

        if self.unsupported:
            lines.append(
                f"  ⚠ h > {self.clearance_m * 1000:.1f} mm："
                "本模型未覆盖壳体前下缘接触，结果不代表通过能力"
            )
        return lines

    def hud_text(self):
        return "\n".join(self.hud_lines())

    # -- 阻滑基线 ------------------------------------------------------

    def creep_baseline(self):
        """复用 runner 的静置蠕滑基线（同一函数、同一红线）。"""
        creep_data = mujoco.MjData(self.model)
        return run_cases.run_creep(
            self.model, creep_data, self.defaults, self.wheel_radius_m
        )

    # -- 结束 ---------------------------------------------------------

    def summary_lines(self, wall_s):
        verdict = self.verdict
        status, reason = self.outcome()
        lines = ["", "===== 查看摘要 ====="]
        lines.append(
            f"工况: {self.label}（{self.case_path.relative_to(REPO_ROOT)}）  "
            f"参数集: {self.config_id}  模式: {self.args.mode}  speed={self.args.speed:g}x"
        )
        lines.append(
            f"时长: 仿真 {self.data.time:.3f} s / 墙钟 {wall_s:.1f} s"
            f"（{len(self.rows)} 个采样步，dt={self.timestep * 1000:g} ms）"
        )
        if self.unsupported:
            lines.append(
                f"最终 outcome: 未覆盖此机理（h={self.step_height_m * 1000:.1f} mm > "
                f"壳体离地 {self.clearance_m * 1000:.1f} mm；"
                "本模型未覆盖壳体前下缘接触，结果不代表通过能力）"
            )
        else:
            lines.append(f"最终 outcome: {status}{('（' + reason + '）') if reason else ''}")
        if verdict is not None:
            judge_label = "judge（原始读数，不作结论）" if self.unsupported else "judge"
            lines.append(
                f"{judge_label}: status={verdict['status']} passed={verdict['passed']} "
                f"primary={verdict['failure_primary'] or '-'} "
                f"flags={';'.join(verdict['failure_flags']) or '-'}"
            )
            metrics = verdict.get("metrics") or {}
            if verdict["status"] == "ok":
                lines.append(
                    f"  t_trigger={fmt(metrics.get('t_trigger_s'))} s  "
                    f"t_climb={fmt(metrics.get('t_climb_s'))} s  "
                    f"advance={fmt(metrics.get('advance_m'))} m  "
                    f"pitch_max={fmt(metrics.get('pitch_max_deg'))} °  "
                    f"slip_max={fmt(max(metrics.get('slip_max_L') or 0.0, metrics.get('slip_max_R') or 0.0))}"
                )
        if self.max_fn[0] > 0.0:
            lines.append(
                f"最大 Fn: {self.max_fn[0]:.3f} N（{self.max_fn[1]}，t={self.max_fn[2]:.2f} s，"
                "正方向=对 geom2）"
            )
        else:
            lines.append("最大 Fn: 全程无接触（—）")

        if self.slope_deg is not None:
            drift = self.drift()
            hit = drift > 0.0005 or self.max_speed > 0.001
            lines.append(
                f"蠕滑红线: {'触发' if hit else '未触发'}（斜面静置口径 drift={drift * 1000:.4f} mm，"
                f"全程最大速度={self.max_speed * 1000:.3f} mm/s，红线 0.5 mm / 1 mm/s）"
            )
        else:
            creep = getattr(self, "creep", None)
            if creep is None:
                lines.append("蠕滑红线: 未测（--no-creep）")
            else:
                lines.append(
                    f"蠕滑红线: {'触发' if creep['redline'] else '未触发'}"
                    f"（静置 drift={creep['drift_m'] * 1000:.4f} mm，"
                    f"残余速度={creep['residual_speed_mps'] * 1000:.4f} mm/s，"
                    f"红线 {creep['max_drift_m'] * 1000:.1f} mm / "
                    f"{creep['max_residual_speed_mps'] * 1000:.1f} mm/s）"
                )
        lines.append(f"接触力读数: {CONTACT_READOUT}")
        if self.finish_reason:
            lines.append(f"停止原因: {self.finish_reason}")
        return lines

    def drift(self):
        if self.start_pos is None:
            return 0.0
        end = np.asarray(self.data.body("chassis").xpos, dtype=np.float64)
        return float(np.linalg.norm(end - self.start_pos))


def fmt(value):
    if value is None:
        return "—"
    return f"{value:.4g}"


# ------------------------------------------------------------------ 叠加层


def draw_overlay(scn, session):
    """把质心、接触法向、前进方向画进 user_scn（不改模型、不写文件）。"""
    scn.ngeom = 0
    model, data = session.model, session.data
    data_id = np.eye(3).reshape(9)

    def add(geom_type, size, pos, mat, rgba):
        if scn.ngeom >= scn.maxgeom:
            return None
        geom = scn.geoms[scn.ngeom]
        mujoco.mjv_initGeom(
            geom,
            geom_type,
            np.asarray(size, dtype=np.float64),
            np.asarray(pos, dtype=np.float64),
            np.asarray(mat, dtype=np.float64).reshape(9),
            np.asarray(rgba, dtype=np.float32),
        )
        scn.ngeom += 1
        return geom

    def add_arrow(start, vector, rgba, width=0.004):
        geom = add(mujoco.mjtGeom.mjGEOM_ARROW, np.zeros(3), np.zeros(3), data_id, rgba)
        if geom is not None:
            mujoco.mjv_connector(
                geom,
                mujoco.mjtGeom.mjGEOM_ARROW,
                width,
                np.asarray(start, dtype=np.float64),
                np.asarray(start, dtype=np.float64) + np.asarray(vector, dtype=np.float64),
            )

    def add_line(start, end, rgba, width=2.0):
        geom = add(mujoco.mjtGeom.mjGEOM_LINE, np.zeros(3), np.zeros(3), data_id, rgba)
        if geom is not None:
            mujoco.mjv_connector(
                geom,
                mujoco.mjtGeom.mjGEOM_LINE,
                width,
                np.asarray(start, dtype=np.float64),
                np.asarray(end, dtype=np.float64),
            )

    # ① 质心小球 + 竖直投影线
    com = com_world(model, data)
    add(
        mujoco.mjtGeom.mjGEOM_SPHERE,
        np.array([0.008, 0.008, 0.008]),
        com,
        data_id,
        [1.0, 0.15, 0.15, 1.0],
    )
    add_line(com, np.array([com[0], com[1], 0.0]), [1.0, 0.15, 0.15, 0.8])

    # ② 每个接触点一条沿法向的箭头，长度按 Fn 归一化（—fn-ref 为满量程）
    contacts = getattr(session, "last_contacts", [])
    max_len = 0.05
    for item in contacts:
        ratio = min(1.0, abs(item["fn"]) / max(session.args.fn_ref, 1e-9))
        length = max(0.008, max_len * ratio)
        add_arrow(
            item["pos"],
            item["normal"] * length,
            [0.1, 0.9, 1.0, 1.0] if item["fn"] >= 0.0 else [1.0, 0.6, 0.1, 1.0],
        )

    # ③ 整机前进方向（机体系 +x）
    xmat = np.asarray(data.body("chassis").xmat, dtype=np.float64).reshape(3, 3)
    origin = np.asarray(data.body("chassis").xpos, dtype=np.float64) + xmat[:, 0] * 0.05
    add_arrow(origin, xmat[:, 0] * 0.12, [0.2, 1.0, 0.2, 1.0], width=0.006)


# ------------------------------------------------------------------ 主循环


def _is_mjpython():
    try:
        return getattr(mujoco.viewer, "_MJPYTHON", None) is not None
    except Exception:
        return False


def run_headless(session):
    """不开窗口跑完整工况：HUD/判定/摘要链路的自检入口。"""
    started = time.perf_counter()
    session.reset()
    session.last_contacts = []
    next_hud = 0.0
    print(session.hud_text())
    next_hud = float(session.data.time) + session.args.hud_interval
    while True:
        reason = session.advance()
        if session.data.time >= next_hud:
            print(session.hud_text())
            next_hud = session.data.time + session.args.hud_interval
        if reason:
            session.finish_reason = reason
            break
    session.evaluate(force=True)
    print("\n".join(session.summary_lines(time.perf_counter() - started)))
    return 0


def run_viewer(session):
    import mujoco.viewer

    handle_state = {"step": 0, "toggle": 0}

    def key_callback(keycode):
        if keycode == 32:  # 空格
            if session.args.mode == "step":
                handle_state["step"] += session.steps_per_press
            else:
                handle_state["toggle"] += 1
        elif keycode in (112, 80):  # p / P
            handle_state["toggle"] += 1

    started = time.perf_counter()
    session.reset()
    session.last_contacts = []
    overlay_ok = True
    finished = False
    finish_reported = False
    next_hud = 0.0
    next_eval = 0.0
    next_panel = 0.0
    print(session.hud_text())
    print("[view] 拖拽旋转 / 滚轮缩放 / 空格（live 暂停、step 单步）/ Esc 退出")
    next_hud = float(session.data.time) + session.args.hud_interval

    with mujoco.viewer.launch_passive(session.model, session.data, key_callback=key_callback) as viewer:
        sim_origin = float(session.data.time)
        wall_origin = time.perf_counter()

        while viewer.is_running():
            if session.args.exit_after_s > 0 and time.perf_counter() - wall_origin >= session.args.exit_after_s:
                print(f"[view] 到达 --exit-after-s {session.args.exit_after_s:g} s，自动退出")
                viewer.close()
                break
            if finished:
                viewer.sync()
                time.sleep(0.05)
                continue

            if handle_state["toggle"]:
                handle_state["toggle"] = 0
                session.paused = not session.paused
                # 暂停期间墙钟照走，恢复时重新对齐，避免追帧暴冲
                sim_origin = float(session.data.time)
                wall_origin = time.perf_counter()

            advanced = 0
            if session.args.mode == "live" and not session.paused:
                target = sim_origin + (time.perf_counter() - wall_origin) * session.args.speed
                burst = 0
                while float(session.data.time) < target and burst < 500:
                    reason = session.advance()
                    advanced += 1
                    burst += 1
                    if reason:
                        session.finish_reason = reason
                        finished = True
                        break
                if advanced == 0:
                    time.sleep(0.002)
            elif handle_state["step"]:
                budget = handle_state["step"]
                handle_state["step"] = 0
                for _ in range(budget):
                    reason = session.advance()
                    advanced += 1
                    if reason:
                        session.finish_reason = reason
                        finished = True
                        break
            else:
                time.sleep(0.01)

            if session.data.time >= next_hud:
                print(session.hud_text())
                next_hud = float(session.data.time) + session.args.hud_interval

            if not finished and session.data.time >= next_eval:
                verdict = session.evaluate()
                if verdict is not None:
                    next_eval = float(session.data.time) + 0.5

            if finished and session.verdict is None:
                session.evaluate(force=True)

            if finished and not finish_reported:
                finish_reported = True
                status, reason = session.outcome()
                print(
                    f"[view] 运行结束（{session.finish_reason}）：outcome={status}"
                    f"{('（' + reason + '）') if reason else ''}；"
                    "窗口保持开启，按 Esc 退出看完整摘要"
                )

            with viewer.lock():
                if session.slope_deg is not None:
                    # 斜面工况车会一直滚，镜头跟着走，否则两秒就出画
                    chassis = np.asarray(session.data.body("chassis").xpos, dtype=np.float64)
                    viewer.cam.lookat[:] = chassis
                if overlay_ok:
                    try:
                        draw_overlay(viewer.user_scn, session)
                    except Exception as error:  # 叠加层只是显示，坏了不影响读数
                        overlay_ok = False
                        print(f"[view] 叠加层已停用：{error}")

            # 面板文字单独调用（set_texts 内部自己加锁，套在 viewer.lock() 里会卡死），
            # 按墙钟节流：step 模式暂停时仿真时间不走，用仿真时间会一直不刷新
            if next_panel <= time.perf_counter():
                next_panel = time.perf_counter() + 0.2
                if overlay_ok:
                    try:
                        viewer.set_texts(
                            (
                                mujoco.mjtFontScale.mjFONTSCALE_100,
                                mujoco.mjtGridPos.mjGRID_TOPRIGHT,
                                session.hud_text(),
                                "",
                            )
                        )
                    except Exception:
                        overlay_ok = False
            viewer.sync()

    if session.verdict is None:
        session.evaluate(force=True)
    print("\n".join(session.summary_lines(time.perf_counter() - started)))
    return 0


def parse_args(argv):
    presets = "\n".join(f"  {name:<22}{spec['help']}" for name, spec in CASE_PRESETS.items())
    parser = argparse.ArgumentParser(
        description="交互式查看 OOMWOO 越障仿真（实时 HUD + 叠加层）",
        epilog="可用工况预设：\n" + presets,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--case", default="flat", help="工况预设名或 case JSON 路径（默认 flat）")
    parser.add_argument(
        "--config",
        default=None,
        help="参数集 ID（默认跟随 case 声明的 config_id，OOMWOO 工况即 oomwoo）",
    )
    parser.add_argument("--mode", choices=("live", "step"), default="live", help="live 实时 / step 单步")
    parser.add_argument("--speed", type=float, default=1.0, help="live 模式倍速：0.25 / 1 / 4")
    parser.add_argument(
        "--step-size-s", type=float, default=None, help="step 模式每按一次空格推进的仿真秒数（默认 1 个时间步）"
    )
    parser.add_argument("--hud-interval", type=float, default=0.5, help="终端 HUD 间隔（仿真秒，默认 0.5）")
    parser.add_argument("--fn-ref", type=float, default=20.0, help="法向箭头满量程（N，默认 20）")
    parser.add_argument("--max-sim-s", type=float, default=None, help="最长仿真时长（默认取 runner 的 40 s）")
    parser.add_argument("--headless", type=float, default=None, metavar="SECONDS", help="不开窗口跑指定仿真秒数后退出（自检用）")
    parser.add_argument(
        "--exit-after-s",
        type=float,
        default=0.0,
        help="墙钟秒数到就自动退出（0 = 不自动退出；自检/录屏用）",
    )
    parser.add_argument("--skip-checks", action="store_true", help="跳过 A1–A5 模型自检")
    parser.add_argument("--no-creep", action="store_true", help="跳过静置蠕滑基线")
    parser.add_argument(
        "--slope-max-drift",
        type=float,
        default=1.0,
        help="斜面观测的位移上限（m，默认 1.0；0 = 不限，滚出镜头也继续跑）",
    )
    args = parser.parse_args(argv)
    if args.speed <= 0:
        parser.error("--speed 必须 > 0")
    if args.step_size_s is None:
        args.step_size_s = 0.0  # 0 = 交给 Session 换成 1 个时间步
    if args.headless is not None:
        args.max_sim_s = float(args.headless)
    return args


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)

    if args.headless is None and sys.platform == "darwin" and not _is_mjpython():
        print(
            "macOS 上 mujoco.viewer.launch_passive 必须用 mjpython 启动：\n"
            "  .venv/bin/mjpython scripts/view.py ...\n"
            "  或直接用 ./scripts/view.sh（已自动选解释器）",
            file=sys.stderr,
        )
        return 2

    config, case_path, preset, label = load_case(args.case)
    session = Session(args, config, case_path, preset, label)
    print(
        f"[view] 工况 {session.label} | case={case_path.relative_to(REPO_ROOT)} | "
        f"config={session.config_id}（{session.params_document['machine']}）"
    )
    print(
        f"[view] 模型 {config['model']['path']} | timestep={session.timestep * 1000:g} ms | "
        f"integrator={config['numerics']['integrator']} | solver={config['numerics']['solver']} | "
        f"cone={config['numerics']['cone']} | 壳体离地={session.clearance_m * 1000:.1f} mm"
        f"{'（默认值）' if session.clearance_source == 'default' else ''}"
    )
    if session.unsupported:
        print(
            f"[view] ⚠ h={session.step_height_m * 1000:.1f} mm > {session.clearance_m * 1000:.1f} mm："
            "本模型未覆盖壳体前下缘接触，outcome 显示「未覆盖此机理」"
        )

    if not args.no_creep and session.slope_deg is None:
        session.creep = session.creep_baseline()
        print(
            f"[view] 静置蠕滑基线：drift={session.creep['drift_m'] * 1000:.4f} mm，"
            f"残余速度={session.creep['residual_speed_mps'] * 1000:.4f} mm/s，"
            f"红线={'触发' if session.creep['redline'] else '未触发'}"
        )

    try:
        if args.headless is not None:
            return run_headless(session)
        return run_viewer(session)
    except KeyboardInterrupt:
        session.evaluate(force=True)
        print("\n".join(session.summary_lines(0.0)))
        return 130


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        ViewError,
        run_cases.ContractError,
        params_io.ParamError,
        model_checks.ModelCheckError,
    ) as error:
        print(f"VIEW ERROR: {error}", file=sys.stderr)
        print("（工况/参数集/模型不匹配一律拒绝运行，不静默降级；见 docs/使用/启动Viewer看仿真.md）", file=sys.stderr)
        raise SystemExit(2)
