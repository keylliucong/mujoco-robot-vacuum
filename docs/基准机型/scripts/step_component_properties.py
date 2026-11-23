#!/usr/bin/env python3
"""Exact B-rep volume / CoM / inertia for one trusted component STEP.

Scope
-----
This script is for **component** STEPs from the trusted ``lib/`` library
(e.g. ``lib/roborock/OOM-W01-drive-wheel-assembly.stp``).  It deliberately does
**not** consume the unreviewed ``designs/one/agentic/july-2026/`` experiment:
that assembly's own README says it is not the OOMWOO One design and has known
design errors (caster upside down, fan/brush on opposite sides, side brush
reversed, bumper outside the body).  Its layout errors would contaminate mass,
CoM and inertia in ways that look plausible.

What it computes
----------------
Open CASCADE's ``BRepGProp`` volume-property integration (exact B-rep, not a
mesh approximation):

* volume,
* centre of mass,
* inertia tensor about the centre of mass,

with ``gmsh.model.occ.getMass / getCenterOfMass / getMatrixOfInertia``.
Mass is ``rho * V``; STEP carries no material density, so ``rho`` is an explicit
input and is recorded in the output.

Selecting a solid
-----------------
A STEP may contain several solids (the drive-wheel module has wheel, motor and
suspension arm).  Use ``--tag`` to select the solid of interest; without it the
largest-volume solid is used.  ``--axis`` (x/y/z) tells the script which axis is
the wheel axle: the diameter is the mean of the two perpendicular extents and
the width is the extent along the axis.  Do not pass ``--axis`` for a non-wheel
part.

Outputs
-------
``oomwoo-<name>-metrics.json``
``oomwoo-<name>-solids.csv``
``oomwoo-<name>-dimensions.md``  (S17 lineage header + param_id/value/unit/method_note)
``oomwoo-<name>-dimensions.csv``

The S17 header records: script rev, table rev, input sha256, method (brep_exact),
mesh export / chord / angle tolerances (N/A because no tessellation is used),
environment, density, selected tag/axis and frame.

Example
-------
    python step_component_properties.py \
        /path/to/OOM-W01-drive-wheel-assembly.stp \
        --tag 3 --axis z --rho 1100 --rho-alt 1240 \
        --name oomwoo-drive-wheel \
        --source 'oomwoo-cad@266210a:lib/roborock/OOM-W01-drive-wheel-assembly.stp' \
        --outdir docs/基准机型 \
        --script-rev <script-commit> --table-rev <generation-base>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import gmsh
import numpy as np


@dataclass
class Solid:
    tag: int
    volume_mm3: float
    com_mm: np.ndarray
    inertia_unit_mm5: np.ndarray
    bbox_mm: tuple[float, float, float, float, float, float]

    @property
    def extents(self) -> tuple[float, float, float]:
        xmin, ymin, zmin, xmax, ymax, zmax = self.bbox_mm
        return xmax - xmin, ymax - ymin, zmax - zmin


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_solids(step_path: Path) -> list[Solid]:
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.Verbosity", 1)
    gmsh.model.add("component")
    gmsh.model.occ.importShapes(str(step_path), highestDimOnly=True)
    gmsh.model.occ.synchronize()

    solids: list[Solid] = []
    for dim, tag in gmsh.model.occ.getEntities(3):
        solids.append(
            Solid(
                tag=tag,
                volume_mm3=float(gmsh.model.occ.getMass(dim, tag)),
                com_mm=np.array(gmsh.model.occ.getCenterOfMass(dim, tag), dtype=float),
                inertia_unit_mm5=np.array(
                    gmsh.model.occ.getMatrixOfInertia(dim, tag), dtype=float
                ).reshape(3, 3),
                bbox_mm=tuple(float(x) for x in gmsh.model.occ.getBoundingBox(dim, tag)),
            )
        )
    gmsh.finalize()
    if not solids:
        raise RuntimeError("STEP contains no 3D solids")
    return solids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("."))
    ap.add_argument("--name", default="component", help="output file stem")
    ap.add_argument("--source", default="", help="provenance string, e.g. repo@rev:path")
    ap.add_argument("--tag", type=int, default=None,
                    help="solid tag to select (default: largest volume)")
    ap.add_argument("--axis", choices=["x", "y", "z"], default=None,
                    help="wheel axle axis; enables diameter/width rows")
    ap.add_argument("--rho", type=float, default=1100.0,
                    help="primary density kg/m^3 (default 1100 = rubber/TPU-ish, an assumption)")
    ap.add_argument("--rho-alt", type=float, default=1240.0,
                    help="secondary density kg/m^3 (default 1240 = PLA)")
    ap.add_argument("--script-rev", default="working-tree")
    ap.add_argument("--table-rev", default="working-tree")
    ap.add_argument("--warning", default="",
                    help="input-data warning to carry into the S17 header (e.g. STEP reader warning)")
    args = ap.parse_args()

    step = args.step.resolve()
    if not step.is_file():
        print(f"not a file: {step}", file=sys.stderr)
        return 2
    digest = sha256(step)
    solids = read_solids(step)

    by_tag = {s.tag: s for s in solids}
    if args.tag is None:
        selected = max(solids, key=lambda s: s.volume_mm3)
    else:
        if args.tag not in by_tag:
            print(f"tag {args.tag} not in {sorted(by_tag)}", file=sys.stderr)
            return 2
        selected = by_tag[args.tag]

    xext, yext, zext = selected.extents
    extent_by_axis = {"x": xext, "y": yext, "z": zext}
    diameter = None
    width = None
    if args.axis:
        others = [a for a in ("x", "y", "z") if a != args.axis]
        diameter = (extent_by_axis[others[0]] + extent_by_axis[others[1]]) / 2.0
        width = extent_by_axis[args.axis]

    volume_m3 = selected.volume_mm3 * 1e-9
    inertia = selected.inertia_unit_mm5 * 1e-15 * args.rho
    alt_inertia = selected.inertia_unit_mm5 * 1e-15 * args.rho_alt
    principal = np.linalg.eigh(inertia)[0]

    metrics = {
        "input": {
            "path": str(step),
            "bytes": step.stat().st_size,
            "sha256": digest,
            "source": args.source,
            "warning": args.warning,
            "n_solids": len(solids),
            "selected_tag": selected.tag,
        },
        "environment": {
            "python": platform.python_version(),
            "gmsh": gmsh.__version__,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "kernel": "Open CASCADE bundled with gmsh; exact OCC version not exposed by gmsh API",
            "algorithm": "B-rep exact volume properties via gmsh.model.occ.getMass / getCenterOfMass / getMatrixOfInertia (OCC GProp); not mesh",
        },
        "units": "STEP read as mm; output lengths mm, volume m^3, mass kg, inertia kg*m^2",
        "frame": "STEP frame as exported; no B-frame rotation is applied to a component",
        "density": {
            "value_kg_m3": args.rho,
            "alt_value_kg_m3": args.rho_alt,
            "note": "STEP carries no material assignment or density; mass = rho * V and is NOT a CAD-given mass.",
        },
        "selected": {
            "tag": selected.tag,
            "volume_mm3": selected.volume_mm3,
            "volume_m3": volume_m3,
            "bbox_mm": selected.bbox_mm,
            "extents_mm": [xext, yext, zext],
            "axis": args.axis,
            "wheel_diameter_mm": diameter,
            "wheel_width_mm": width,
        },
        "mass": {
            f"kg_at_rho_{args.rho:g}": volume_m3 * args.rho,
            f"kg_at_rho_{args.rho_alt:g}": volume_m3 * args.rho_alt,
        },
        "com_mm": selected.com_mm.tolist(),
        "inertia_about_com": {
            f"kg_m2_at_rho_{args.rho:g}": inertia.tolist(),
            f"kg_m2_at_rho_{args.rho_alt:g}": alt_inertia.tolist(),
        },
        "principal_moments": {
            f"kg_m2_at_rho_{args.rho:g}": principal.tolist(),
            f"kg_m2_at_rho_{args.rho_alt:g}": np.linalg.eigh(alt_inertia)[0].tolist(),
        },
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.name
    (args.outdir / f"{stem}-metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (args.outdir / f"{stem}-solids.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["tag", "volume_mm3",
                    "com_x_mm", "com_y_mm", "com_z_mm",
                    "bbox_xmin_mm", "bbox_ymin_mm", "bbox_zmin_mm",
                    "bbox_xmax_mm", "bbox_ymax_mm", "bbox_zmax_mm"])
        for s in sorted(solids, key=lambda s: s.tag):
            w.writerow([s.tag, f"{s.volume_mm3:.6f}",
                        *[f"{x:.6f}" for x in s.com_mm],
                        *[f"{x:.6f}" for x in s.bbox_mm]])

    dims: list[tuple[str, object, str, str]] = []

    def add(pid: str, value: object, unit: str, note: str) -> None:
        dims.append((pid, value, unit, note))

    bbox_note = "OCC B-rep bbox of the selected solid; STEP frame; no mesh."
    add("geom.component.bbox.x_mm", xext, "mm", bbox_note)
    add("geom.component.bbox.y_mm", yext, "mm", bbox_note)
    add("geom.component.bbox.z_mm", zext, "mm", bbox_note)
    if diameter is not None:
        add("geom.component.wheel.diameter_mm", diameter, "mm",
            f"Mean of the two extents perpendicular to the {args.axis} axle axis; selected solid tag {selected.tag}; STEP frame.")
        add("geom.component.wheel.width_mm", width, "mm",
            f"Extent along the {args.axis} axle axis; selected solid tag {selected.tag}; STEP frame.")
    add("mass.volume_m3", volume_m3, "m^3",
        "B-rep volume of the selected solid; no mesh.")
    add(f"mass.kg_at_rho_{args.rho:g}", volume_m3 * args.rho, "kg",
        "V * rho; rho is an explicit assumption, not a STEP material.")
    add(f"mass.kg_at_rho_{args.rho_alt:g}", volume_m3 * args.rho_alt, "kg",
        "V * rho; alternate density for scale comparison; same caveat.")
    add("com.x_mm", selected.com_mm[0], "mm",
        "Volume centroid of the selected solid; STEP frame; density-independent.")
    add("com.y_mm", selected.com_mm[1], "mm",
        "Volume centroid of the selected solid; STEP frame; density-independent.")
    add("com.z_mm", selected.com_mm[2], "mm",
        "Volume centroid of the selected solid; STEP frame; density-independent.")
    inertia_note = (
        f"B-rep exact GProp matrix about the selected solid's CoM, scaled by rho={args.rho:g}; "
        "STEP frame; no mesh."
    )
    for name, value in (
        ("Ixx", inertia[0, 0]), ("Iyy", inertia[1, 1]), ("Izz", inertia[2, 2]),
        ("Ixy", inertia[0, 1]), ("Ixz", inertia[0, 2]), ("Iyz", inertia[1, 2]),
    ):
        add(f"inertia.{name}_kgm2", value, "kg*m^2", inertia_note)
    for i, value in enumerate(principal, start=1):
        add(f"inertia.principal.{i}_kgm2", value, "kg*m^2",
            f"Eigenvalue {i} of the selected solid's STEP-frame inertia tensor at rho={args.rho:g}.")

    ids = [r[0] for r in dims]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"duplicate param_id(s): {sorted({x for x in ids if ids.count(x) > 1})}")

    with (args.outdir / f"{stem}-dimensions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["param_id", "value", "unit", "method_note"])
        for pid, value, unit, note in dims:
            w.writerow([pid, f"{value:.12g}" if isinstance(value, float) else value, unit, note])

    lines = [
        f"# OOMWOO 组件 STEP 尺寸表（S17 准入）：`{stem}`",
        "",
        f"- generated_by=`docs/基准机型/scripts/step_component_properties.py@{args.script_rev}`",
        f"- table_rev=`{args.table_rev}`",
        f"- source=`{args.source}`",
        f"- input_file=`{step.name}` ({step.stat().st_size} bytes)",
        f"- input_sha256=`{digest}`",
        f"- input_warning=`{args.warning}`" if args.warning else "- input_warning=`none`",
        f"- selected_tag=`{selected.tag}` (of {len(solids)} solids)",
        f"- selected_axis=`{args.axis or 'none'}`",
        "- method=`brep_exact`",
        "- mesh_export=`none`",
        "- chord_tol=`N/A` (B-rep exact; no tessellation)",
        "- angle_tol=`N/A` (B-rep exact; no tessellation)",
        f"- env=`Python {platform.python_version()}; gmsh {gmsh.__version__}; NumPy {np.__version__}; Open CASCADE bundled with gmsh (exact OCC version not exposed by gmsh API)`",
        f"- rho_primary=`{args.rho:g} kg/m^3`; rho_alt=`{args.rho_alt:g} kg/m^3`",
        "- frame=`STEP frame as exported; no B-frame rotation applied to a component`",
        "",
        "| param_id | value | unit | method_note |",
        "|---|---|---|---|",
    ]
    for pid, value, unit, note in dims:
        v = f"{value:.12g}" if isinstance(value, float) else str(value)
        lines.append(f"| `{pid}` | {v} | {unit} | {note} |")
    lines.append("")
    lines.append("> This table is for one trusted component, not for the whole machine. It must not be combined with another frame or another design without a documented transform.")
    (args.outdir / f"{stem}-dimensions.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"input sha256: {digest}")
    print(f"solids: {len(solids)}; selected tag {selected.tag}")
    print(f"volume: {selected.volume_mm3:.3f} mm^3 = {volume_m3*1000:.6f} L")
    print(f"mass @ {args.rho:g}: {volume_m3*args.rho:.6f} kg")
    print(f"mass @ {args.rho_alt:g}: {volume_m3*args.rho_alt:.6f} kg")
    print(f"CoM (STEP frame): {selected.com_mm}")
    print(f"principal moments @ {args.rho:g}: {principal}")
    if diameter is not None:
        print(f"wheel diameter={diameter:.3f} mm width={width:.3f} mm (axis {args.axis})")
    print(f"wrote: {args.outdir / (stem + '-dimensions.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
