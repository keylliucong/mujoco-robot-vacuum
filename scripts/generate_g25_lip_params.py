"""G2.5 前下缘敏感性参数集生成器（只写 params/，不改模型）。

基准：``params/oomwoo_g25.json``（G2.5 基线，height=12.5 mm、radius=0、rigid）。
本脚本按单因素两档生成四个变体，供 ``scripts/run_oomwoo.py --params`` 扫描：

    oomwoo_g25_hlo  height = 7.5 mm   （基线 −5 mm）
    oomwoo_g25_hhi  height = 17.5 mm  （基线 +5 mm）
    oomwoo_g25_r3   radius = 3 mm
    oomwoo_g25_soft compliance = soft（solref 0.05 s，solimp 0.75/0.95/0.01/0.5/2.0）

派生量随之重算：``geom_radius = max(radius, 0.2 mm)``、
``center_x = overhang``、``center_z = height + geom_radius``。

用法（Mac/Windows 均可，只读写 JSON）：
    python scripts/generate_g25_lip_params.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

PARAMS_DIR = Path(__file__).resolve().parent.parent / "params"
BASE = PARAMS_DIR / "oomwoo_g25.json"

VARIANTS = {
    "oomwoo_g25_hlo": {"front_lip.height_m": 0.0075},
    "oomwoo_g25_hhi": {"front_lip.height_m": 0.0175},
    "oomwoo_g25_r3": {"front_lip.radius_m": 0.003},
    "oomwoo_g25_soft": {
        "front_lip.compliance": 1.0,
        "front_lip.solref_timeconst_s": 0.05,
        "front_lip.solimp_d0": 0.75,
        "front_lip.solimp_d1": 0.95,
        "front_lip.solimp_d2": 0.01,
        "front_lip.solimp_d3": 0.5,
        "front_lip.solimp_d4": 2.0,
    },
}


def derive(document: dict) -> None:
    params = document["params"]
    height = float(params["front_lip.height_m"]["value"])
    radius = float(params["front_lip.radius_m"]["value"])
    overhang = float(params["front_lip.overhang_m"]["value"])
    geom_radius = max(radius, 0.0002)
    params["front_lip.geom_radius_m"]["value"] = geom_radius
    params["front_lip.center_x_m"]["value"] = overhang
    params["front_lip.center_z_m"]["value"] = height + geom_radius


def main() -> int:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    derive(base)
    BASE.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for config_id, overrides in VARIANTS.items():
        document = copy.deepcopy(base)
        document["config_id"] = config_id
        document["note"] = (
            f"{base['note']} 本文件是 G2.5 敏感性变体：{config_id}，"
            f"覆盖 {', '.join(f'{k}={v}' for k, v in overrides.items())}；"
            "只用于说明哪些前缘参数值得实测，不作机型结论。"
        )
        for key, value in overrides.items():
            document["params"][key]["value"] = value
        derive(document)
        path = PARAMS_DIR / f"{config_id}.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {path.relative_to(PARAMS_DIR.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
