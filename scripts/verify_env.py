"""MuJoCo 接触力读数校验：球静置在平面上，用法向力与球重对照（误差限 1%）。

在 Windows 项目目录执行：
    .venv\\Scripts\\python.exe scripts\\verify_env.py

脚本做三件事：
1. 打印实际使用的 Python / MuJoCo / NumPy / 解释器，以及时间步、求解器、
   摩擦锥、condim、摩擦系数，便于复现。
2. 对 mjCONE_PYRAMIDAL 与 mjCONE_ELLIPTIC 各跑一次球静置场景。
3. 用 mujoco.mj_contactForce 读取接触坐标系下的六维力，取第 0 分量为法向力，
   与 m*g 对照；同时打印接触坐标系与法向方向，用来确认单位和正方向。

不依赖外部模型文件，也不启动图形界面。全部输出为 ASCII，便于 Windows 重定向。
"""

import sys

import mujoco
import numpy as np

RADIUS = 0.1          # m
DENSITY = 1000.0      # kg/m^3（MuJoCo 默认值，这里显式写出）
GRAVITY = 9.81        # m/s^2
TIMESTEP = 0.002      # s
DROP_HEIGHT = 0.6     # m（球心初始高度）
SETTLE_MAX_STEPS = 5000
SAMPLE_STEPS = 100
ERROR_LIMIT = 0.01    # 1%

XML = """
<mujoco model="contact-force-check">
  <option timestep="{timestep}" gravity="0 0 -{gravity}" cone="{cone}"
          solver="Newton" iterations="100" tolerance="1e-10"/>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.1"
          friction="1 0.01 0.01" condim="3"/>
    <body name="ball" pos="0 0 {drop}">
      <joint type="free"/>
      <geom name="ball" type="sphere" size="{radius}" density="{density}"
            friction="1 0.01 0.01" condim="3"/>
    </body>
  </worldbody>
</mujoco>
"""

CONES = (
    ("pyramidal", mujoco.mjtCone.mjCONE_PYRAMIDAL),
    ("elliptic", mujoco.mjtCone.mjCONE_ELLIPTIC),
)


def build_model(cone_name: str) -> mujoco.MjModel:
    return mujoco.MjModel.from_xml_string(
        XML.format(
            timestep=TIMESTEP,
            gravity=GRAVITY,
            cone=cone_name,
            drop=DROP_HEIGHT,
            radius=RADIUS,
            density=DENSITY,
        )
    )


def find_floor_ball_contact(model: mujoco.MjModel, data: mujoco.MjData) -> int:
    floor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    ball_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ball")
    for i in range(data.ncon):
        pair = {data.contact[i].geom1, data.contact[i].geom2}
        if pair == {floor_id, ball_id}:
            return i
    raise RuntimeError("no floor-ball contact found")


def run_cone(cone_name: str, expected_cone: int, expected_mass: float) -> bool:
    model = build_model(cone_name)
    data = mujoco.MjData(model)
    ball_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "ball")
    floor_geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    ball_geom = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "ball")
    mass = float(model.body_mass[ball_body])
    weight = mass * GRAVITY

    # 自由落体并静置；用连续若干步的低速作为收敛条件。
    quiet_steps = 0
    settle_steps = 0
    for _ in range(SETTLE_MAX_STEPS):
        mujoco.mj_step(model, data)
        settle_steps += 1
        quiet = abs(float(data.qvel[2])) < 1e-4 and abs(float(data.qpos[2]) - RADIUS) < 1e-4
        quiet_steps = quiet_steps + 1 if quiet else 0
        if quiet_steps >= 50:
            break
    if data.ncon != 1:
        raise RuntimeError(f"expected 1 contact after settling, got {data.ncon}")

    # 逐帧用 mj_contactForce 读取接触坐标系下的力，取样本统计。
    samples = np.zeros((SAMPLE_STEPS, 6))
    heights = np.zeros(SAMPLE_STEPS)
    normals = np.zeros((SAMPLE_STEPS, 3))
    for k in range(SAMPLE_STEPS):
        mujoco.mj_step(model, data)
        cid = find_floor_ball_contact(model, data)
        force = np.zeros(6)
        mujoco.mj_contactForce(model, data, cid, force)
        samples[k] = force
        heights[k] = float(data.qpos[2])
        normals[k] = np.array(data.contact[cid].frame[0:3])
    normal_forces = samples[:, 0]
    tangential_forces = np.linalg.norm(samples[:, 1:3], axis=1)
    mean_normal = float(normal_forces.mean())
    error = (mean_normal - weight) / weight
    normal_axis = normals.mean(axis=0)

    print()
    print(f"--- cone = {cone_name} (mjCONE_{cone_name.upper()}={expected_cone}) ---")
    print(f"model.opt.cone:            {int(model.opt.cone)} (expected {expected_cone})")
    print(f"model.opt.solver:          {mujoco.mjtSolver(model.opt.solver).name}"
          f" ({model.opt.solver})")
    print(f"model.opt.timestep:        {model.opt.timestep} s")
    print(f"condim floor/ball:         {model.geom_condim[floor_geom]}/"
          f"{model.geom_condim[ball_geom]}")
    print(f"friction floor/ball:       {np.round(model.geom_friction[floor_geom], 4).tolist()}/"
          f"{np.round(model.geom_friction[ball_geom], 4).tolist()}")
    print(f"settle steps:              {settle_steps}")
    print(f"sample steps:              {SAMPLE_STEPS}")
    print(f"mass (model.body_mass):    {mass:.6f} kg")
    print(f"mass (density*volume):     {expected_mass:.6f} kg")
    print(f"m*g:                       {weight:.6f} N")
    print(f"mean normal force [0]:     {mean_normal:.6f} N")
    print(f"min/max normal force:      {normal_forces.min():.6f} / {normal_forces.max():.6f} N")
    print(f"normal force std:          {normal_forces.std():.6f} N")
    print(f"mean tangential force:     {tangential_forces.mean():.6f} N "
          f"(max {tangential_forces.max():.6f} N)")
    print(f"contact frame normal:      [{normal_axis[0]: .6f} {normal_axis[1]: .6f} "
          f"{normal_axis[2]: .6f}]")
    print(f"ball z (mean):             {heights.mean():.6f} m")
    print(f"error vs m*g:              {error * 100:+.4f} %")
    ok = (
        int(model.opt.cone) == expected_cone
        and abs(error) <= ERROR_LIMIT
        and normal_axis[2] > 0.999
        and tangential_forces.mean() < 0.01 * weight
    )
    print(f"RESULT:                    {'PASS' if ok else 'FAIL'} "
          f"(limit {ERROR_LIMIT * 100:.0f}%)")
    return ok


def main() -> int:
    volume = 4.0 / 3.0 * np.pi * RADIUS ** 3
    expected_mass = DENSITY * volume
    print("=== MuJoCo contact force readout check ===")
    print(f"Python:                    {sys.version.split()[0]}")
    print(f"MuJoCo:                    {mujoco.__version__}")
    print(f"NumPy:                     {np.__version__}")
    print(f"Executable:                {sys.executable}")
    print(f"scene:                     sphere r={RADIUS} m, density={DENSITY} kg/m^3, "
          f"drop from z={DROP_HEIGHT} m onto plane")
    print(f"gravity:                   {GRAVITY} m/s^2")
    print(f"error limit:               {ERROR_LIMIT * 100:.0f}% of m*g")
    print("force source:              mujoco.mj_contactForce (contact frame, "
          "component 0 = normal)")

    results = [run_cone(name, enum_value, expected_mass) for name, enum_value in CONES]
    print()
    print("CONTACT FORCE CHECK:", "PASS" if all(results) else "FAIL")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
