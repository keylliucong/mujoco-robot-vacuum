"""Capture base-tier poses from the existing OOMWOO runner and render them offline."""

import argparse
import json
import os
from pathlib import Path
import sys

import mujoco
from PIL import Image, ImageDraw, ImageFont


CASE = "oomwoo_step10_dt2ms"
FRAME_MS = 50
SAMPLE_S = 0.08


def capture(out):
    # The working directory is the unmodified Windows main checkout.
    sys.path.insert(0, str(Path.cwd() / "scripts"))
    from run_oomwoo import run_cases

    original_run = run_cases.run_case
    original_step = run_cases.step_once
    captured = []

    def observe_run(model, data, *args, **kwargs):
        if captured:
            return original_run(model, data, *args, **kwargs)
        poses = []
        next_sample = 0.0

        def observe_step(step_model, step_data):
            nonlocal next_sample
            original_step(step_model, step_data)
            if step_data.time >= next_sample - 1e-9:
                poses.append((float(step_data.time), step_data.qpos.copy()))
                next_sample += SAMPLE_S

        run_cases.step_once = observe_step
        try:
            result = original_run(model, data, *args, **kwargs)
        finally:
            run_cases.step_once = original_step
        poses.append((float(data.time), data.qpos.copy()))
        captured.append((model, poses))
        return result

    run_cases.run_case = observe_run
    try:
        result = run_cases.main(["--config", f"cases/{CASE}.json", "--out", str(out)])
    finally:
        run_cases.run_case = original_run
    if result or not captured:
        raise RuntimeError(f"Runner did not record the base tier (exit {result})")
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    return *captured[0], run


def render(out, model, poses, run):
    verdict = run["cases"][0]["repeats"][0]["tiers"][0]["verdict"]
    if verdict["status"] == "ok" and verdict["passed"]:
        crossing = verdict["metrics"]["crossing"]
        result = "PASSED"
        reason = f'crossed=true  |  end duty {crossing["end_duty"]:.0%}  |  advance {verdict["metrics"]["advance_m"]:.2f} m'
    elif verdict["status"] == "ok":
        result, reason = "BLOCKED", verdict["failure_primary"]
    else:
        result, reason = "INVALID", verdict["invalid_reason"]

    data = mujoco.MjData(model)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.azimuth = 83
    camera.elevation = -17
    camera.distance = 0.96
    colors = {
        "floor_plane": (0.76, 0.81, 0.85, 1.0),
        "step": (0.96, 0.63, 0.20, 1.0),
        "chassis_shell": (0.19, 0.57, 0.76, 0.78),
        "wheel_L_tire": (0.15, 0.22, 0.29, 1.0),
        "wheel_R_tire": (0.15, 0.22, 0.29, 1.0),
        "caster_wheel": (0.29, 0.37, 0.43, 1.0),
    }
    geometry_type = mujoco.mjtObj.mjOBJ_GEOM
    font = ImageFont.truetype(str(Path(os.environ["WINDIR"]) / "Fonts" / "arial.ttf"), 19)
    small = ImageFont.truetype(str(Path(os.environ["WINDIR"]) / "Fonts" / "arial.ttf"), 15)
    frames = []
    with mujoco.Renderer(model, height=320, width=640) as renderer:
        for index, (time, pose) in enumerate(poses):
            data.time = time
            data.qpos[:] = pose
            mujoco.mj_forward(model, data)
            x = float(data.body("chassis").xpos[0])
            camera.lookat[:] = (max(0.37, x + 0.10), 0.0, 0.06)
            renderer.update_scene(data, camera=camera)
            for geom in renderer.scene.geoms[:renderer.scene.ngeom]:
                if geom.objtype != geometry_type or geom.objid < 0:
                    continue
                name = model.geom(geom.objid).name
                if name in colors:
                    geom.rgba[:] = colors[name]
                    geom.emission = 0.58
            frame = Image.fromarray(renderer.render().copy())
            draw = ImageDraw.Draw(frame)
            draw.rectangle((0, 0, 640, 39), fill="#13232b")
            draw.text((16, 8), f"OOMWOO simulation   |   10 mm step   |   t = {time:05.2f} s",
                      font=font, fill="white")
            draw.rectangle((0, 265, 640, 320), fill="#13232b")
            final = index == len(poses) - 1
            draw.text((16, 271), f"Judge v{run['contract_version']}   |   {result if final else 'PENDING'}",
                      font=font, fill="#8ce4c2" if final else "white")
            draw.text((16, 296), reason if final else "Awaiting the full observation window   |   1.6x playback",
                      font=small, fill="white")
            frames.append(frame)

    duration_ms = [FRAME_MS] * (len(frames) - 1) + [850]
    if sum(duration_ms) > 10_000:
        raise ValueError("Animation would exceed 10 s")
    gif = out / "oomwoo-step10.gif"
    paletted = [frame.quantize(colors=96) for frame in frames]
    paletted[0].save(gif, save_all=True, append_images=paletted[1:], loop=0,
                     duration=duration_ms, optimize=True)
    if gif.stat().st_size >= 10_000_000:
        raise ValueError("Animation exceeds 10 MB")

    trigger = verdict["metrics"]["t_trigger_s"]
    drive_touch = verdict["metrics"]["t_wheel_touch_s"]
    key_times = (trigger - 0.65, trigger, drive_touch or trigger + 0.45, poses[-1][0])
    sheet = Image.new("RGB", (1280, 640))
    for index, moment in enumerate(key_times):
        closest = min(range(len(poses)), key=lambda k: abs(poses[k][0] - moment))
        sheet.paste(frames[closest], ((index % 2) * 640, (index // 2) * 320))
    sheet.save(out / "F8-step10-keyframes.png", dpi=(300, 300))
    print(json.dumps({"frames": len(frames), "duration_s": sum(duration_ms) / 1000,
                      "bytes": gif.stat().st_size, "result": result, "reason": reason}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    render(args.out.resolve(), *capture(args.out.resolve()))
