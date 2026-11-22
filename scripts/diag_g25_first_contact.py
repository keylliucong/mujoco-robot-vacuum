"""诊断：G2.5 台阶工况首次接触到底落在哪个 geom（前下缘还是壳体/轮）。

只读模型与 case，不写输出；用于报告里区分「首次接触来源」。
用法（Windows）：
    .venv\\Scripts\\python.exe scripts\\diag_g25_first_contact.py cases\\oomwoo_g25_step20.json
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_checks  # noqa: E402
import params_io  # noqa: E402
import run_cases  # noqa: E402
import run_oomwoo  # noqa: E402

run_cases.LEDGER_PATH = run_oomwoo.LEDGER
run_cases.RUNNER_DEFAULTS = run_oomwoo.RUNNER_DEFAULTS


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        raise SystemExit("usage: diag_g25_first_contact.py <case.json>")
    config = run_cases.load_case(argv[0])
    defaults = run_cases.load_runner_defaults()
    model_path = REPO_ROOT / config["model"]["path"]
    rendered = params_io.load_and_render(model_path)
    params_document = rendered["params"]
    model_text = rendered["text"]
    ledger = model_checks.load_ledger(run_oomwoo.LEDGER)
    base_model = mujoco.MjModel.from_xml_string(model_text)
    base_data = mujoco.MjData(base_model)
    mujoco.mj_forward(base_model, base_data)
    has_suspension = model_checks.read_capability(base_model, "has_suspension")
    chassis_front_m = run_cases.chassis_front(base_model)
    scenario = run_cases.build_scenario_xml(
        model_text, config, chassis_front_m, defaults, params_document
    )
    ET.fromstring(scenario)
    model = mujoco.MjModel.from_xml_string(scenario)
    overrides = []
    run_cases.apply_numerics(
        model, config["numerics"], config["numerics"]["timestep_s"], overrides
    )
    limits = run_cases.apply_torque_limits(model, config, overrides)
    data = mujoco.MjData(model)
    pair_lookup, ordered_pairs = run_cases.build_pair_lookup(
        config, config["scenario"]["kind"]
    )
    geom_names = run_cases.geom_name_table(model)
    friction_specs = run_cases.friction_expectations(
        config, config["scenario"]["kind"]
    )
    run_cases.reset_state(model, data)
    print(f"case={config['case_id']} timestep={model.opt.timestep:g} s")
    lip = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "chassis_front_lip")
    print(
        "chassis_front_lip: xpos={} rbound={:.6f} pos={}".format(
            np.round(np.asarray(data.geom_xpos[lip], dtype=float), 6).tolist(),
            float(model.geom_rbound[lip]),
            np.round(np.asarray(model.geom_pos[lip], dtype=float), 6).tolist(),
        )
    )
    step = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "obstacle")
    print("obstacle xpos={}".format(np.round(np.asarray(data.xpos[step], dtype=float), 6).tolist()))

    ramp_s = config["scenario"]["approach"]["settle_s"]
    speed = config["scenario"]["approach"]["speed_mps"]
    kp = defaults["drive"]["speed_kp_nm_per_mps"]
    yaw = defaults["drive"]["yaw_damping_nm_per_radps"]
    max_steps = int(round(defaults["time"]["max_sim_s"] / model.opt.timestep))
    for _ in range(max_steps):
        ramp = min(1.0, float(data.time) / ramp_s)
        run_cases.set_drive(model, data, limits, kp, speed, ramp, yaw)
        run_cases.step_once(model, data)
        hit = False
        for i in range(data.ncon):
            contact = data.contact[i]
            name1 = geom_names.get(int(contact.geom1))
            name2 = geom_names.get(int(contact.geom2))
            key = pair_lookup.get(frozenset((name1, name2)))
            if key is None or not key.endswith("--step"):
                continue
            spec = friction_specs.get(frozenset((name1, name2)))
            if spec is not None:
                run_cases.check_s24_contact(contact, spec, f"{name1}--{name2}")
            pos = np.asarray(data.contact[i].pos, dtype=float)
            friction = np.asarray(contact.friction, dtype=float)
            print(
                f"t={data.time:.4f}s FIRST {name1}--{name2} pair={key} "
                f"dim={int(contact.dim)} pos={np.round(pos, 6).tolist()} "
                f"friction={np.round(friction, 6).tolist()} dist={contact.dist:.6e}"
            )
            hit = True
        if hit:
            return 0
    print("no step contact")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
