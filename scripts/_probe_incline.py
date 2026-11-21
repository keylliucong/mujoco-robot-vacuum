"""Temporary probe: incline box creep vs contact stiffness (no noslip). Removed later."""

import numpy as np
import mujoco


def build(dt, solref, solimp, integrator="Euler", angle_deg=30.0):
    angle = np.deg2rad(angle_deg)
    standoff = 0.102
    return mujoco.MjModel.from_xml_string(f"""
<mujoco model="probe">
  <option timestep="{dt}" gravity="0 0 -9.81" cone="pyramidal"
          solver="Newton" iterations="200" tolerance="1e-10"
          integrator="{integrator}"/>
  <worldbody>
    <geom name="incline" type="plane" size="0 0 0.1" euler="0 {angle_deg} 0"
          friction="1 0.01 0.01" condim="3" solref="{solref}" solimp="{solimp}"/>
    <body name="block" pos="{np.sin(angle)*standoff} 0 {np.cos(angle)*standoff}"
          quat="{np.cos(angle/2)} 0 {np.sin(angle/2)} 0">
      <joint type="free"/>
      <geom name="block" type="box" size="0.1 0.1 0.1" density="1000"
            friction="1 0.01 0.01" condim="3" solref="{solref}" solimp="{solimp}"/>
    </body>
  </worldbody>
</mujoco>""")


def run(tag, dt, solref="0.02 1", solimp="0.9 0.95 0.001", integrator="Euler"):
    m = build(dt, solref, solimp, integrator)
    d = mujoco.MjData(m)
    for _ in range(int(1.0 / dt)):
        mujoco.mj_step(m, d)
    k = int(0.2 / dt)
    p0 = d.qpos[0:3].copy()
    for _ in range(k):
        mujoco.mj_step(m, d)
    drift = float(np.linalg.norm(d.qpos[0:3] - p0))
    lin = float(np.linalg.norm(d.qvel[0:3]))
    ang = float(np.linalg.norm(d.qvel[3:6]))
    print(f"{tag:<34} dt={dt:<8} ncon={d.ncon} v={lin:.3e} w={ang:.3e} "
          f"drift200ms={drift*1000:.4f}mm warn={int(np.count_nonzero(d.warning.number))}")


for tag, args in [
    ("K solref5m solimp.99", dict(dt=0.0005, solref="0.005 1",
                                 solimp="0.99 0.999 0.0001")),
    ("M solref2m solimp.99", dict(dt=0.0002, solref="0.002 1",
                                 solimp="0.99 0.999 0.0001")),
    ("N solref5m solimp.999", dict(dt=0.0005, solref="0.005 1",
                                  solimp="0.999 0.9999 0.0001")),
    ("O solref2m solimp.999", dict(dt=0.0002, solref="0.002 1",
                                  solimp="0.999 0.9999 0.0001")),
]:
    try:
        run(tag, **args)
    except Exception as exc:  # noqa: BLE001
        print(f"{tag:<34} ERROR {exc}")
