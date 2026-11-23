"""按当前契约重判既有批次时程（不重跑仿真）。

用法（Windows，项目 .venv）：

    .venv\\Scripts\\python.exe scripts\\rejudge_cases.py ^
        --root outputs\\g3-b1 ^
        --out outputs\\g3-b1-rejudge-v1100 ^
        --summary-csv docs\\验证输出\\2026-11-22_G3-第一批-v1.10.0\\rejudge_summary.csv

为什么不改 run_cases.py：run_cases 的职责是「跑 + 判 + 写批次」，重判只需要
「读既有 timeseries + 调 judge」。本脚本复用 run_cases 的参数组装函数，但
不重跑 mujoco 动力学，也不写 summary.csv（summary 列冻结，报告层结果另行落盘）。

对每个 batch：
- 从 run.json 取 case JSON、repeat/tier 目录与 timestep；
- 用 v1.10.0 的 _runner.json 重建 judge 参数（含 end_hold_s / end_duty_* /
  obstacle_half_width_m）；
- 先做 v1.10.0 前置横向校验（step_too_narrow_for_heading）：不通过则整批
  标 reject（v1.11.0 起它是配置拒绝码，不是 invalid），不再看运行时判据；
- 否则调用 judge.judge_case 重判该 tier 的 timeseries.csv。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import mujoco  # noqa: E402

import judge  # noqa: E402
import model_checks  # noqa: E402
import params_io  # noqa: E402
import run_cases  # noqa: E402

SUMMARY_COLUMNS = [
    "batch",
    "case_id",
    "repeat",
    "tier",
    "timestep_s",
    "status",
    "passed",
    "invalid_reason",
    "failure_primary",
    "failure_flags",
    "report_outcome",
    "end_duty",
    "end_hold_s",
    "end_frames",
    "end_state_ambiguous",
    "lateral_exit",
    "crossed",
    "cross_fail_reasons",
    "advance_m",
    "t_recover_s",
    "contact_normal_max_n",
    "precheck_ok",
    "precheck_need_half_width_m",
    "precheck_bench_half_width_m",
    "scenario_xml_sha256",
    "config_sha256",
    "output_dir",
]


def read_timeseries(path):
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"空 timeseries：{path}")
    return {name: [row[name] for row in rows] for name in rows[0]}


def load_case_context(config_path):
    """与 run_cases.main 同口径地准备模型/台账/判据参数所需的常量。"""
    config = run_cases.load_case(config_path)
    defaults = run_cases.load_runner_defaults()

    model_rel = config["model"]["path"]
    model_path = (REPO_ROOT / model_rel).resolve()
    if run_cases.sha256_file(model_path) != config["model"]["sha256"]:
        raise run_cases.ContractError("模型 sha256 与配置不符")
    rendered = params_io.load_and_render(model_path, None)
    params_document = rendered["params"]
    run_cases.check_front_lip_derived(params_document)
    model_text = rendered["text"]

    ledger, _labels = run_cases.load_ledger_rows(
        params_document["machine"], params_document["config_id"]
    )
    radius = model_checks.ledger_value(ledger, "geom.wheel_radius_m")
    run_cases.MODEL_CONSTANTS["wheel_radius_m"] = radius
    run_cases.MODEL_CONSTANTS["susp_range_m"] = model_checks.ledger_value(
        ledger, "susp.travel_limit_m"
    )
    run_cases.MODEL_CONSTANTS["com_offset_B_m"] = model_checks.declared_com_offset(
        ledger
    )
    platform_tol = model_checks.ledger_value(ledger, "judge.platform_height_tol_m")
    pair_friction = run_cases.config_friction_from_ledger(config, ledger)

    config_id = run_cases.parse_config_id(config)
    if params_document["config_id"] != config_id:
        raise run_cases.ContractError("case 的 config_id 与参数集不一致")

    base_model = mujoco.MjModel.from_xml_string(model_text)
    base_data = mujoco.MjData(base_model)
    mujoco.mj_forward(base_model, base_data)
    has_suspension = model_checks.read_capability(base_model, "has_suspension")
    body_length_m = model_checks.body_length(base_model)
    chassis_front_m = run_cases.chassis_front(base_model)
    _pair_lookup, ordered_pairs = run_cases.build_pair_lookup(
        config, config["scenario"]["kind"]
    )

    stage = config["scenario"]
    step_front_m = (
        chassis_front_m + stage["approach"]["start_distance_m"]
        if stage["kind"] == "step"
        else 0.0
    )

    precheck = None
    if stage["kind"] == "step":
        min_advance_m = config["judge"]["min_advance_body_lengths"] * body_length_m
        body_half_width_m = run_cases.chassis_half_width(base_model)
        margin_body_half = float(defaults["lateral_margin_body_half"])
        heading_rad = math.radians(stage["heading_deg"])
        need_half_width_m = (
            abs(math.tan(heading_rad)) * (min_advance_m + body_length_m)
            + margin_body_half * body_half_width_m
        )
        bench_half_width_m = float(defaults["obstacle_half_width_m"])
        precheck = {
            "ok": bench_half_width_m >= need_half_width_m,
            "need_half_width_m": need_half_width_m,
            "bench_half_width_m": bench_half_width_m,
            "min_advance_m": min_advance_m,
            "body_length_m": body_length_m,
            "body_half_width_m": body_half_width_m,
            "margin_body_half": margin_body_half,
            "heading_deg": stage["heading_deg"],
        }

    return {
        "config": config,
        "defaults": defaults,
        "model_text": model_text,
        "ledger": ledger,
        "radius": radius,
        "platform_tol": platform_tol,
        "pair_friction": pair_friction,
        "has_suspension": has_suspension,
        "body_length_m": body_length_m,
        "step_front_m": step_front_m,
        "ordered_pairs": ordered_pairs,
        "precheck": precheck,
    }


def rejudge_tier(ctx, timeseries_path, timestep_s, limits, scenario_sha, config_sha, output_dir, wrapper="baseline"):
    model = mujoco.MjModel.from_xml_string(ctx["model_text"])
    model.opt.timestep = float(timestep_s)
    if float(model.opt.timestep) != float(timestep_s):
        raise RuntimeError("timestep 回读不一致")
    params = run_cases.build_judge_params(
        ctx["config"],
        ctx["defaults"],
        model,
        limits,
        ctx["ordered_pairs"],
        ctx["body_length_m"],
        ctx["radius"],
        ctx["has_suspension"],
        ctx["pair_friction"],
        ctx["platform_tol"],
        ctx["step_front_m"],
    )
    if wrapper == "oomwoo":
        # 与 scripts/run_oomwoo.py 的补丁一致：OOMWOO 无被动悬挂，
        # susp_* 是占位铰；judge 用 1 m 名义行程避免永远报 suspension_bottom。
        params["susp_range_m"] = 1.0
    table = read_timeseries(timeseries_path)
    verdict = judge.judge_case(table, params)
    crossing = (verdict.get("metrics") or {}).get("crossing") or {}

    precheck = ctx["precheck"]
    if precheck is not None and not precheck["ok"]:
        # v1.11.0：step_too_narrow_for_heading 是配置拒绝码，不是运行期 invalid。
        status = "reject"
        invalid_reason = ""
        passed = None
        primary = ""
        flags = []
        report_outcome = "reject:step_too_narrow_for_heading"
    else:
        status = verdict["status"]
        invalid_reason = verdict.get("invalid_reason") or ""
        passed = verdict.get("passed")
        primary = verdict.get("failure_primary") or ""
        flags = verdict.get("failure_flags") or []
        if status == "invalid":
            report_outcome = "invalid:" + invalid_reason if invalid_reason else "invalid"
        elif status == "ok" and passed:
            report_outcome = "cleared"
        elif status == "ok":
            report_outcome = "blocked"
        else:
            report_outcome = status

    metrics = verdict.get("metrics") or {}
    return {
        "row": {
            "status": status,
            "passed": "" if passed is None else int(passed),
            "invalid_reason": invalid_reason,
            "failure_primary": primary,
            "failure_flags": ";".join(flags),
            "report_outcome": report_outcome,
            "end_duty": crossing.get("end_duty", ""),
            "end_hold_s": crossing.get("end_hold_s", ""),
            "end_frames": crossing.get("end_frames", ""),
            "end_state_ambiguous": crossing.get("end_state_ambiguous", ""),
            "lateral_exit": crossing.get("lateral_exit", ""),
            "crossed": crossing.get("crossed", ""),
            "cross_fail_reasons": ";".join(crossing.get("cross_fail_reasons") or []),
            "advance_m": metrics.get("advance_m", ""),
            "t_recover_s": metrics.get("t_recover_s", ""),
            "contact_normal_max_n": metrics.get("contact_normal_max_n", ""),
            "precheck_ok": "" if precheck is None else bool(precheck["ok"]),
            "precheck_need_half_width_m": (
                "" if precheck is None else precheck["need_half_width_m"]
            ),
            "precheck_bench_half_width_m": (
                "" if precheck is None else precheck["bench_half_width_m"]
            ),
            "scenario_xml_sha256": scenario_sha,
            "config_sha256": config_sha,
            "output_dir": output_dir,
        },
        "verdict": verdict,
        "precheck": precheck,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="按当前 judge 重判既有批次时程")
    parser.add_argument("--root", required=True, help="既有批次根目录（含 <batch>/run.json）")
    parser.add_argument("--out", required=True, help="重判 JSON 输出目录")
    parser.add_argument("--summary-csv", default=None, help="汇总 CSV（可选）")
    parser.add_argument(
        "--wrapper",
        choices=("baseline", "oomwoo"),
        default="baseline",
        help="台账与 runner 默认值：baseline=docs/参数溯源.csv + cases/_runner.json；oomwoo=试跑台账 + _runner_oomwoo.json",
    )
    args = parser.parse_args(argv)
    if args.wrapper == "oomwoo":
        run_cases.LEDGER_PATH = REPO_ROOT / "docs" / "试跑" / "参数溯源-oomwoo.csv"
        run_cases.RUNNER_DEFAULTS = REPO_ROOT / "cases" / "_runner_oomwoo.json"

    root = Path(args.root)
    if not root.is_absolute():
        root = REPO_ROOT / root
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for batch_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        run_json_path = batch_dir / "run.json"
        if not run_json_path.exists():
            continue
        run_json = json.loads(run_json_path.read_text(encoding="utf-8"))
        case = run_json["cases"][0]
        config_path = REPO_ROOT / case["config"]
        ctx = load_case_context(config_path)
        limits = {
            name: float(ctx["config"]["drive"]["channels"][name]["torque_limit_nm"])
            for name in ("wheel_L", "wheel_R")
        }
        batch_rows = []
        for repeat in case["repeats"]:
            for tier in repeat["tiers"]:
                tier_dir = (batch_dir / tier["dir"]).resolve()
                ts = tier_dir / "timeseries.csv"
                if not ts.exists():
                    raise RuntimeError(f"缺 timeseries：{ts}")
                result = rejudge_tier(
                    ctx,
                    ts,
                    tier["timestep_s"],
                    limits,
                    case["scenario_xml_sha256"],
                    case["config_sha256"],
                    tier["dir"],
                    wrapper=args.wrapper,
                )
                row = {
                    "batch": batch_dir.name,
                    "case_id": case["case_id"],
                    "repeat": repeat["repeat"],
                    "tier": tier["tier"],
                    "timestep_s": tier["timestep_s"],
                }
                row.update(result["row"])
                rows.append(row)
                batch_rows.append({"row": row, "verdict": result["verdict"]})
                print(
                    f"{batch_dir.name} r{repeat['repeat']} {tier['tier']}: "
                    f"{row['report_outcome']} end_duty={row['end_duty']} "
                    f"crossed={row['crossed']}"
                )
        payload = {
            "source_batch": str(batch_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
            "contract_version": judge.CONTRACT_VERSION,
            "wrapper": args.wrapper,
            "precheck": ctx["precheck"],
            "tiers": batch_rows,
        }
        (out_dir / f"{batch_dir.name}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    if args.summary_csv:
        summary_path = Path(args.summary_csv)
        if not summary_path.is_absolute():
            summary_path = REPO_ROOT / summary_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"wrote {len(rows)} tier rows; out={out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        run_cases.ContractError,
        params_io.ParamError,
        model_checks.ModelCheckError,
        judge.JudgeError,
    ) as error:
        print(f"CONTRACT ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
