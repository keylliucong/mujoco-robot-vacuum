#!/usr/bin/env python
"""30° 斜面静置观测（试跑专用；G2 契约没有 slope 工况）。

为什么单独写
------------
契约 v1.7 的 ``scenario.kind`` 只有 ``flat`` / ``step``，runner/obstacle.py 只
注入水平地面与台阶；judge 的平地段还要求车身速度稳定在指令速度附近，静置斜面
必然判 ``invalid:data_invalid``（v1.8.1 起稳态不足并入 data_invalid）。所以斜面只能做**观测**，不能走 G2 判定。

物理等价
--------
把重力绕 +y 旋转 θ：``g = (g·sinθ, 0, -g·cosθ)``，机器人仍站在水平面上。
对刚体静力学这与把地面倾斜 θ 完全等价（法向载荷 mg·cosθ、切向 mg·sinθ），
且不需要改注入器。报告里把它记作“等效斜面”，不是几何斜面。

两个变体
--------
- ``free``：按模型原样，无驱动、无驻车。OOMWOO 的减速箱静摩擦/自锁未建模，
  预期会滚下去；这用来暴露“静置保持”缺哪一块物理。
- ``locked``：用 equality 把左右轮转角锁在 0，代表理想驻车/自锁。用来区分
  “轮地摩擦不够”与“传动系不会保持”。

判读只写观测：held / slid / invalid，不出通过结论。

用法
----
    python scripts/slope_hold.py --model models/oomwoo.xml --out outputs/slope30 --repeat 2
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import mujoco
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import params_io  # noqa: E402

GRAVITY = 9.81


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add_lock(text: str) -> str:
    root = ET.fromstring(text)
    equality = ET.SubElement(root, "equality")
    for name in ("wheel_L_spin", "wheel_R_spin", "caster_roll"):
        ET.SubElement(equality, "joint", {"joint1": name, "polycoef": "0 1 0 0 0"})
    return ET.tostring(root, encoding="unicode")


def build_model(model_text: str, angle_deg: float, timestep: float):
    model = mujoco.MjModel.from_xml_string(model_text)
    theta = math.radians(angle_deg)
    model.opt.gravity[:] = np.array([GRAVITY * math.sin(theta), 0.0, -GRAVITY * math.cos(theta)])
    model.opt.timestep = timestep
    return model


def run_once(model, duration_s: float):
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    start = np.array(data.body("chassis").xpos, dtype=float)
    rows = []
    steps = int(round(duration_s / model.opt.timestep))
    for _ in range(steps):
        # 无驱动；斜面静置不加减速器。
        mujoco.mj_step(model, data)
        mujoco.mj_forward(model, data)
        xpos = np.array(data.body("chassis").xpos, dtype=float)
        qvel = np.array(data.joint("chassis_free").qvel, dtype=float)
        rows.append(
            {
                "t_s": float(data.time),
                "pos_x_m": float(xpos[0]),
                "pos_y_m": float(xpos[1]),
                "pos_z_m": float(xpos[2]),
                "vel_x_mps": float(qvel[0]),
                "vel_y_mps": float(qvel[1]),
                "vel_z_mps": float(qvel[2]),
                "wheel_L_speed_radps": -float(np.asarray(data.joint("wheel_L_spin").qvel).reshape(-1)[0]),
                "wheel_R_speed_radps": -float(np.asarray(data.joint("wheel_R_spin").qvel).reshape(-1)[0]),
            }
        )
    end = np.array(data.body("chassis").xpos, dtype=float)
    tail = max(1, int(round(0.5 / model.opt.timestep)))
    residual = max(
        float(np.linalg.norm(np.array([r["vel_x_mps"], r["vel_y_mps"], r["vel_z_mps"]])))
        for r in rows[-tail:]
    )
    return {
        "rows": rows,
        "drift_m": float(np.linalg.norm(end - start)),
        "residual_speed_mps": residual,
        "start_m": start.tolist(),
        "end_m": end.tolist(),
    }


def outcome(run: dict, drift_redline: float, speed_redline: float) -> str:
    if not math.isfinite(run["drift_m"]) or not math.isfinite(run["residual_speed_mps"]):
        return "invalid"
    if run["drift_m"] > drift_redline or run["residual_speed_mps"] > speed_redline:
        return "slid"
    return "held"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="30° 等效斜面静置观测")
    parser.add_argument("--model", default="models/oomwoo.xml")
    parser.add_argument("--out", required=True)
    parser.add_argument("--angle-deg", type=float, default=30.0)
    parser.add_argument("--duration-s", type=float, default=10.0)
    parser.add_argument("--timestep-s", type=float, default=0.002)
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args(argv)

    model_path = (REPO_ROOT / args.model).resolve()
    rendered = params_io.load_and_render(model_path)
    base_text = rendered["text"]
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    if out_dir.exists():
        raise SystemExit(f"输出目录已存在，拒绝覆盖：{out_dir}")
    out_dir.mkdir(parents=True)

    variants = {"free": base_text, "locked": add_lock(base_text)}
    result = {
        "kind": "slope_hold",
        "method": "equivalent_gravity",
        "angle_deg": args.angle_deg,
        "gravity_mps2": [
            GRAVITY * math.sin(math.radians(args.angle_deg)),
            0.0,
            -GRAVITY * math.cos(math.radians(args.angle_deg)),
        ],
        "duration_s": args.duration_s,
        "timestep_s": args.timestep_s,
        "drive": "none",
        "model": {
            "path": str(model_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(model_path),
            "rendered_sha256": sha256_text(base_text),
            "params": str(rendered["params_path"].relative_to(REPO_ROOT)).replace("\\", "/"),
            "params_sha256": sha256_file(rendered["params_path"]),
        },
        "python": sys.version.split()[0],
        "mujoco": mujoco.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "variants": {},
    }

    for name, text in variants.items():
        runs = []
        for repeat in range(1, args.repeat + 1):
            model = build_model(text, args.angle_deg, args.timestep_s)
            run = run_once(model, args.duration_s)
            tag = name if args.repeat == 1 else f"{name}_r{repeat}"
            case_dir = out_dir / tag
            case_dir.mkdir(parents=True, exist_ok=True)
            with open(case_dir / "timeseries.csv", "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(run["rows"][0].keys()), lineterminator="\n")
                writer.writeheader()
                for row in run["rows"]:
                    writer.writerow({k: f"{v:.9f}" for k, v in row.items()})
            digest = hashlib.sha256((case_dir / "timeseries.csv").read_bytes()).hexdigest()
            runs.append(
                {
                    "repeat": repeat,
                    "dir": str(case_dir.relative_to(out_dir)).replace("\\", "/"),
                    "drift_m": run["drift_m"],
                    "residual_speed_mps": run["residual_speed_mps"],
                    "outcome": outcome(run, drift_redline=0.0005, speed_redline=0.001),
                    "timeseries_sha256": digest,
                }
            )
        raw_outcome = runs[0]["outcome"]
        invalid_reason = ""
        if raw_outcome == "slid" and name == "free":
            invalid_reason = "no_drivetrain_holding_model"
        elif raw_outcome == "slid" and name == "locked":
            # 锁轮后仍以 ~2 mm/s 匀速漂移：软接触/摩擦锥在持续切向载荷下的蠕滑，
            # 超过“无驱动 10 s 漂移 0.5 mm / 残余 1 mm/s”红线，不能当静置结论。
            invalid_reason = "creep_baseline_exceeded"
        result["variants"][name] = {
            "runs": runs,
            "consistent": len({r["timeseries_sha256"] for r in runs}) == 1,
            "outcome": "invalid" if invalid_reason else raw_outcome,
            "invalid_reason": invalid_reason,
            "raw_outcome": raw_outcome,
        }

    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (out_dir / "slope.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["variants"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
