"""G2 判定模块：只吃时程 + 阈值，不 import mujoco，不读模型或配置对象（S04/S09）。

契约版本：v1.8.3（文档）；判据集在 v1.7 基础上吸收 v1.8.2 的
`t_trigger` 口径（首次任一机体-台阶接触），并按 G2.5 需要增加 `belly_contact`
失败模式（枚举扩展，待契约正文同步）。
本文件是唯一写 `passed` / `failure_*` 的地方；输入是 CSV 列字典（字符串原样，
空串表示无数据）与一份扁平的数值参数字典。参数键集封闭，出现未知键即 raise，
因此配置无法夹带期望结果（S09）。
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right

CONTRACT_VERSION = "1.8.3"

FAILURE_PRIORITY = (
    "data_invalid",
    "topple",
    "belly_contact",
    "retreat",
    "bottom_out",
    "stall",
    "torque_limit",
    "suspension_bottom",
    "slip",
    "timeout",
    "no_contact",
)

REQUIRED_PARAMS = frozenset(
    {
        "kind",
        "timestep_s",
        "speed_mps",
        "window_s",
        "fail_on",
        "min_advance_m",
        "recover_speed_ratio",
        "recover_hold_s",
        "stall_speed_mps",
        "stall_duration_s",
        "tilt_pitch_deg",
        "tilt_roll_deg",
        "slip_ratio",
        "contact_normal_min_n",
        "settle_tol_mps",
        "settle_window_s",
        "settle_end_s",
        "wheel_radius_m",
        "step_height_m",
        "platform_height_tol_m",
        "step_front_m",
        "step_half_width_m",
        "heading_rad",
        "com_offset_x_m",
        "contact_gap_tol_s",
        "susp_range_m",
        "susp_bottom_rel",
        "torque_limit_L_nm",
        "torque_limit_R_nm",
        "torque_saturation_rel",
        "slip_eps_mps",
        "climb_height_ratio",
        "climb_hold_s",
        "has_suspension",
        "pair_friction",
        "wheel_step_pairs",
        "bottom_out_pairs",
        "all_pairs",
    }
)


class JudgeError(ValueError):
    """判定输入不合法（缺列、参数越界）。"""


def _require(params):
    missing = REQUIRED_PARAMS.difference(params)
    extra = set(params).difference(REQUIRED_PARAMS)
    if missing:
        raise JudgeError(f"判定参数缺键：{sorted(missing)}")
    if extra:
        raise JudgeError(f"判定参数出现未定义键：{sorted(extra)}")


def _contact_columns(pair_key):
    prefix = f"contact_{pair_key}"
    return (
        f"{prefix}_active",
        f"{prefix}_normal_n",
        f"{prefix}_tangent_n",
        f"{prefix}_count",
    )


def _validate_contacts(columns, pair_keys):
    for key in pair_keys:
        active_col, normal_col, tangent_col, count_col = _contact_columns(key)
        for col in (active_col, normal_col, tangent_col, count_col):
            if col not in columns:
                raise JudgeError(f"缺接触列：{col}")
        acts = columns[active_col]
        normals = columns[normal_col]
        tangents = columns[tangent_col]
        counts = columns[count_col]
        for i, raw in enumerate(acts):
            if raw not in ("0", "1"):
                raise JudgeError(f"{active_col}[{i}] 不是 0/1：{raw!r}")
            if raw == "0":
                if normals[i] != "" or tangents[i] != "":
                    raise JudgeError(f"{key} 第 {i} 行 active=0 但力列非空（缺失≠零）")
            else:
                if normals[i] == "" or tangents[i] == "":
                    raise JudgeError(f"{key} 第 {i} 行 active=1 但力列为空")
            if counts[i] == "":
                raise JudgeError(f"{count_col}[{i}] 为空；计数 0 是真实值")
            if int(counts[i]) < 0:
                raise JudgeError(f"{count_col}[{i}] 为负")


def _floats(columns, name):
    if name not in columns:
        raise JudgeError(f"缺列：{name}")
    out = []
    for raw in columns[name]:
        if raw == "":
            out.append(None)
        else:
            value = float(raw)
            if not math.isfinite(value):
                raise JudgeError(f"{name} 出现非有限值")
            out.append(value)
    return out


def _times(columns):
    times = _floats(columns, "t_s")
    if any(t is None for t in times):
        raise JudgeError("t_s 有空值")
    return times


def judge_case(columns, params):
    """返回 {status, passed, failure_primary, failure_flags, metrics, data_quality}。"""
    _require(params)
    pair_keys = list(params["all_pairs"])
    if not timeseries_columns_complete(columns):
        raise JudgeError("时程列集合不完整")
    _validate_contacts(columns, pair_keys)

    times = _times(columns)
    if len(times) < 2:
        raise JudgeError("时程行数不足")
    step = params["timestep_s"]
    for i in range(1, len(times)):
        if not times[i] > times[i - 1]:
            raise JudgeError(f"t_s 非单调递增（第 {i} 行）")
        if abs((times[i] - times[i - 1]) - step) > step * 1e-6:  # arithmetic
            raise JudgeError(f"t_s 步长不恒定（第 {i} 行）")

    pos_x = _floats(columns, "pos_x_m")
    pos_y = _floats(columns, "pos_y_m")
    pos_z = _floats(columns, "pos_z_m")
    vel_x = _floats(columns, "vel_x_mps")
    pitch = _floats(columns, "pitch_rad")
    roll = _floats(columns, "roll_rad")
    speed_l = _floats(columns, "wheel_L_speed_radps")
    speed_r = _floats(columns, "wheel_R_speed_radps")
    torque_l = _floats(columns, "wheel_L_torque_nm")
    torque_r = _floats(columns, "wheel_R_torque_nm")
    travel_l = _floats(columns, "susp_L_travel_m")
    travel_r = _floats(columns, "susp_R_travel_m")
    has_suspension = bool(params["has_suspension"])
    if not has_suspension and any(
        value is not None for value in travel_l + travel_r
    ):
        raise JudgeError("has_suspension=0 时 susp_*_travel_m 必须整列为空，不得写 0（S22/§1.2）")

    wheel_step = [k for k in params["wheel_step_pairs"] if k in pair_keys]
    bottom_out = [k for k in params["bottom_out_pairs"] if k in pair_keys]
    step_pairs = [k for k in pair_keys if k.endswith("--step")]
    non_wheel_step = [k for k in step_pairs if k not in wheel_step]
    active = {k: columns[f"contact_{k}_active"] for k in pair_keys}

    def first_active(key):
        col = active[key]
        for i, raw in enumerate(col):
            if raw == "1":
                return i
        return None

    kind = params["kind"]
    trigger_source = ""
    if kind == "step":
        # v1.8.2：t_trigger = 首次任一机体-台阶接触。旧定义只看驱动轮，
        # 台阶高于离地间隙时永不触发，会把真实托底漏成 invalid/no_contact。
        hits = [(first_active(k), k) for k in step_pairs]
        hits = [(i, k) for i, k in hits if i is not None]
        if not hits:
            return _result(
                status="invalid",
                invalid_reason="never_contacted",
                flags=["no_contact"],
                params=params,
                metrics=_empty_metrics(),
            )
        trigger_index, trigger_source = min(hits, key=lambda item: item[0])
        wheel_hits = [first_active(k) for k in wheel_step]
        wheel_hits = [i for i in wheel_hits if i is not None]
        wheel_touch_index = min(wheel_hits) if wheel_hits else None
    else:
        trigger_index = 0
        wheel_touch_index = None
        trigger_source = "flat"
    t_trigger = times[trigger_index]
    t_wheel_touch = times[wheel_touch_index] if wheel_touch_index is not None else None

    window_end = t_trigger + params["window_s"]
    if times[-1] + step * 1e-6 < window_end:  # arithmetic
        return _result(
            status="invalid",
            invalid_reason="data_invalid",
            flags=["data_invalid", "timeout"],
            params=params,
            metrics=_empty_metrics(),
        )

    lo = bisect_left(times, t_trigger - params["settle_window_s"] - step * 0.5)  # arithmetic
    hi = trigger_index + 1
    if kind == "flat":
        settle_at = params["settle_end_s"]
        hi = bisect_right(times, settle_at)
        lo = bisect_left(times, settle_at - params["settle_window_s"] - step * 0.5)  # arithmetic
    settle_speeds = [v for v in vel_x[lo:hi] if v is not None]
    if settle_speeds and abs(_mean(settle_speeds) - params["speed_mps"]) > params["settle_tol_mps"]:
        return _result(
            status="invalid",
            invalid_reason="not_settled",
            flags=[],
            params=params,
            metrics=_empty_metrics(),
        )

    end_index = bisect_right(times, window_end) - 1
    if end_index <= trigger_index:
        return _result(
            status="invalid",
            invalid_reason="data_invalid",
            flags=["data_invalid"],
            params=params,
            metrics=_empty_metrics(),
        )
    window = range(trigger_index, end_index + 1)

    advance = _last(pos_x, end_index) - _value(pos_x, trigger_index)
    pitch_max = math.degrees(_abs_max(pitch, window))
    roll_max = math.degrees(_abs_max(roll, window))
    torque_max_l = _abs_max(torque_l, window)
    torque_max_r = _abs_max(torque_r, window)
    travel_max_l = _max(travel_l, window) if has_suspension else None
    travel_max_r = _max(travel_r, window) if has_suspension else None

    slip_l = _slip_max(speed_l, vel_x, window, params)
    slip_r = _slip_max(speed_r, vel_x, window, params)

    normal_max = 0.0
    for k in pair_keys:
        values = _floats(columns, f"contact_{k}_normal_n")
        normal_max = max(normal_max, _max(values, window))

    end_pos_z = _last(pos_z, end_index)
    end_pos_x = _last(pos_x, end_index)
    end_pos_y = _last(pos_y, end_index)
    max_pos_z = _max(pos_z, window)
    crossing = None
    if kind == "step":
        # 跨越证据（v1.8.3 返工）：机体确实从台阶前缘上方过去，而不是绕开。
        # 以 heading 为前进方向把位置投影到台阶坐标系：s 为沿前进方向进度，
        # lat 为横向偏移。台阶前缘平面过 (step_front_m, 0)，法向为 heading。
        cos_h = math.cos(params["heading_rad"])
        sin_h = math.sin(params["heading_rad"])
        end_s = end_pos_x * cos_h + end_pos_y * sin_h
        end_lat = -end_pos_x * sin_h + end_pos_y * cos_h
        # 质心投影比 B 原点略偏后，仍用同一 heading 方向换算
        com_s = end_s + params["com_offset_x_m"] * cos_h
        wheel_on_top = any(
            columns[f"contact_{k}_active"][end_index] == "1" for k in wheel_step
        )
        ended_on_platform = bool(
            wheel_on_top
            or end_pos_z >= params["step_height_m"] - params["platform_height_tol_m"]
        )
        reached_platform = (
            max_pos_z >= params["step_height_m"] - params["platform_height_tol_m"]
        )
        crossed_front = com_s >= params["step_front_m"]
        within_width = abs(end_lat) <= params["step_half_width_m"]
        # 从首触到质心越过前缘，机体-台阶接触允许的空档不超过上限；
        # 空档越大越像"飞过去"或"绕过去"，不是跨越。
        cross_index = end_index
        for i in window:
            s_i = pos_x[i] * cos_h + pos_y[i] * sin_h
            if s_i + params["com_offset_x_m"] * cos_h >= params["step_front_m"]:
                cross_index = i
                break
        contact_gap_max = _contact_gap(
            columns,
            sorted(k for k in pair_keys if k.endswith("--step")),
            trigger_index,
            cross_index,
            params["timestep_s"],
        )
        contact_ok = contact_gap_max <= params["contact_gap_tol_s"]
        crossing = {
            "end_progress_m": end_s,
            "end_lateral_m": end_lat,
            "com_progress_m": com_s,
            "max_pos_z_m": max_pos_z,
            "ended_on_platform": ended_on_platform,
            "reached_platform": reached_platform,
            "crossed_front": crossed_front,
            "within_width": within_width,
            "contact_gap_max_s": contact_gap_max,
            "contact_ok": contact_ok,
            "crossed": bool(
                crossed_front
                and within_width
                and reached_platform
                and ended_on_platform
                and contact_ok
            ),
        }

    flags = []
    if pitch_max > params["tilt_pitch_deg"] or roll_max > params["tilt_roll_deg"]:
        flags.append("topple")
    if advance < 0.0:
        flags.append("retreat")
    if kind == "step":
        wheel_touched = any(_has_active(active[k], window) for k in wheel_step)
        other_body_touched = any(_has_active(active[k], window) for k in non_wheel_step)
        # G2.5：驱动轮在整个窗口内够不到台阶，而壳体（含前下缘）/从动轮已经
        # 碰到台阶——确定、可重复的真实托底受阻，不是"没接触所以数据无效"。
        if other_body_touched and not wheel_touched:
            flags.append("belly_contact")
    if any(_has_active(active[k], window) for k in bottom_out):
        flags.append("bottom_out")
    if crossing is not None and not crossing["crossed"]:
        flags.append("bottom_out")
    if _stall(vel_x, times, window, params):
        flags.append("stall")
    if max(torque_max_l, torque_max_r) >= max(
        params["torque_limit_L_nm"], params["torque_limit_R_nm"]
    ) * (1 - params["torque_saturation_rel"]):
        flags.append("torque_limit")
    if has_suspension and max(travel_max_l, travel_max_r) >= (
        params["susp_range_m"] * params["susp_bottom_rel"]
    ):
        flags.append("suspension_bottom")
    # 打滑两条判据：运动学滑移率（轮速 vs 机体速度）与接触力比 |Ft|/Fn > μ。
    # μ 来自台账（run_cases 经 params["pair_friction"] 注入），此处不写死。
    slip_kinematic = max(slip_l, slip_r) > params["slip_ratio"]
    slip_force = _friction_exceeded(columns, pair_keys, window, params["pair_friction"])
    if slip_kinematic or slip_force:
        flags.append("slip")

    t_recover, v_recover = _recover(times, vel_x, window, params)
    t_climb = _climb(times, pos_z, trigger_index, window, params)
    recovered = t_recover is not None
    advance_ok = advance >= params["min_advance_m"]
    crossed_ok = crossing is None or crossing["crossed"]

    fail_on = set(params["fail_on"])
    hit = [f for f in flags if f in fail_on]
    passed = bool(advance_ok and recovered and crossed_ok and not hit)

    observed = list(flags)
    if not passed:
        flags.append("timeout")

    primary = ""
    if not passed:
        primary = next((f for f in FAILURE_PRIORITY if f in observed and f in fail_on), "")
        if not primary:
            # fail_on 未列入的观测异常也要如实报，不得一律落成 timeout。
            primary = next((f for f in FAILURE_PRIORITY if f in observed), "timeout")

    metrics = {
        "t_trigger_s": t_trigger,
        "t_wheel_touch_s": t_wheel_touch,
        "t_climb_s": t_climb,
        "t_recover_s": t_recover,
        "advance_m": advance,
        "v_recover_mps": v_recover,
        "pitch_max_deg": pitch_max,
        "roll_max_deg": roll_max,
        "slip_max_L": slip_l,
        "slip_max_R": slip_r,
        "torque_max_L_nm": torque_max_l,
        "torque_max_R_nm": torque_max_r,
        "susp_travel_max_L_m": travel_max_l,
        "susp_travel_max_R_m": travel_max_r,
        "contact_normal_max_n": normal_max,
        "end_pos_z_m": end_pos_z,
        "on_platform": None if crossing is None else crossing["ended_on_platform"],
        "slip_force_exceeded": slip_force,
        "trigger_source": trigger_source,
        "crossing": crossing,
    }
    result = _result(
        status="ok",
        invalid_reason="",
        flags=flags,
        params=params,
        metrics=metrics,
        passed=passed,
        primary=primary,
    )
    result["trigger_source"] = trigger_source
    return result


def timeseries_columns_complete(columns):
    required = [
        "t_s",
        "pos_x_m",
        "pos_y_m",
        "pos_z_m",
        "quat_w",
        "quat_x",
        "quat_y",
        "quat_z",
        "pitch_rad",
        "roll_rad",
        "yaw_rad",
        "vel_x_mps",
        "vel_y_mps",
        "vel_z_mps",
        "wheel_L_speed_radps",
        "wheel_R_speed_radps",
        "wheel_L_torque_nm",
        "wheel_R_torque_nm",
        "susp_L_travel_m",
        "susp_R_travel_m",
        "chassis_min_z_m",
    ]
    return all(name in columns for name in required)


def _result(status, invalid_reason, flags, params, metrics, passed=None, primary=""):
    ordered = [f for f in FAILURE_PRIORITY if f in flags]
    return {
        "status": status,
        "invalid_reason": invalid_reason,
        "passed": passed,
        "failure_primary": primary,
        "failure_flags": ordered,
        "metrics": metrics,
        "conclusion_level_inputs": {
            "fail_on": list(params["fail_on"]),
            "window_s": params["window_s"],
        },
    }


def _empty_metrics():
    return {
        "t_trigger_s": None,
        "t_wheel_touch_s": None,
        "t_climb_s": None,
        "t_recover_s": None,
        "advance_m": None,
        "v_recover_mps": None,
        "pitch_max_deg": None,
        "roll_max_deg": None,
        "slip_max_L": None,
        "slip_max_R": None,
        "torque_max_L_nm": None,
        "torque_max_R_nm": None,
        "susp_travel_max_L_m": None,
        "susp_travel_max_R_m": None,
        "contact_normal_max_n": None,
        "end_pos_z_m": None,
        "on_platform": None,
        "slip_force_exceeded": None,
        "trigger_source": "",
        "crossing": None,
    }


def _value(series, index):
    value = series[index]
    if value is None:
        raise JudgeError("时程关键列为空")
    return value


def _last(series, index):
    for i in range(index, -1, -1):
        if series[i] is not None:
            return series[i]
    raise JudgeError("时程关键列全空")


def _mean(values):
    return sum(values) / len(values)


def _abs_max(series, indices):
    values = [abs(series[i]) for i in indices if series[i] is not None]
    return max(values) if values else 0.0


def _max(series, indices):
    values = [series[i] for i in indices if series[i] is not None]
    return max(values) if values else 0.0


def _has_active(column, indices):
    return any(column[i] == "1" for i in indices)


def _contact_gap(columns, keys, start, stop, step):
    """区间 [start, stop] 内"所有机体-台阶接触同时为空"的最长连续时长。"""
    worst = 0.0
    gap = 0.0
    for i in range(start, stop + 1):
        active = any(columns[f"contact_{key}_active"][i] == "1" for key in keys)
        if active:
            gap = 0.0
        else:
            gap += step
            worst = max(worst, gap)
    return worst


def _slip_max(speed_rad, vel_x, indices, params):
    radius = params["wheel_radius_m"]
    eps = params["slip_eps_mps"]
    out = 0.0
    for i in indices:
        if speed_rad[i] is None or vel_x[i] is None:
            continue
        v_wheel = speed_rad[i] * radius
        out = max(out, abs(v_wheel - vel_x[i]) / max(abs(v_wheel), eps))
    return out


def _friction_exceeded(columns, pair_keys, indices, pair_friction):
    """接触力比 |Ft|/Fn 是否超过台账 μ（缺列/缺参数即输入错误）。"""
    for key in pair_keys:
        if key not in pair_friction:
            raise JudgeError(f"缺接触对 {key} 的摩擦参数")
        mu = float(pair_friction[key])
        normals = _floats(columns, f"contact_{key}_normal_n")
        tangents = _floats(columns, f"contact_{key}_tangent_n")
        for i in indices:
            normal = normals[i]
            tangent = tangents[i]
            if normal is None or tangent is None or normal <= 0.0:
                continue
            if abs(tangent) / normal > mu:
                return True
    return False


def _stall(vel_x, times, indices, params):
    need = params["stall_duration_s"]
    threshold = params["stall_speed_mps"]
    start = None
    for i in indices:
        speed = vel_x[i]
        slow = speed is not None and abs(speed) < threshold
        if slow and start is None:
            start = times[i]
        if not slow and start is not None:
            if times[i] - start >= need:
                return True
            start = None
    if start is not None and times[indices[-1]] - start >= need:
        return True
    return False


def _recover(times, vel_x, indices, params):
    target = params["recover_speed_ratio"] * params["speed_mps"]
    hold = params["recover_hold_s"]
    start = None
    for i in indices:
        speed = vel_x[i]
        if speed is not None and speed >= target:
            if start is None:
                start = i
            elif times[i] - times[start] >= hold:
                lo = start
                hi = i
                values = [v for v in vel_x[lo : hi + 1] if v is not None]
                return times[start] - times[indices[0]], _mean(values)
        else:
            start = None
    return None, None


def _climb(times, pos_z, trigger_index, indices, params):
    base = pos_z[trigger_index]
    if base is None:
        raise JudgeError("pos_z 在触发点为空")
    target = base + params["climb_height_ratio"] * params["step_height_m"]
    if params["step_height_m"] <= 0.0:
        return None
    start = None
    for i in indices:
        value = pos_z[i]
        if value is not None and value >= target:
            if start is None:
                start = i
            elif times[i] - times[start] >= params["climb_hold_s"]:
                return times[start] - times[trigger_index]
        else:
            start = None
    return None
