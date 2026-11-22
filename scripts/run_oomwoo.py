"""试跑专用批运行入口：复用 G2 的 run_cases.py，只换台账/runner 默认路径。

为什么需要这个包装层
--------------------
1. ``run_cases.py`` 把台账路径写死为 ``docs/参数溯源.csv``。G2 的台账实现
   （``model_checks.check_ledger_against_xml``）只按 xpath 的 ``:`` 后半段解析，
   不校验文件名，所以同一张台账里放 prototype 与 oomwoo 两套同名 param_id 会
   互相覆盖/比对失败。试跑因此用独立台账
   ``docs/试跑/参数溯源-oomwoo.csv``，并把路径注入本模块，不改上游脚本。
2. OOMWOO 的 runner 常量单独放在 ``cases/_runner_oomwoo.json``，本模块只切换
   该路径。

几何观测（``body_length()`` / ``chassis_min_z()``）已修回 ``model_checks``
（box / cylinder / sphere / capsule / ellipsoid 统一按几何与姿态取支撑），
wrapper 不再分叉。

剩余补丁：OOMWOO 的 susp_L/R 是 ±1 µm 占位铰，``susp_range_m`` 置 1 m 只影响
悬挂触底诊断；这是能力声明/占位铰问题，另记试跑报告。

用法（Windows，项目 .venv）：
    .venv\\Scripts\\python.exe scripts\\run_oomwoo.py \
        --config cases\\oomwoo_flat.json --out outputs\\oomwoo-flat --repeat 2
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_cases  # noqa: E402

LEDGER = REPO_ROOT / "docs" / "试跑" / "参数溯源-oomwoo.csv"

run_cases.LEDGER_PATH = LEDGER
run_cases.RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner_oomwoo.json"


def build_judge_params(*args, **kwargs):
    """OOMWOO 无被动悬挂：susp_L/R 是 ±1 µm 占位铰，名义行程 0 会让 judge 永远报
    suspension_bottom。

    这里把判定用的 susp_range_m 置为 1 m（永不到达），只影响悬挂触底诊断，
    不改变任何物理量。上游修法见试跑报告。
    """
    params = _ORIGINAL_BUILD_JUDGE_PARAMS(*args, **kwargs)
    params["susp_range_m"] = 1.0
    return params


_ORIGINAL_BUILD_JUDGE_PARAMS = run_cases.build_judge_params
run_cases.build_judge_params = build_judge_params

if __name__ == "__main__":
    try:
        raise SystemExit(run_cases.main())
    except run_cases.ContractError as error:
        print(f"CONTRACT ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
