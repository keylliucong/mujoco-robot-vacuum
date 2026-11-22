#!/usr/bin/env python3
"""S23 台账键检查：`param_id = <machine>.<config_id>.<量名>`（契约 v1.8.4）。

全表唯一，键里的 `config_id` 必须与 `ref` 的 `config_id=` 一致，xpath 无占位。

用法：
    python scripts/check_param_ids.py                       # 默认查 docs/参数溯源.csv
    python scripts/check_param_ids.py docs/参数溯源.csv
    python scripts/check_param_ids.py --budget docs/不确定度预算.csv
    python scripts/check_param_ids.py --counts              # 附带各机型行数

退出码：0 通过；1 有违规；2 输入文件读不了。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


MACHINES = ("own", "prototype", "oomwoo")
# config_id 不含点号，量名可含点号（路径式量名，如 geom.chassis.half_x）。
PREFIX_RE = re.compile(
    r"^(?P<machine>[A-Za-z0-9_-]+)\.(?P<config_id>[A-Za-z0-9_-]+)\.(?P<name>\S+)$"
)
MACHINE_REF_RE = re.compile(r"machine\s*=\s*([A-Za-z0-9_-]+)")
CONFIG_REF_RE = re.compile(r"config_id\s*=\s*([A-Za-z0-9_-]+)")
# TODO(...)、N/A(...)、—、- 都是占位，不是"没绑 xpath"。
PLACEHOLDER_RE = re.compile(r"^\s*(?:TODO\(.*\)|N/A\(.*\)|—|-)\s*$", re.IGNORECASE)
# 真实指针至少带一个定位分隔符（`file:/...`、`@attr`、`[0]`）。
POINTER_RE = re.compile(r"[/:@\[]")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check_ledger_rows(
    rows: list[dict[str, str]], name: str = "<ledger>"
) -> tuple[list[str], Counter[str], set[str]]:
    """校验已读入的行，返回（错误, 各机型行数, param_id 集合）。"""
    errors: list[str] = []
    machine_counts: Counter[str] = Counter()

    if not rows:
        return [f"{name}: 空表或没有表头"], machine_counts, set()

    for column in ("param_id", "xpath", "ref"):
        if column not in rows[0]:
            return [f"{name}: 缺少 {column} 列"], machine_counts, set()

    seen: dict[str, int] = {}
    ids: set[str] = set()
    for line, row in enumerate(rows, start=2):
        param_id = (row.get("param_id") or "").strip()
        xpath = (row.get("xpath") or "").strip()
        ref = row.get("ref") or ""

        if not param_id:
            errors.append(f"{name}:{line}: param_id 为空")
            continue

        ids.add(param_id)
        match = PREFIX_RE.match(param_id)
        if not (match and match.group("machine") in MACHINES):
            match = None
            errors.append(
                f"{name}:{line}: param_id {param_id!r} 不是三段键"
                f" <machine>.<config_id>.<量名>（首段须为 {'/'.join(MACHINES)}，"
                "config_id 不得含点号）"
            )
        else:
            machine = match.group("machine")
            machine_counts[machine] += 1

        if param_id in seen:
            errors.append(
                f"{name}:{line}: param_id {param_id!r} 重复"
                f"（首次出现在第 {seen[param_id]} 行）"
            )
        else:
            seen[param_id] = line

        if PLACEHOLDER_RE.match(xpath):
            errors.append(f"{name}:{line}: xpath {xpath!r} 是占位，应为空或真实指针")
        elif xpath and not POINTER_RE.search(xpath):
            errors.append(
                f"{name}:{line}: xpath {xpath!r} 不像真实指针（无 / : @ [ 定位符）"
            )

        ref_match = MACHINE_REF_RE.search(ref)
        if ref_match and match:
            ref_machine = ref_match.group(1)
            if ref_machine != match.group("machine"):
                errors.append(
                    f"{name}:{line}: param_id 前缀 {match.group('machine')!r} 与 "
                    f"ref 的 machine={ref_machine} 不一致"
                )

        config_match = CONFIG_REF_RE.search(ref)
        if config_match and match:
            ref_config = config_match.group(1)
            if ref_config != match.group("config_id"):
                errors.append(
                    f"{name}:{line}: param_id 的 config_id "
                    f"{match.group('config_id')!r} 与 ref 的 "
                    f"config_id={ref_config} 不一致"
                )

    return errors, machine_counts, ids


def check_ledger(path: Path) -> tuple[list[str], Counter[str], set[str]]:
    return check_ledger_rows(read_rows(path), str(path))


def check_budget_rows(
    rows: list[dict[str, str]], ledger_ids: set[str], name: str = "<budget>"
) -> list[str]:
    """预算表的 param_id 必须能解析到台账行。"""
    errors: list[str] = []
    if not rows:
        return [f"{name}: 空表或没有表头"]
    if "param_id" not in rows[0]:
        return [f"{name}: 缺少 param_id 列"]

    for line, row in enumerate(rows, start=2):
        param_id = (row.get("param_id") or "").strip()
        if param_id not in ledger_ids:
            errors.append(f"{name}:{line}: param_id {param_id!r} 在台账中找不到对应行")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ledger",
        nargs="?",
        default="docs/参数溯源.csv",
        help="台账 CSV（默认 docs/参数溯源.csv）",
    )
    parser.add_argument(
        "--budget",
        default=None,
        help="同时校验预算表 param_id 能联到台账（例如 docs/不确定度预算.csv）",
    )
    parser.add_argument(
        "--counts", action="store_true", help="通过时打印各机型行数"
    )
    args = parser.parse_args(argv)

    ledger_path = Path(args.ledger)
    try:
        errors, counts, ledger_ids = check_ledger(ledger_path)
        if args.budget:
            budget_path = Path(args.budget)
            errors += check_budget_rows(read_rows(budget_path), ledger_ids, str(budget_path))
    except OSError as exc:
        print(f"读取失败: {exc}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"\n共 {len(errors)} 处违规。", file=sys.stderr)
        return 1

    if args.counts:
        summary = ", ".join(f"{name}={counts.get(name, 0)}" for name in MACHINES)
        print(f"OK {ledger_path}: {len(ledger_ids)} 行（{summary}）")
    else:
        print(f"OK {ledger_path}: {len(ledger_ids)} 行 param_id 唯一且为三段键")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
