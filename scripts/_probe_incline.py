"""Temporary probe: incline box creep vs contact stiffness. Not part of deliverable."""

import sys
import numpy as np
import mujoco


def build(dt, solref, solimp, noslip, integrator, angle_deg=30.0):
    angle = np.deg2rad(angle_deg)
    standoff = 0.102
    return mujoco.MjModel.from_xml_string(f"""
<mujoco model="probe">
  <option timestep="{dt}" gravity="0 0 -9.81" cone="pyramidal"
          solver="Newton" iterations="200" tolerance="1e-10"
          noslip_iterations="{noslip}" noslip_tolerance="1e-10"
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


def run(tag, dt, solref="0.02 1", solimp="0.9 0.95 0.001", noslip=0,
        integrator="Euler", sim_time=4.0):
    m = build(dt, solref, solimp, noslip, integrator)
    d = mujoco.MjData(m)
    n = int(sim_time / dt)
    for _ in range(n):
        mujoco.mj_step(m, d)
    # drift over last 0.2 s
    k = int(0.2 / dt)
    p0 = d.qpos[0:3].copy()
    for _ in range(k):
        mujoco.mj_step(m, d)
    drift = np.linalg.norm(d.qpos[0:3] - p0)
    lin = np.linalg.norm(d.qvel[0:3])
    ang = np.linalg.norm(d.qvel[3:6])
    frames = [np.array(d.contact[i].frame).reshape(3, 3)[0]
              for i in range(d.ncon) if d.contact[i].geom1 == 0 and d.contact[i].geom2 == 1]
    n_mean = np.mean(frames, axis=0)
    f = np.zeros(6)
    mujoco.mj_contactForce(m, d, 0, f)
    print(f"{tag:<28} dt={dt:<7} ncon={d.ncon} "
          f"v={lin:.3e} w={ang:.3e} drift200ms={drift*1000:.4f}mm "
          f"Fn0={f[0]:.6f} warn={int(np.count_nonzero(d.warning.number))}")


for tag, args in [
    ("A default", dict(dt=0.002)),
    ("B noslip100", dict(dt=0.002, noslip=100)),
    ("C solref5m noSl10", dict(dt=0.0005, solref="0.005 1", noslip=10)),
    ("D solref2m noSl100", dict(dt=0.0002, solref="0.002 1", noslip=100)),
    ("E solref2m implfast", dict(dt=0.0002, solref="0.002 1", noslip=10,
                                 integrator="implicitfast")),
    ("F solref5m implfast", dict(dt=0.002, solref="0.005 1", noslip=10,
                                 integrator="implicitfast")),
]:
    try:
        run(tag, **args)
    except Exception as exc:  # noqa: BLE001
        print(f"{tag:<28} ERROR {exc}")
