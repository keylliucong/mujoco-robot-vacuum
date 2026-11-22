"""MuJoCo 环境冒烟测试：加载最小模型、步进、确认接触求解可用。

在 Windows 项目目录执行：
    .venv\\Scripts\\python.exe scripts\\verify_env.py

接触力只用 ``mujoco.mj_contactForce`` 读取，不用 ``efc_force``：
金字塔锥下后者是棱边系数，不是力。不依赖外部模型文件，也不启动图形界面。
"""

import sys

import mujoco
import numpy as np

XML = """
<mujoco model="smoke">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.1"
          friction="1 0.01 0.01" condim="3"/>
    <body name="ball" pos="0 0 0.6">
      <joint type="free"/>
      <geom name="ball" type="sphere" size="0.1" rgba="0.8 0.2 0.2 1"
            friction="1 0.01 0.01" condim="3"/>
    </body>
  </worldbody>
</mujoco>
"""


def main() -> int:
    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)

    for _ in range(1000):
        mujoco.mj_step(model, data)

    res = np.zeros(6, dtype=np.float64)
    normals = []
    for i in range(data.ncon):
        mujoco.mj_contactForce(model, data, i, res)
        normals.append(abs(float(res[0])))
    max_normal = max(normals) if normals else 0.0
    ball_z = float(data.qpos[2])
    ok = data.ncon > 0 and max_normal > 0.0 and 0.05 < ball_z < 0.15

    print(f"Python:        {sys.version.split()[0]}")
    print(f"MuJoCo:        {mujoco.__version__}")
    print(f"NumPy:         {np.__version__}")
    print(f"Executable:    {sys.executable}")
    print(f"timestep:      {model.opt.timestep}")
    print(f"steps:         {data.time / model.opt.timestep:.0f}")
    print(f"active contacts (ncon): {data.ncon}")
    print(f"ball z:        {ball_z:.4f} m (expected ~0.1 m)")
    print(f"max contact normal (mj_contactForce): {max_normal:.3f} N")
    print("SMOKE TEST:", "OK" if ok else "NOT_OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
