"""从 G2.5 批次输出里提取「首次接触来源」与判定摘要（不依赖 MuJoCo）。

runner 的 summary.csv 只有判据侧结果；「首次接触是轮还是壳体」需要看时程里的
`contact_<pair>_active` 列。本脚本对每个 (case, repeat) 取 base 档timeseries.csv，
找第一帧任一 `*--step` 接触对、第一帧驱动轮接触、第一帧 chassis_* 接触。

用法：
    python scripts/analyze_g25_contacts.py outputs/g25-step12p5 outputs/g25-step20 ...
输出 CSV 到 stdout（UTF-8）。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def read_summary(batch_dir: Path):
    path = batch_dir / "summary.csv"
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def timeseries_path(batch_dir: Path, case_id: str, repeat: str, total_repeats: int) -> Path:
    name = case_id if total_repeats == 1 else f"{case_id}_r{repeat}"
    return batch_dir / name / "timeseries.csv"


def first_active(columns, _unused, predicate):
    indices = [i for i, name in enumerate(columns) if predicate(name)]
    for row_index in range(len(next(iter(columns.values())))):
        for name in indices:
            if columns[name][row_index] == "1":
                return name, float(columns["t_s"][row_index])
    return "", None


def load_timeseries(path: Path):
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = {name: [] for name in reader.fieldnames}
        for row in reader:
            for name in columns:
                columns[name].append(row[name])
    return columns


def analyze(batch_dir: Path):
    summary = read_summary(batch_dir)
    total = len(summary)
    out = []
    for row in summary:
        path = timeseries_path(batch_dir, row["case_id"], row["repeat"], total)
        columns = load_timeseries(path)
        first_step, t_first = first_active(
            columns, None, lambda n: n.startswith("contact_") and n.endswith("--step_active")
        )
        wheel_step, t_wheel = first_active(
            columns,
            None,
            lambda n: n.startswith("contact_wheel_") and n.endswith("--step_active"),
        )
        chassis_step, t_chassis = first_active(
            columns,
            None,
            lambda n: n.startswith("contact_chassis--") and n.endswith("--step_active"),
        )
        out.append(
            {
                "batch": batch_dir.name,
                "case_id": row["case_id"],
                "repeat": row["repeat"],
                "status": row["status"],
                "passed": row["passed"],
                "failure_primary": row["failure_primary"],
                "failure_flags": row["failure_flags"],
                "t_trigger_s": row["t_trigger_s"],
                "first_contact_pair": first_step.replace("contact_", "").replace("_active", ""),
                "t_first_contact_s": "" if t_first is None else f"{t_first:.6f}",
                "t_wheel_touch_s": "" if t_wheel is None else f"{t_wheel:.6f}",
                "t_chassis_touch_s": "" if t_chassis is None else f"{t_chassis:.6f}",
                "advance_m": row["advance_m"],
                "pitch_max_deg": row["pitch_max_deg"],
                "contact_normal_max_n": row["contact_normal_max_n"],
            }
        )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("batches", nargs="+")
    args = parser.parse_args(argv)
    rows = []
    for batch in args.batches:
        rows.extend(analyze(Path(batch)))
    if not rows:
        raise SystemExit("no rows")
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
