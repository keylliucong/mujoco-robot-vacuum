#!/usr/bin/env python3
"""一次性迁移：给台账 `param_id` 加 `<machine>.` 前缀、清空 xpath 占位。

对应 ADR-014 / S23。默认只演练，不落盘；确认后加 `--write`。

用法：
    python scripts/migrate_param_ids.py --ledger docs/参数溯源.csv \
        --budget docs/不确定度预算.csv
    python scripts/migrate_param_ids.py --ledger docs/参数溯源.csv \
        --budget docs/不确定度预算.csv --write

规则（与 ADR-014 一致）：
1. 机型取自该行 `ref` 的 `machine=own|prototype|oomwoo`；
2. `param_id` 已是 `<machine>.` 前缀则保留，前缀与 ref 不一致即报错；
3. `xpath` 为 `TODO(...)` / `N/A(...)` / `—` 的改为空字符串；
4. 迁移后复用 `check_param_ids.py`：全表唯一、前缀合法、xpath 无占位；
5. 预算表按 `unc_id` 的 `unc.<machine>.` 取机型；没有则按裸量名在台账中
   唯一归属的机型；仍无唯一归属时按 `own`（main 预算表的历史口径）。
   迁移后再跨表检查每个预算 `param_id` 都能落到台账行。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_param_ids import (  # noqa: E402
    MACHINE_REF_RE,
    MACHINES,
    PLACEHOLDER_RE,
    PREFIX_RE,
    check_budget_rows,
    check_ledger_rows,
)


UNC_MACHINE_RE = re.compile(r"^unc\.(?P<machine>[A-Za-z0-9_-]+)\.")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def ledger_machine(row: dict[str, str]) -> str:
    match = MACHINE_REF_RE.search(row.get("ref") or "")
    if not match:
        raise ValueError(
            f"param_id={row.get('param_id')!r} 的 ref 没有 machine=...，无法定机型"
        )
    machine = match.group(1)
    if machine not in MACHINES:
        raise ValueError(f"机型 {machine!r} 不在固定取值 {MACHINES}")
    return machine


def bare_name(param_id: str) -> str:
    match = PREFIX_RE.match(param_id)
    if match and match.group("machine") in MACHINES:
        return match.group("name")
    return param_id


def prefix_machine(param_id: str) -> str | None:
    match = PREFIX_RE.match(param_id)
    if match and match.group("machine") in MACHINES:
        return match.group("machine")
    return None


def migrate_ledger(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, set[str]]]:
    owned_names: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        owned_names[bare_name((row.get("param_id") or "").strip())].add(
            ledger_machine(row)
        )

    for row in rows:
        machine = ledger_machine(row)
        param_id = (row.get("param_id") or "").strip()
        existing = prefix_machine(param_id)
        if existing:
            if existing != machine:
                raise ValueError(
                    f"param_id={param_id!r} 前缀与 ref 的 machine={machine} 不一致"
                )
        else:
            row["param_id"] = f"{machine}.{param_id}"

        xpath = (row.get("xpath") or "").strip()
        if PLACEHOLDER_RE.match(xpath):
            row["xpath"] = ""
    return rows, owned_names


def budget_machine(row: dict[str, str], owned_names: dict[str, set[str]]) -> str:
    unc_id = (row.get("unc_id") or "").strip()
    match = UNC_MACHINE_RE.match(unc_id)
    if match and match.group("machine") in MACHINES:
        return match.group("machine")

    name = bare_name((row.get("param_id") or "").strip())
    owners = owned_names.get(name, set())
    if len(owners) == 1:
        return next(iter(owners))
    return "own"


def migrate_budget(
    rows: list[dict[str, str]], owned_names: dict[str, set[str]]
) -> list[dict[str, str]]:
    for row in rows:
        machine = budget_machine(row, owned_names)
        param_id = (row.get("param_id") or "").strip()
        existing = prefix_machine(param_id)
        if existing:
            if existing != machine:
                raise ValueError(
                    f"预算行 {row.get('unc_id')!r} 的 param_id={param_id!r} "
                    f"前缀与推断机型 {machine!r} 不一致"
                )
        else:
            row["param_id"] = f"{machine}.{param_id}"
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default="docs/参数溯源.csv", help="台账 CSV")
    parser.add_argument("--budget", default=None, help="预算表 CSV（可选）")
    parser.add_argument("--write", action="store_true", help="落盘；不加则只演练")
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger)
    try:
        ledger_fields, ledger_rows = read_csv(ledger_path)
        ledger_rows, owned_names = migrate_ledger(ledger_rows)

        budget_rows: list[dict[str, str]] = []
        budget_fields: list[str] = []
        budget_path = Path(args.budget) if args.budget else None
        if budget_path:
            budget_fields, budget_rows = read_csv(budget_path)
            budget_rows = migrate_budget(budget_rows, owned_names)
    except (OSError, ValueError) as exc:
        print(f"迁移失败: {exc}", file=sys.stderr)
        return 2

    if args.write:
        write_csv(ledger_path, ledger_fields, ledger_rows)
        if budget_path:
            write_csv(budget_path, budget_fields, budget_rows)

    errors, counts, ledger_ids = check_ledger_rows(ledger_rows, str(ledger_path))
    if budget_path:
        errors += check_budget_rows(budget_rows, ledger_ids, str(budget_path))

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    summary = ", ".join(f"{name}={counts.get(name, 0)}" for name in MACHINES)
    action = "已写入" if args.write else "演练通过（未落盘，加 --write 落盘）"
    print(f"{action}: {ledger_path} {len(ledger_rows)} 行（{summary}）")
    if budget_path:
        print(f"预算表: {budget_path} {len(budget_rows)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
