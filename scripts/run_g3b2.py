"""G3 第二批（摩擦/限扭/速度敏感性）批运行入口。

本批只允许改 case 层的 ``environment.pairs[*].friction``、轮端限扭与
``approach.speed_mps``；``judge.py`` / ``scripts/run_cases.py`` / 契约 /
``cases/_runner*.json`` 默认层均不改。OOMWOO case 的 pair 摩擦在 runner 里有两道
一致性校验（``config_friction_from_ledger`` 与 S24 接触回读），μ 必须同时出现在
case 和台账里。为了让「case 是唯一改动源」成立，本包装层：

1. 读 case 的 ``environment.pairs``，把台账中对应的
   ``contact.<pair>_friction_s`` 行改成 case 的 ``friction[0]``；其余行逐字不动；
2. 把派生台账写到临时文件，交给未修改的 ``run_oomwoo.py`` / ``run_cases.py`` 跑；
3. 跑完把派生台账复制到批次目录 ``derived_ledger.csv``，并打印改动行，便于复核。

没有摩擦改动时（限扭/速度维），派生台账与基准台账逐字相同。用法与
``scripts/run_oomwoo.py`` 相同：

    .venv\\Scripts\\python.exe scripts\\run_g3b2.py \
        --config cases\\g3-b2\\g3_b2_friction_mu0p5_h10p0.json \
        --out outputs\\g3-b2\\friction\\mu0p5_h10p0 --repeat 2
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_oomwoo  # noqa: E402,F401  （先装载 OOMWOO 台账/runner 默认层补丁）
import run_cases  # noqa: E402

BASE_LEDGER = REPO_ROOT / "docs" / "试跑" / "参数溯源-oomwoo.csv"


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def derive_ledger(config_path: Path) -> tuple[Path, list[tuple[str, str, str]]]:
    """按 case 的 pair 摩擦派生台账；返回 (临时路径, [(param_id, 旧值, 新值)])。"""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fieldnames, rows = _read_rows(BASE_LEDGER)
    by_id = {row["param_id"]: row for row in rows}
    changes: list[tuple[str, str, str]] = []
    for key, spec in config["environment"]["pairs"].items():
        param_id = run_cases.pair_mu_id(key)
        if param_id not in by_id:
            raise run_cases.ContractError(f"台账缺 contact 行：{param_id}")
        target = float(spec["friction"][0])
        current = float(by_id[param_id]["value"])
        if abs(current - target) > 1e-12:
            by_id[param_id]["value"] = repr(target)
            changes.append((param_id, repr(current), repr(target)))

    fd, name = tempfile.mkstemp(prefix="g3b2-ledger-", suffix=".csv")
    Path(name).unlink(missing_ok=True)
    tmp_path = Path(name)
    with tmp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return tmp_path, changes


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    known, _ = parser.parse_known_args(argv)

    config_path = Path(known.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    out_dir = Path(known.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir

    ledger_path, changes = derive_ledger(config_path)
    run_cases.LEDGER_PATH = ledger_path
    print(f"[g3b2] derived_ledger {ledger_path}")
    print(f"[g3b2] base_ledger {BASE_LEDGER}")
    if changes:
        for param_id, old, new in changes:
            print(f"[g3b2] ledger_override {param_id}: {old} -> {new}")
    else:
        print("[g3b2] ledger_override none（case 摩擦与基准台账一致）")

    try:
        rc = run_cases.main(argv)
        if out_dir.exists():
            shutil.copyfile(ledger_path, out_dir / "derived_ledger.csv")
    finally:
        ledger_path.unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
