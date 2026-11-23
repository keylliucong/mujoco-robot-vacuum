"""G2 判定模块：只吃时程 + 阈值，不 import mujoco，不读模型或配置对象（S04/S09）。

契约版本：v1.11.0（文档）；判据集在 v1.7 基础上吸收 v1.8.2 的
`t_trigger` 口径（首次任一机体-台阶接触），按 v1.9.0 增加 `belly_contact`
与 `cross_fail` 失败模式，按 v1.10.0 把末态改为窗口占空比、横向越界改为
`invalid`，按 v1.10.1 增加 `invalid:lateral_drift_untrusted`，按 v1.11.0
把「越过」换成后缘量并新增 `kind=ramp` 三判退；`lateral_exit_step_width`
仍只表示几何出界（契约正文已同步）。
本文件是唯一写 `passed` / `failure_*` 的地方；输入是 CSV 列字典（字符串原样，
空串表示无数据）与一份扁平的数值参数字典。参数键集封闭，出现未知键即 raise，
因此配置无法夹带期望结果（S09）。
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right

CONTRACT_VERSION = "1.11.0"

FAILURE_PRIORITY = (
    "topple",
    "belly_contact",
    "retreat",
    "cross_fail",
    "bottom_out",
    "stall",
    "torque_limit",
    "suspension_bottom",
    "slip",
    "timeout",
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
        "end_hold_s",
        "end_duty_min",
        "end_duty_ambiguous",
        "lateral_drift_untrusted_ratio",
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
        "x_rear_B_m",
        "z_rear_m",
        "z_cg_m",
        "ramp_angle_rad",
        "ramp_length_m",
        "ramp_width_m",
        "ramp_top_platform_m",
        "ramp_top_front_m",
        "ramp_start_m",
        "ramp_start_side_tol_m",
        "ramp_top_duty",
        "post_cross_window_s",
        "ramp_detach_hold_s",
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
    if kind in ("step", "ramp"):
        # v1.8.2：t_trigger = 首次任一机体-台阶/坡面接触。旧定义只看驱动轮，
        # 台阶高于离地间隙时永不触发，会把真实托底漏成 invalid:never_contacted。
        hits = [(first_active(k), k) for k in step_pairs]
        hits = [(i, k) for i, k in hits if i is not None]
        if not hits:
            return _result(
                status="invalid",
                invalid_reason="never_contacted",
                flags=[],
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
            flags=[],
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
            flags=[],
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
    z_error_max = None
    if kind in ("step", "ramp"):
        # 跨越证据：以 heading 为前进方向把位置投影到障碍坐标系。
        # v1.11.0：判定量换成车身最后缘——s_rear = s − L_rear，
        # L_rear = x_rear_B·cosθ + (z_cg − z_rear)·sinθ（θ 取判定末帧俯仰）。
        # 质心投影只留作诊断，不再参与 passed。
        cos_h = math.cos(params["heading_rad"])
        sin_h = math.sin(params["heading_rad"])
        # 坡道的 s 原点在坡脚；台阶的 s 是台阶坐标系世界投影（step_front_m 同系）。
        s_offset = params["ramp_start_m"] if kind == "ramp" else 0.0
        end_s = end_pos_x * cos_h + end_pos_y * sin_h - s_offset
        end_lat = -end_pos_x * sin_h + end_pos_y * cos_h
        pitch_end = _value(pitch, end_index)
        l_rear = params["x_rear_B_m"] * math.cos(pitch_end) + (
            params["z_cg_m"] - params["z_rear_m"]
        ) * math.sin(pitch_end)
        com_s = end_s + params["com_offset_x_m"] * cos_h
        floor_keys = [k for k in pair_keys if k.endswith("--floor")]
        common_crossing = {
            "end_progress_m": end_s,
            "end_lateral_m": end_lat,
            "com_progress_m": com_s,
            "max_pos_z_m": max_pos_z,
            "x_rear_B_m": params["x_rear_B_m"],
            "z_rear_m": params["z_rear_m"],
            "L_rear_m": l_rear,
            "pitch_rad": pitch_end,
        }

    if kind == "step":
        wheel_on_top_count = sum(
            1 for k in wheel_step if columns[f"contact_{k}_active"][end_index] == "1"
        )
        both_wheels_on_top = bool(wheel_step) and wheel_on_top_count == len(wheel_step)
        # 没有地面接触对时不能把「查不到」当成「无接触」（诊断字段）。
        no_floor_contact_at_end = bool(floor_keys) and not any(
            columns[f"contact_{k}_active"][end_index] == "1" for k in floor_keys
        )
        reached_platform = (
            max_pos_z >= params["step_height_m"] - params["platform_height_tol_m"]
        )
        crossed_front = end_s - l_rear >= params["step_front_m"]
        # v1.10.0（S26）：末态不是一帧，是末 end_hold_s 内的占空比。
        # 灰带 [end_duty_ambiguous, end_duty_min) 判 invalid:end_state_ambiguous，
        # 不由单点阈值猜一侧。
        hold_start = bisect_left(
            times, window_end - params["end_hold_s"] - step * 0.5  # arithmetic
        )
        hold_indices = list(range(hold_start, end_index + 1))
        if not hold_indices:
            hold_indices = [end_index]
        both_on_top_flags = []
        for i in hold_indices:
            count_i = sum(
                1 for k in wheel_step if columns[f"contact_{k}_active"][i] == "1"
            )
            both_on_top_flags.append(bool(wheel_step) and count_i == len(wheel_step))
        end_frames = len(hold_indices)
        end_duty = sum(1 for flag in both_on_top_flags if flag) / end_frames
        end_state_ambiguous = (
            params["end_duty_ambiguous"] <= end_duty < params["end_duty_min"]
        )
        ended_on_platform = end_duty >= params["end_duty_min"]
        # 横向越界不是能力失败，是试验条件问题（运行时兜底；前置校验在 runner）。
        lateral_exit = abs(end_lat) > params["step_half_width_m"]
        # v1.10.1：横向漂移不可信（运行时兜底乙）。先扣掉航向本身的几何横向
        # 分量 advance·tan|ψ|——30° 斜向爬升本来就有 0.58×前进距离的横移，
        # 不扣会把正常斜向整组误判成异常。扣完仍超过前进距离的一定比例，
        # 说明这次运行的横向行为不能代表机型能力（航向控制或轮-地各向异性
        # 摩擦尚未具备），判 invalid 而非能力失败。
        advance_positive = max(advance, 0.0)
        drift_excess = abs(end_lat) - advance_positive * math.tan(
            abs(params["heading_rad"])
        )
        drift_ratio = drift_excess / max(advance_positive, params["min_advance_m"])
        drift_untrusted = drift_ratio >= params["lateral_drift_untrusted_ratio"]
        # 从首触到后缘越过前缘，机体-台阶接触允许的空档不超过上限；
        # 空档越大越像"飞过去"或"绕过去"，不是跨越。
        cross_index = end_index
        for i in window:
            s_i = pos_x[i] * cos_h + pos_y[i] * sin_h - s_offset
            if s_i - l_rear >= params["step_front_m"]:
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
        cross_fail_reasons = []
        if not crossed_front:
            cross_fail_reasons.append("front_edge_not_passed")
        if not reached_platform:
            cross_fail_reasons.append("platform_height_not_reached")
        if not ended_on_platform:
            cross_fail_reasons.append("not_ended_on_platform")
        if not contact_ok:
            cross_fail_reasons.append("step_contact_gap_too_long")
        crossing = {
            **common_crossing,
            "s_rear_m": end_s - l_rear,
            "wheel_on_top_count": wheel_on_top_count,
            "both_wheels_on_top": both_wheels_on_top,
            "no_floor_contact_at_end": no_floor_contact_at_end,
            "ended_on_platform": ended_on_platform,
            "end_duty": end_duty,
            "end_hold_s": params["end_hold_s"],
            "end_frames": end_frames,
            "end_state_ambiguous": end_state_ambiguous,
            "lateral_exit": lateral_exit,
            "lateral_drift_excess_m": drift_excess,
            "lateral_drift_ratio": drift_ratio,
            "lateral_drift_untrusted": drift_untrusted,
            "reached_platform": reached_platform,
            "crossed_front": crossed_front,
            "contact_gap_max_s": contact_gap_max,
            "contact_ok": contact_ok,
            "cross_fail_reasons": cross_fail_reasons,
            "crossed": bool(
                crossed_front and reached_platform and ended_on_platform and contact_ok
            ),
        }
    elif kind == "ramp":
        # v1.11.0 §3.2：坡道三判退（跌落 / 未登顶整体未过 / 失速）。
        # 不新增失败类别：跌落→topple、未登顶/整体未过→cross_fail、失速→stall。
        ramp_top_front = params["ramp_top_front_m"]
        end_s_rear = end_s - l_rear
        crossed_front = end_s_rear >= ramp_top_front
        # t_cross_s = s_rear 首次到达坡顶前沿；登顶占空比窗口锚在它上面，
        # 不开到 run 末端（短平台上会混进下坡帧）。
        t_cross_index = None
        for i in window:
            s_i = pos_x[i] * cos_h + pos_y[i] * sin_h - s_offset
            if s_i - l_rear >= ramp_top_front:
                t_cross_index = i
                break
        t_cross_s = times[t_cross_index] if t_cross_index is not None else None
        top_pairs = [
            k
            for k in pair_keys
            if k.startswith("wheel_") and k.endswith("--step_top")
        ]

        def both_wheels_on_ramp_top(i):
            return bool(top_pairs) and all(
                columns[f"contact_{k}_active"][i] == "1" for k in top_pairs
            )

        if t_cross_index is not None:
            top_start = bisect_left(
                times,
                times[t_cross_index]
                - params["post_cross_window_s"]
                - step * 0.5,  # arithmetic
            )
            top_indices = list(range(top_start, t_cross_index + 1))
            top_frames = len(top_indices)
            top_hits = sum(1 for i in top_indices if both_wheels_on_ramp_top(i))
            top_duty = top_hits / top_frames if top_frames else 0.0
            post_end = (
                bisect_right(
                    times,
                    times[t_cross_index] + params["post_cross_window_s"] + step * 0.5,  # arithmetic
                )
                - 1
            )
            post_cross_floor_contact = any(
                columns[f"contact_{k}_active"][i] == "1"
                for i in range(t_cross_index + 1, post_end + 1)
                for k in floor_keys
            )
        else:
            top_frames = 0
            top_duty = 0.0
            post_cross_floor_contact = False
        # 跌落：坡道接触对全为空 + pos_z ≤ z0+5 mm + 此前爬升 ≥50 mm，
        # 持续 ramp_detach_hold_s 后 latch。阈值是专家给的可执行定义（任务 C）。
        ramp_pairs = [
            k
            for k in pair_keys
            if k.endswith("--step") or k.endswith("--step_top")
        ]
        z0 = _value(pos_z, trigger_index)
        climbed = False
        detach_run = 0
        detach_frames = 0
        detached = False
        z_error_max = 0.0
        for i in window:
            dz = pos_z[i] - z0
            if dz >= 0.05:  # contract-tolerance：此前 max(pos_z−z0) ≥ 50 mm
                climbed = True
            s_i = pos_x[i] * cos_h + pos_y[i] * sin_h - s_offset
            if s_i <= 0.0:
                z_ramp = 0.0
            elif s_i >= ramp_top_front:
                z_ramp = params["ramp_length_m"] * math.sin(params["ramp_angle_rad"])
            else:
                z_ramp = s_i * math.tan(params["ramp_angle_rad"])
            z_error_max = max(z_error_max, abs(pos_z[i] - z_ramp))
            ramp_active = any(columns[f"contact_{k}_active"][i] == "1" for k in ramp_pairs)
            low = pos_z[i] <= z0 + 0.005  # contract-tolerance：z0 + 5 mm
            if climbed and not ramp_active and low:
                detach_run += 1
                detach_frames += 1
                if detach_run * step >= params["ramp_detach_hold_s"]:
                    detached = True
                    break
            else:
                detach_run = 0
        still_on_start = end_s < 0.0
        ended_on_ramp_top = (
            crossed_front
            and top_duty >= params["ramp_top_duty"]
            and not post_cross_floor_contact
        )
        cross_fail_reasons = []
        if not crossed_front:
            cross_fail_reasons.append("rear_edge_not_passed")
        if still_on_start:
            cross_fail_reasons.append("still_on_start_side")
        if top_duty < params["ramp_top_duty"]:
            cross_fail_reasons.append("ramp_top_not_reached")
        if post_cross_floor_contact:
            cross_fail_reasons.append("left_ramp_top_after_cross")
        crossing = {
            **common_crossing,
            "s_rear_m": end_s_rear,
            "ramp_top_front_m": ramp_top_front,
            "ramp_start_side_tol_m": params["ramp_start_side_tol_m"],
            "t_cross_s": t_cross_s,
            "ramp_top_duty_actual": top_duty,
            "post_cross_floor_contact": post_cross_floor_contact,
            "ramp_top_frames": top_frames,
            "detached": detached,
            "detach_frames": detach_frames,
            "still_on_start_side": still_on_start,
            "ended_on_ramp_top": ended_on_ramp_top,
            "crossed_front": crossed_front,
            "cross_fail_reasons": cross_fail_reasons,
            "crossed": bool(crossed_front and ended_on_ramp_top),
            # 与 step 分支同名的诊断键：坡道不判横向越界/灰带。
            "ended_on_platform": ended_on_ramp_top,
            "end_duty": top_duty,
            "end_state_ambiguous": False,
            "lateral_exit": False,
            "lateral_drift_excess_m": 0.0,
            "lateral_drift_ratio": 0.0,
            "lateral_drift_untrusted": False,
        }

    flags = []
    detached = bool(crossing is not None and crossing.get("detached"))
    if (
        pitch_max > params["tilt_pitch_deg"]
        or roll_max > params["tilt_roll_deg"]
        or detached
    ):
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
        flags.append("cross_fail")
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
    if not passed and not observed:
        # timeout 只在窗口内没有任何机理命中时补；否则 topple/cross_fail 等
        # 已给出主因，再追加 timeout 会让 reviewer 误读。
        flags.append("timeout")

    primary = ""
    if not passed:
        primary = next((f for f in FAILURE_PRIORITY if f in observed and f in fail_on), "")
        if not primary:
            # fail_on 未列入的观测异常也要如实报，不得一律落成 timeout。
            primary = next((f for f in FAILURE_PRIORITY if f in observed), "timeout")

    ramp_metrics = None
    if kind == "ramp" and crossing is not None:
        ramp_metrics = {
            "s_m": crossing["end_progress_m"],
            "s_rear_m": crossing["s_rear_m"],
            "z_error_m": z_error_max,
            "detach_frames": crossing["detach_frames"],
            "top_duty": crossing["ramp_top_duty_actual"],
        }
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
        "ramp": ramp_metrics,
    }
    # v1.10.0：invalid 不是失败类别——不写 failure_primary / failure_flags，
    # 也不进通过率分母。运行时横向兜底优先于灰带（几何已确定的先报）；
    # v1.10.1 的两条横向兜底同序：几何出界 → 漂移不可信 → 末态灰带。
    if crossing is not None and crossing["lateral_exit"]:
        invalid = _result(
            status="invalid",
            invalid_reason="lateral_exit_step_width",
            flags=[],
            params=params,
            metrics=metrics,
        )
        invalid["trigger_source"] = trigger_source
        return invalid
    if crossing is not None and crossing["lateral_drift_untrusted"]:
        invalid = _result(
            status="invalid",
            invalid_reason="lateral_drift_untrusted",
            flags=[],
            params=params,
            metrics=metrics,
        )
        invalid["trigger_source"] = trigger_source
        return invalid
    if crossing is not None and crossing["end_state_ambiguous"]:
        invalid = _result(
            status="invalid",
            invalid_reason="end_state_ambiguous",
            flags=[],
            params=params,
            metrics=metrics,
        )
        invalid["trigger_source"] = trigger_source
        return invalid
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
        "ramp": None,
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
    """接触力比 |Ft|/Fn 是否超过台账 μ（缺列/缺参数即输入错误）。

    力点可能正压在摩擦锥面上，浮点会给出 μ+1e-9；1e-6 相对容差只吸收
    这种数值噪声，不改变真实超限的判定。
    """
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
            if abs(tangent) / normal > mu * (1.0 + 1e-6):  # arithmetic：浮点容差
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
