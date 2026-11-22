"""试跑专用批运行入口：复用 G2 的 run_cases.py，只换模型/台账与两处几何取值。

为什么需要这个包装层
--------------------
1. ``run_cases.py`` 把台账路径写死为 ``docs/参数溯源.csv``。G2 的台账实现
   （``model_checks.check_ledger_against_xml``）只按 xpath 的 ``:`` 后半段解析，
   不校验文件名，所以同一张台账里放 prototype 与 oomwoo 两套同名 param_id 会
   互相覆盖/比对失败。试跑因此用独立台账
   ``docs/试跑/参数溯源-oomwoo.csv``，并把路径注入本模块，不改上游脚本。
2. ``model_checks.body_length()`` 只认 ``chassis_*`` 的 **box** 几何；OOMWOO 是
   圆柱壳体，没有 box。``model_checks.chassis_min_z()`` 用包围球近似，对圆柱会
   给出远低于真实底面的值。两处都在这里做试跑级补丁，并在
   ``docs/试跑/oomwoo-全流程试跑.md`` 记录为流程缺口（应在 model_checks 内修）。

这两个补丁只影响观测/判据统计，不改变物理；判定仍然只在 judge.py。

OOMWOO 无被动悬挂：模型用 `<custom><numeric name="has_suspension" data="0"/>`
声明（契约 v1.8.0），不建 susp_L/R，输出 susp_*_travel_m 整列为空。

用法（Windows，项目 .venv）：
    .venv\\Scripts\\python.exe scripts\\run_oomwoo.py \
        --config cases\\oomwoo_flat.json --out outputs\\oomwoo-flat --repeat 2
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_cases  # noqa: E402

LEDGER = REPO_ROOT / "docs" / "试跑" / "参数溯源-oomwoo.csv"


def body_length(model) -> float:
    """chassis_* 几何在 x 方向的包围盒长度（圆柱按直径；box 按 2*半长）。"""
    lengths = []
    for gid in range(model.ngeom):
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        size = np.asarray(model.geom_size[gid], dtype=float)
        geom_type = model.geom_type[gid]
        if geom_type == mujoco.mjtGeom.mjGEOM_BOX:
            lengths.append(2 * float(size[0]))
        elif geom_type == mujoco.mjtGeom.mjGEOM_CYLINDER:
            lengths.append(2 * float(size[0]))
        elif geom_type == mujoco.mjtGeom.mjGEOM_SPHERE:
            lengths.append(2 * float(size[0]))
        elif geom_type == mujoco.mjtGeom.mjGEOM_CAPSULE:
            lengths.append(2 * (float(size[0]) + float(size[1])))
    if not lengths:
        raise run_cases.ContractError("chassis_* 中没有可求 x 向长度的几何")
    return max(lengths)


def chassis_min_z(model, data) -> float:
    """chassis_* 几何的实际下界（圆柱/球/盒按几何中心与半高，胶囊按包围球）。"""
    lows = []
    for gid in range(model.ngeom):
        name = model.geom(gid).name
        if not name.startswith("chassis_"):
            continue
        center_z = float(np.asarray(data.geom_xpos[gid], dtype=float)[2])
        size = np.asarray(model.geom_size[gid], dtype=float)
        geom_type = model.geom_type[gid]
        if geom_type == mujoco.mjtGeom.mjGEOM_CYLINDER:
            lows.append(center_z - float(size[1]))
        elif geom_type == mujoco.mjtGeom.mjGEOM_BOX:
            lows.append(center_z - float(size[2]))
        elif geom_type == mujoco.mjtGeom.mjGEOM_SPHERE:
            lows.append(center_z - float(size[0]))
        else:
            lows.append(center_z - float(model.geom_rbound[gid]))
    if not lows:
        raise run_cases.ContractError("chassis_* 中没有几何")
    return min(lows)


run_cases.LEDGER_PATH = LEDGER
run_cases.RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner_oomwoo.json"

run_cases.model_checks.body_length = body_length
run_cases.model_checks.chassis_min_z = chassis_min_z

if __name__ == "__main__":
    try:
        raise SystemExit(run_cases.main())
    except run_cases.ContractError as error:
        print(f"CONTRACT ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
