#!/usr/bin/env python
"""STEP/STP -> 质量属性（B-rep 精确积分，不三角化）。

方法
----
用 OpenCascade 的 BRepGProp.VolumeProperties 对每个实体做体积积分，得到
体积、质心与**关于质心**的惯量张量（OCCT GProp_GProps 的定义）。多实体
先逐个积分，再按体积加权合并（密度在同一文件内视为均匀）。

与 mesh 近似的区别：没有弦高/角度容差，结果不随三角化参数变化；代价是
必须装 OCCT（本脚本用 OCP 的 Python 绑定，版本写进输出头）。

单位
----
STEP 文件按 mm 读入（OCCT STEP reader 的默认工作单位），输出统一换算为
SI：m、m^3、kg、kg*m^2。密度默认 1000 kg/m^3（水），调用方用
``--part name=path=density`` 覆盖。密度不是 CAD 数据，输出里单列。

用法
----
    python scripts/step_mass_properties.py \
        --part wheel=../oomwoo-cad/lib/roborock/OOM-W01-drive-wheel-assembly.stp=1200 \
        --out docs/试跑/step-质量属性-oomwoo.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
except ImportError as error:  # pragma: no cover
    raise SystemExit("需要 numpy：python -m pip install numpy") from error

try:
    import OCP
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
except ImportError as error:  # pragma: no cover
    raise SystemExit(
        "需要 OCP（OpenCascade Python 绑定）。参考安装：\n"
        "  python -m pip install cadquery-ocp==7.9.3.1.1 'vtk==9.6.2'\n"
        f"原始错误：{error}"
    ) from error


OCP_VERSION = getattr(OCP, "__version__", "unknown")
METHOD = "occt-gprop-brep-exact"
MM = 1.0e-3
MM3 = 1.0e-9
MM5 = 1.0e-15


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_step(path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP 读取失败（{status}）：{path}")
    reader.TransferRoots()
    return reader.OneShape()


def solid_properties(shape):
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    while explorer.More():
        solid = TopoDS.Solid_s(explorer.Current())
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(solid, props)
        solids.append((solid, props))
        explorer.Next()
    return solids


def tensor_from_gprops(props) -> np.ndarray:
    matrix = props.MatrixOfInertia()
    return np.array(
        [[matrix.Value(i, j) for j in range(1, 4)] for i in range(1, 4)], dtype=float
    )


def combine(solids, density: float):
    """按体积加权合并实体，返回 (volume_m3, com_m, inertia_about_com_kgm2, bbox_m)。"""
    entries = []
    total_volume_mm3 = 0.0
    for solid, props in solids:
        volume_mm3 = float(props.Mass())
        if volume_mm3 <= 0.0:
            continue
        com_mm = np.array(
            [props.CentreOfMass().X(), props.CentreOfMass().Y(), props.CentreOfMass().Z()],
            dtype=float,
        )
        inertia_mm5 = tensor_from_gprops(props)  # mm^5 * (kg/mm^3) 归一
        entries.append((volume_mm3, com_mm, inertia_mm5))
        total_volume_mm3 += volume_mm3
    if not entries:
        raise RuntimeError("没有正体积实体")

    volume_m3 = total_volume_mm3 * MM3
    mass = volume_m3 * density
    com_mm = sum(vol * com for vol, com, _ in entries) / total_volume_mm3
    # OCCT 的惯量按 mm^5（体积积分 r^2 dV），mm^5 -> m^5 是 1e-15。
    inertia = np.zeros((3, 3))
    for vol, com, inertia_mm5 in entries:
        m = vol * MM3 * density
        inertia += inertia_mm5 * MM5 * density
        d = (com - com_mm) * MM
        inertia += m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    x0, y0, z0, x1, y1, z1 = bbox_of_solids(solids)
    return volume_m3, mass, com_mm * MM, inertia, (x0, y0, z0, x1, y1, z1)


def bbox_of_solids(solids):
    box = Bnd_Box()
    for solid, _ in solids:
        BRepBndLib.Add_s(solid, box)
    return box.Get()


def principal_moments(inertia: np.ndarray):
    values = np.linalg.eigvalsh(inertia)
    return sorted(float(v) for v in values)


def parse_part(spec: str):
    parts = spec.split("=")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("--part 必须是 name=path=density")
    name, path, density = parts
    return name, Path(path).expanduser().resolve(), float(density)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="STEP -> 质量属性（B-rep 精确积分）")
    parser.add_argument("--part", action="append", type=parse_part, required=True)
    parser.add_argument("--out", required=True, help="输出 CSV 路径")
    parser.add_argument("--solid-out", default="", help="可选：逐实体明细 CSV")
    parser.add_argument("--note", default="", help="写进输出头的备注")
    args = parser.parse_args(argv)

    rows = []
    solid_rows = []
    for name, path, density in args.part:
        if not path.is_file():
            raise SystemExit(f"输入不存在：{path}")
        shape = read_step(path)
        solids = solid_properties(shape)
        volume_m3, mass, com_m, inertia, bbox = combine(solids, density)
        for index, (solid, props) in enumerate(solids):
            box = Bnd_Box()
            BRepBndLib.Add_s(solid, box)
            sx0, sy0, sz0, sx1, sy1, sz1 = box.Get()
            sp = tensor_from_gprops(props)
            solid_rows.append(
                {
                    "part": name,
                    "solid_index": index,
                    "volume_m3": float(props.Mass()) * MM3,
                    "com_x_m": props.CentreOfMass().X() * MM,
                    "com_y_m": props.CentreOfMass().Y() * MM,
                    "com_z_m": props.CentreOfMass().Z() * MM,
                    "size_x_m": (sx1 - sx0) * MM,
                    "size_y_m": (sy1 - sy0) * MM,
                    "size_z_m": (sz1 - sz0) * MM,
                    "bbox_min_x_m": sx0 * MM,
                    "bbox_min_y_m": sy0 * MM,
                    "bbox_min_z_m": sz0 * MM,
                    "ixx_kgm2": sp[0, 0] * MM5 * density,
                    "iyy_kgm2": sp[1, 1] * MM5 * density,
                    "izz_kgm2": sp[2, 2] * MM5 * density,
                }
            )
        bbox_m = tuple(v * MM for v in bbox)
        moments = principal_moments(inertia)
        # 车轮类部件：给出最大外径与轴向厚度（按最小尺寸轴为轴向）
        size = [bbox_m[3] - bbox_m[0], bbox_m[4] - bbox_m[1], bbox_m[5] - bbox_m[2]]
        axis = min(range(3), key=lambda i: size[i])
        diameter = max(size[(axis + 1) % 3], size[(axis + 2) % 3])
        rows.append(
            {
                "part": name,
                "source": str(path),
                "input_sha256": sha256_file(path),
                "solids": len(solids),
                "density_kg_m3": density,
                "volume_m3": volume_m3,
                "mass_kg": mass,
                "com_x_m": com_m[0],
                "com_y_m": com_m[1],
                "com_z_m": com_m[2],
                "bbox_min_x_m": bbox_m[0],
                "bbox_min_y_m": bbox_m[1],
                "bbox_min_z_m": bbox_m[2],
                "bbox_max_x_m": bbox_m[3],
                "bbox_max_y_m": bbox_m[4],
                "bbox_max_z_m": bbox_m[5],
                "size_x_m": size[0],
                "size_y_m": size[1],
                "size_z_m": size[2],
                "outer_diameter_m": diameter,
                "axial_thickness_m": size[axis],
                "ixx_kgm2": inertia[0, 0],
                "iyy_kgm2": inertia[1, 1],
                "izz_kgm2": inertia[2, 2],
                "ixy_kgm2": inertia[0, 1],
                "ixz_kgm2": inertia[0, 2],
                "iyz_kgm2": inertia[1, 2],
                "i1_kgm2": moments[0],
                "i2_kgm2": moments[1],
                "i3_kgm2": moments[2],
            }
        )

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header_meta = {
        "generated_by": f"scripts/step_mass_properties.py@{git_rev()}",
        "method": METHOD,
        "tessellation": "none (B-rep volume integration)",
        "python": sys.version.split()[0],
        "ocp": OCP_VERSION,
        "numpy": np.__version__,
        "os": platform.platform(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "input_sha256": {row["part"]: row["input_sha256"] for row in rows},
    }
    columns = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        handle.write(
            "# generated_by={generated_by}; method={method}; tessellation={tessellation}; "
            "ocp={ocp}; python={python}; input_sha256={sha}; note={note}\n".format(
                sha=json.dumps(header_meta["input_sha256"], ensure_ascii=False, sort_keys=True),
                **{k: header_meta[k] for k in ("generated_by", "method", "tessellation", "ocp", "python", "note")},
            )
        )
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (f"{value:.12g}" if isinstance(value, float) else value)
                    for key, value in row.items()
                }
            )
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(
        json.dumps(header_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {out_path}")
    print(f"wrote {meta_path}")
    if args.solid_out:
        solid_path = Path(args.solid_out).expanduser().resolve()
        solid_path.parent.mkdir(parents=True, exist_ok=True)
        with open(solid_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(solid_rows[0].keys()), lineterminator="\n")
            writer.writeheader()
            for row in solid_rows:
                writer.writerow(
                    {k: (f"{v:.12g}" if isinstance(v, float) else v) for k, v in row.items()}
                )
        print(f"wrote {solid_path}")
    for row in rows:
        print(
            f"{row['part']:12s} solids={row['solids']:3d} V={row['volume_m3'] * 1e6:9.3f} cm3 "
            f"m={row['mass_kg'] * 1000:8.2f} g (rho={row['density_kg_m3']:.0f}) "
            f"bbox={row['size_x_m'] * 1000:.1f}x{row['size_y_m'] * 1000:.1f}x{row['size_z_m'] * 1000:.1f} mm "
            f"I1..3={row['i1_kgm2']:.4e},{row['i2_kgm2']:.4e},{row['i3_kgm2']:.4e} kg*m2"
        )
    return 0


def git_rev() -> str:
    try:
        import subprocess

        return subprocess.check_output(
            ["git", "rev-parse", "--short=12", "HEAD"], text=True, cwd=Path(__file__).parent
        ).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
