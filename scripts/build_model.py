"""从结构模板 + 参数 JSON 生成可运行 MJCF。

设计约束
--------
- ``models/baseline.xml`` 只写结构（body 树、关节、geom 拓扑、接触对、驱动方式），
  不写任何几何/质量/惯量/摩擦/限扭数值。
- 所有数值来自 ``params/<config_id>.json``，每个值带来源标签；本脚本只做
  占位符替换与一致性检查，不修改数值。
- 生成产物写到 ``build/models/<config_id>.xml``，不手工编辑；同一模板 + 同一
  参数文件必须得到逐字节相同的 XML。

用法
----
    .venv\\Scripts\\python.exe scripts/build_model.py \
        --params params/oomwoo.json --out build/models/oomwoo_public_v1.xml --validate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
REQUIRED_TOP_KEYS = ("schema_version", "config_id", "machine", "values")
LABELS = {"本机实测", "图纸推算", "公开参考", "工程假设", "缺失", "待标定"}


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_params(path: Path) -> dict:
    params = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_TOP_KEYS if k not in params]
    if missing:
        raise SystemExit(f"params missing top-level keys: {missing}")
    values = params["values"]
    bad = []
    for key, entry in values.items():
        if not isinstance(entry, dict) or "value" not in entry:
            bad.append(f"{key}: missing value")
            continue
        if entry.get("label") not in LABELS:
            bad.append(f"{key}: invalid label {entry.get('label')!r}")
    if bad:
        raise SystemExit("params validation error:\n  - " + "\n  - ".join(bad))
    return params


def flatten(params: dict) -> dict:
    return {k: v["value"] for k, v in params["values"].items()}


def format_value(value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int,)):
        return str(value)
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, str):
        return value
    raise SystemExit(f"unsupported parameter value type: {type(value)} ({value!r})")


def render(template: str, params: dict) -> tuple[str, list[str], dict]:
    values = flatten(params)
    missing = []
    used = []

    def _sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        used.append(key)
        return format_value(values[key])

    out = PLACEHOLDER_RE.sub(_sub, template)
    if missing:
        raise SystemExit("unresolved template placeholders:\n  - " + "\n  - ".join(
            sorted(set(missing))))
    leftovers = PLACEHOLDER_RE.findall(out)
    if leftovers:
        raise SystemExit(f"unresolved placeholders after render: {leftovers}")
    unused = sorted(set(values) - set(used))
    return out, sorted(set(used)), {"unused_parameter_keys": unused}


def build_from_files(template_path: Path, params_path: Path,
                     out_path: Path | None = None, validate: bool = False) -> dict:
    template = template_path.read_text(encoding="utf-8")
    params = load_params(params_path)
    xml, used, meta = render(template, params)
    xml_bytes = xml.encode("utf-8")
    manifest = {
        "config_id": params["config_id"],
        "machine": params["machine"],
        "template_path": str(template_path),
        "template_sha256": sha256_file(template_path),
        "params_path": str(params_path),
        "params_sha256": sha256_file(params_path),
        "xml_sha256": sha256_bytes(xml_bytes),
        "placeholders_used": len(used),
        "unused_parameter_keys": meta["unused_parameter_keys"],
        "source": params.get("source", {}),
        "missing": params.get("missing", []),
        "blockers": params.get("blockers", []),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }

    if validate:
        try:
            import mujoco
        except Exception as exc:  # pragma: no cover - platform dependent
            raise SystemExit(f"mujoco import error; cannot validate: {exc}")
        model = mujoco.MjModel.from_xml_string(xml)
        manifest["mujoco_validation"] = {
            "mujoco_version": mujoco.__version__,
            "nbody": int(model.nbody),
            "ngeom": int(model.ngeom),
            "njnt": int(model.njnt),
            "nu": int(model.nu),
            "timestep_s": float(model.opt.timestep),
            "cone": int(model.opt.cone),
            "integrator": int(model.opt.integrator),
            "mass_assembly_kg": float(sum(model.body_mass[1:])),
        }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(xml_bytes)
        manifest["xml_path"] = str(out_path)
        manifest_path = out_path.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return {"xml": xml, "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", default=str(repo / "models/baseline.xml"))
    parser.add_argument("--params", default=str(repo / "params/oomwoo.json"))
    parser.add_argument("--out", default=None,
                        help="默认 build/models/<config_id>.xml")
    parser.add_argument("--validate", action="store_true",
                        help="用当前安装的 MuJoCo 编译生成 XML")
    args = parser.parse_args(argv)

    params_path = Path(args.params)
    params = load_params(params_path)
    out_path = Path(args.out) if args.out else repo / "build/models" / f"{params['config_id']}.xml"
    result = build_from_files(Path(args.template), params_path, out_path,
                              validate=args.validate)
    m = result["manifest"]
    print(f"config_id:      {m['config_id']}")
    print(f"machine:        {m['machine']}")
    print(f"template sha256:{m['template_sha256']}")
    print(f"params sha256:  {m['params_sha256']}")
    print(f"xml sha256:     {m['xml_sha256']}")
    print(f"xml path:       {m.get('xml_path', '-')}")
    if m["unused_parameter_keys"]:
        print("unused params:  " + ", ".join(m["unused_parameter_keys"]))
    if "mujoco_validation" in m:
        v = m["mujoco_validation"]
        print(f"mujoco {v['mujoco_version']}: nbody={v['nbody']} ngeom={v['ngeom']} "
              f"njnt={v['njnt']} nu={v['nu']} timestep={v['timestep_s']} "
              f"cone={v['cone']} integrator={v['integrator']} "
              f"mass={v['mass_assembly_kg']:.6f} kg")
    if m["blockers"]:
        print("blockers:")
        for item in m["blockers"]:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
