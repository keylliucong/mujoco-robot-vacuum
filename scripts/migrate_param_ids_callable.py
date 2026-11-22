#!/usr/bin/env python3
"""把台账 / 预算 / 参数集里的 `param_id` 迁到契约 v1.8.4 的三段键。

键形：`<machine>.<config_id>.<量名>`（ADR-016）。

规则：
1. `machine` 取现有键首段；没有前缀时取 `ref` 的 `machine=`；
2. `config_id` 优先取该行 `ref` 里已有的 `config_id=`，没有则按机型取默认配置：
   `own -> unloaded`、`prototype -> proto_v1`、`oomwoo -> oomwoo_public_v1`；
3. 量名保持原样（含路径式量名里的点），只在 machine 后插入 config_id；
4. `ref` 里出现的旧 `param_id` 引用同步替换；
5. 预算表按台账的旧→新映射同步 `param_id`；
6. `params/*.json` 的键改用同一三段键，值、标签、来源一律不动。

脚本默认只演练；`--write` 落盘。重复运行不会产生新变化（幂等），
`--manifest` 可把每个改动文件/行/旧键/新键写成 CSV 清单。

用法：
    python scripts/migrate_param_ids_callable.py --write \
        --manifest docs/参数溯源-三段键迁移清单.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_param_ids import MACHINES, check_budget_rows, check_ledger_rows  # noqa: E402

DEFAULT_LEDGER = Path("docs/参数溯源.csv")
DEFAULT_BUDGET = Path("docs/不确定度预算.csv")
DEFAULT_PARAMS_DIR = Path("params")
DEFAULT_MANIFEST = Path("docs/参数溯源-三段键迁移清单.csv")

DEFAULT_CONFIG = {
    "own": "unloaded",
    "prototype": "proto_v1",
    "oomwoo": "oomwoo_public_v1",
}
MACHINE_REF_RE = re.compile(r"machine\s*=\s*([A-Za-z0-9_-]+)")
CONFIG_REF_RE = re.compile(r"config_id\s*=\s*([A-Za-z0-9_-]+)")
# 旧键/引用必须以完整 token 出现，不能把 oomwoo.m_dry 当成 oomwoo.m_dry_x 的前缀。
TOKEN_START = r"(?<![A-Za-z0-9_.-])"
TOKEN_END = r"(?![A-Za-z0-9_.-])"


@dataclass(frozen=True)
class Change:
    kind: str
    path: str
    line: int
    old: str
    new: str


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


def machine_from_id(param_id: str) -> str | None:
    first = param_id.split(".", 1)[0]
    return first if first in MACHINES else None


def row_machine(row: dict[str, str]) -> str:
    param_id = (row.get("param_id") or "").strip()
    from_id = machine_from_id(param_id)
    match = MACHINE_REF_RE.search(row.get("ref") or "")
    from_ref = match.group(1) if match else None
    if from_id and from_ref and from_id != from_ref:
        raise ValueError(
            f"param_id={param_id!r} 的机型号 {from_id!r} 与 ref 的 "
            f"machine={from_ref} 不一致"
        )
    machine = from_id or from_ref
    if machine not in MACHINES:
        raise ValueError(
            f"param_id={param_id!r} 无法确定机型（首段或 ref 的 machine= 须为 "
            f"{'/'.join(MACHINES)}）"
        )
    return machine


def row_config(row: dict[str, str], machine: str) -> str:
    match = CONFIG_REF_RE.search(row.get("ref") or "")
    if match:
        return match.group(1)
    return DEFAULT_CONFIG[machine]


def is_three_segment(param_id: str, machine: str, config_id: str) -> bool:
    parts = param_id.split(".", 2)
    return len(parts) == 3 and parts[0] == machine and parts[1] == config_id


def three_segment_id(param_id: str, machine: str, config_id: str) -> str:
    if is_three_segment(param_id, machine, config_id):
        return param_id
    prefix = f"{machine}."
    if param_id.startswith(prefix):
        rest = param_id[len(prefix) :]
    else:
        rest = param_id
    return f"{machine}.{config_id}.{rest}"


def replace_refs(text: str, mapping: dict[str, str]) -> str:
    for old in sorted(mapping, key=len, reverse=True):
        new = mapping[old]
        if old == new:
            continue
        text = re.sub(
            TOKEN_START + re.escape(old) + TOKEN_END,
            lambda _match, value=new: value,
            text,
        )
    return text


def migrate_ledger(
    rows: list[dict[str, str]], path: Path
) -> tuple[list[dict[str, str]], dict[str, str], list[Change]]:
    mapping: dict[str, str] = {}
    configs: dict[str, tuple[str, str]] = {}
    for row in rows:
        machine = row_machine(row)
        config_id = row_config(row, machine)
        old = (row.get("param_id") or "").strip()
        new = three_segment_id(old, machine, config_id)
        if old in mapping and mapping[old] != new:
            raise ValueError(f"同一 param_id 迁移出两个结果：{old!r} -> {mapping[old]!r}/{new!r}")
        mapping[old] = new
        configs[old] = (machine, config_id)

    changes: list[Change] = []
    migrated: list[dict[str, str]] = []
    for line, row in enumerate(rows, start=2):
        new_row = dict(row)
        old = (row.get("param_id") or "").strip()
        new = mapping[old]
        if old != new:
            changes.append(Change("param_id", str(path), line, old, new))
            new_row["param_id"] = new

        old_ref = row.get("ref") or ""
        new_ref = replace_refs(old_ref, mapping)
        if new_ref != old_ref:
            changes.append(Change("ref", str(path), line, old_ref, new_ref))
            new_row["ref"] = new_ref
        migrated.append(new_row)
    return migrated, mapping, changes


def migrate_budget(
    rows: list[dict[str, str]], mapping: dict[str, str], path: Path
) -> tuple[list[dict[str, str]], list[Change]]:
    changes: list[Change] = []
    migrated: list[dict[str, str]] = []
    for line, row in enumerate(rows, start=2):
        new_row = dict(row)
        old = (row.get("param_id") or "").strip()
        if old in mapping:
            new = mapping[old]
        elif is_generic_three_segment(old):
            new = old
        else:
            raise ValueError(f"{path}:{line}: 预算 param_id {old!r} 不在台账旧键里")
        if old != new:
            changes.append(Change("budget_param_id", str(path), line, old, new))
            new_row["param_id"] = new
        migrated.append(new_row)
    return migrated, changes


def is_generic_three_segment(param_id: str) -> bool:
    parts = param_id.split(".", 2)
    return (
        len(parts) == 3
        and parts[0] in MACHINES
        and parts[1]
        and "." not in parts[1]
        and bool(parts[2])
    )


def migrate_params_document(
    document: dict, path: Path, text: str
) -> tuple[dict, str, list[Change]]:
    machine = document.get("machine")
    config_id = document.get("config_id")
    params = document.get("params")
    if not isinstance(machine, str) or not isinstance(config_id, str):
        raise ValueError(f"{path}: 缺 machine/config_id")
    if not isinstance(params, dict):
        raise ValueError(f"{path}: 缺 params 对象")

    changes: list[Change] = []
    replacements: dict[str, str] = {}
    new_params: dict[str, dict] = {}
    for old in params:
        new = three_segment_id(old, machine, config_id)
        if new in new_params:
            raise ValueError(f"{path}: 迁移后键重复 {new!r}")
        new_params[new] = params[old]
        if old != new:
            line = next(
                (
                    index
                    for index, source_line in enumerate(text.splitlines(), start=1)
                    if re.match(r'^\s*"' + re.escape(old) + r'"\s*:', source_line)
                ),
                0,
            )
            changes.append(Change("params_key", str(path), line, old, new))
            replacements[old] = new

    new_document = dict(document)
    new_document["params"] = new_params

    # 优先做键名文本替换，保留原 JSON 的缩进、数字写法和键顺序。
    new_text = text
    for old_key, new_key in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        pattern = re.compile(
            r'(?m)^(\s*)"' + re.escape(old_key) + r'"(\s*:)'
        )
        new_text, count = pattern.subn(
            lambda match, value=new_key: match.group(1) + f'"{value}"' + match.group(2),
            new_text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"{path}: 找不到 JSON 键 {old_key!r}")
    if changes and json.loads(new_text) != new_document:
        raise ValueError(f"{path}: JSON 文本替换后与原对象不一致，拒绝写盘")
    return new_document, new_text, changes


def migrate_params_dir(
    directory: Path,
) -> tuple[dict[Path, str], list[Change]]:
    updates: dict[Path, str] = {}
    changes: list[Change] = []
    for path in sorted(directory.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        document = json.loads(text)
        _new_document, new_text, file_changes = migrate_params_document(document, path, text)
        if file_changes:
            updates[path] = new_text
            changes.extend(file_changes)
    return updates, changes


def write_manifest(path: Path, changes: list[Change]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["kind", "path", "line", "old", "new"],
            lineterminator="\n",
        )
        writer.writeheader()
        for change in changes:
            writer.writerow(
                {
                    "kind": change.kind,
                    "path": change.path,
                    "line": change.line,
                    "old": change.old,
                    "new": change.new,
                }
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--budget", type=Path, default=DEFAULT_BUDGET)
    parser.add_argument("--params-dir", type=Path, default=DEFAULT_PARAMS_DIR)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--write", action="store_true", help="落盘；不加则只演练")
    args = parser.parse_args(argv)

    try:
        ledger_fields, ledger_rows = read_csv(args.ledger)
        ledger_rows, mapping, ledger_changes = migrate_ledger(ledger_rows, args.ledger)

        budget_fields, budget_rows = read_csv(args.budget)
        budget_rows, budget_changes = migrate_budget(budget_rows, mapping, args.budget)

        params_updates, params_changes = migrate_params_dir(args.params_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"迁移失败: {exc}", file=sys.stderr)
        return 2

    changes = ledger_changes + budget_changes + params_changes

    errors, counts, ledger_ids = check_ledger_rows(ledger_rows, str(args.ledger))
    errors += check_budget_rows(budget_rows, ledger_ids, str(args.budget))
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    if args.write:
        if ledger_changes:
            write_csv(args.ledger, ledger_fields, ledger_rows)
        if budget_changes:
            write_csv(args.budget, budget_fields, budget_rows)
        for path, text in params_updates.items():
            path.write_text(text, encoding="utf-8")
    if args.manifest:
        write_manifest(args.manifest, changes)

    for change in changes:
        print(f"{change.path}:{change.line}: {change.old} -> {change.new}")
    action = "已写入" if args.write else "演练通过（未落盘，加 --write 落盘）"
    summary = ", ".join(f"{name}={counts.get(name, 0)}" for name in MACHINES)
    print(
        f"{action}: {args.ledger} {len(ledger_rows)} 行（{summary}）；"
        f"预算 {len(budget_rows)} 行；参数集 {len(params_updates)} 个文件；"
        f"共 {len(changes)} 处改动"
    )
    if args.manifest:
        print(f"清单: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
