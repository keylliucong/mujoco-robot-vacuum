"""Generate the report figures from committed evidence and one archived trace."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.patches import Rectangle
import numpy as np


HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parents[1] / "验证输出"
REJUDGE = "2026-11-23_"
BLUE, ORANGE, GREEN, GREY = "#0072B2", "#D55E00", "#009E73", "#687780"
COLORS = {"cleared": BLUE, "blocked": ORANGE, "invalid": GREY}
MARKERS = {"cleared": "o", "blocked": "s", "invalid": "x"}
WIDE = 183 / 25.4


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def evidence(name, tail="summary.csv"):
    return rows(EVIDENCE / f"{REJUDGE}{name}-rejudge-v1.11.0" / tail)


def figure(tag, title, height, bottom=0.20, left=0.13, top=0.81, width=WIDE):
    fig = plt.figure(figsize=(width, height))
    fig.subplots_adjust(left=left, right=0.96, bottom=bottom, top=top)
    fig.text(0.035, 0.94, f"{tag}  {title}", va="top", fontsize=8.5, weight="bold")
    return fig


def save(fig, filename, note):
    fig.text(0.035, 0.045, note, va="bottom", fontsize=7, color="#36454d", linespacing=1.45)
    fig.savefig(HERE / f"{filename}.png", dpi=300, facecolor="white")
    plt.close(fig)


def point(ax, x, y, outcome):
    key = outcome.split(":")[0]
    ax.scatter(x, y, s=24, color=COLORS[key], marker=MARKERS[key], zorder=3)


def f1():
    fig = figure("F1", "仿真闸口已建立，本机证据仍待补齐", 2.55, bottom=0.23, left=0.05)
    ax = fig.add_subplot()
    ax.set(xlim=(0, 7), ylim=(0, 1))
    ax.axis("off")
    gates = [
        ("G0", "输入冻结", "进行中", "老板（待签）"),
        ("G1", "读数校验", "已达成", "仿真专家已签"),
        ("G2", "原型入口", "有条件达成", "架构师／仿真专家*"),
        ("G3", "扫描验证", "进行中", "总签字方待确认"),
        ("G4", "本机标定", "进行中", "试验标定／仿真专家"),
        ("G5", "独立验证", "未开始", "签字方待确认"),
        ("G6", "结论定级", "未开始", "老板（待签）"),
    ]
    colors = [ORANGE, GREEN, GREEN, ORANGE, ORANGE, GREY, GREY]
    for i, ((gate, name, status, signer), color) in enumerate(zip(gates, colors)):
        ax.text(i + 0.5, 0.82, gate, ha="center", weight="bold", fontsize=8)
        ax.text(i + 0.5, 0.65, name, ha="center")
        ax.plot([i + 0.11, i + 0.89], [0.54, 0.54], color=color, lw=2.5)
        ax.text(i + 0.5, 0.33, status, color=color, ha="center")
        ax.text(i + 0.5, 0.13, signer, ha="center", fontsize=7)
        if i < 6:
            ax.annotate("", (i + 1.10, 0.54), (i + 0.9, 0.54),
                        arrowprops={"arrowstyle": "->", "color": "#707a80", "lw": 0.7})
    save(fig, "F1-gates", "* G2 责任方据看板，有条件收口据 D-14。G4 已有模板，实测标定待执行。\n"
         "流程反映交付成熟度。本机测量不确定度未标定，G6 尚无产品性能结论。")


def f2(ts, first):
    fig = figure("F2", "20 mm 在不同模型与台阶设置下给出不同判定", 3.8, bottom=0.24, left=0.15, top=0.83)
    ax1, ax2 = fig.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.52})
    for ax in (ax1, ax2):
        ax.set_yticks(range(3), ["invalid", "blocked", "cleared"])
        ax.set_ylim(-0.35, 2.75)
        ax.set_xlim(8.8, 31.0)
        ax.grid(axis="y", color="#e4eaed", lw=0.55)
    y = {"invalid": 0, "blocked": 1, "cleared": 2}
    ax1.set_title("A  OOMWOO 正对尖棱 · v1.11.0 · 2 / 5 ms 控制周期", loc="left", fontsize=8)
    ax1.axvspan(10, 12.5, color="#EAF4F9", zorder=0)
    for height in (10, 12.5, 20):
        outcome = ts[2][height, 2]["report_outcome"]
        assert all(ts[2][height, dt]["report_outcome"] == outcome for dt in (2, 1, .5))
        assert ts[5][height, 2]["report_outcome"] == outcome
        point(ax1, height, y[outcome], outcome)
    support = rows(EVIDENCE / "2026-11-22_G2.5-前缘三档" / "g25-step30_summary.csv")[0]
    assert support["passed"] == "0"
    ax1.scatter(30, 1, s=26, facecolors="white", edgecolors=ORANGE, marker="s", zorder=3)
    ax1.annotate("G2.5 独立批次\nv1.9.0", (30, 1), (25.1, 1.48), fontsize=7,
                 arrowprops={"arrowstyle": "-", "lw": 0.65})
    ax1.text(12.7, 2.04, "夹逼区间 (10, 12.5] mm", color=BLUE, va="center")
    ax2.set_title("B  通用原型正对圆角 · 2 ms 时步 · v1.11.0", loc="left", fontsize=8)
    heights = [10, 12.5, 15, 17.5, 20]
    for height in heights:
        key = f"height_h{height:.1f}".replace(".", "p")
        outcome = next(row["report_outcome"] for row in first if row["batch"] == key)
        point(ax2, height, y[outcome], outcome)
    ax2.text(20.8, 2, "20 mm 为最高采样点", va="center", color=BLUE)
    point(ax2, 15, 0, "invalid")
    ax2.annotate("v1.9 报告层历史点：孤立不可判\n非单调表象", (15, 0), (17.2, 0.33),
                 fontsize=7, color=GREY, arrowprops={"arrowstyle": "-", "lw": 0.65})
    ax2.set_xticks([10, 12.5, 15, 17.5, 20, 25, 30])
    ax2.set_xlabel("台阶高度 (mm)")
    save(fig, "F2-obstacle-boundary", "A：2 ms 控制周期覆盖 2 / 1 / 0.5 ms 时步，5 ms 只覆盖 2 ms 时步。B：15 mm 历史点单独标注。\n"
         "20 ms 控制周期见 F3，斜向诊断见 F7。模型参数未标定，夹逼仅适用于 A 的已采样设置。")


def f3(ts):
    fig = figure("F3", "物理时步与控制周期分别检查", 3.35, bottom=0.25, left=0.19, top=0.74)
    grid = fig.add_gridspec(3, 3, height_ratios=(2, .33, 1), hspace=0.15, wspace=0.25)
    for column, height in enumerate((10, 12.5, 20)):
        for panel, periods in ((0, (2, 5)), (2, (20,))):
            ax = fig.add_subplot(grid[panel, column])
            ax.set(xlim=(-.5, 2.5), ylim=(len(periods) - .5, -.5))
            ax.set_frame_on(False)
            for iy, period in enumerate(periods):
                for ix, dt in enumerate((2, 1, .5)):
                    row = ts[period].get((height, dt))
                    outcome = row["report_outcome"].split(":")[0] if row else "未跑"
                    color = COLORS.get(outcome, GREY) if panel == 0 else GREY
                    detail = ""
                    if panel == 2 and height == 10:
                        detail = f'\nduty {float(row["end_duty"]):.2f}'
                    ax.add_patch(Rectangle((ix - .46, iy - .44), .92, .88, color=color,
                                           alpha=.14 if row else .06, lw=0))
                    ax.text(ix, iy, outcome + detail, ha="center", va="center", color=color, fontsize=7)
            ax.set_yticks(range(len(periods)), [f"{p} ms" for p in periods] if column == 0 else [""] * len(periods))
            ax.tick_params(length=0, pad=4)
            if panel == 0:
                ax.set_title(f"{height:g} mm", fontsize=8)
                ax.set_xticks(range(3), ["2", "1", "0.5"])
                ax.tick_params(top=True, labeltop=True, labelbottom=False)
            else:
                ax.set_xticks([])
    fig.text(0.045, 0.62, "控制\n周期", color=GREY, va="center")
    fig.text(0.045, 0.32, "判定\n不可用", color=GREY, va="center", weight="bold")
    fig.text(0.035, 0.80, "物理时步 (ms)", color=GREY)
    save(fig, "F3-control-timestep", "OOMWOO 节点按 v1.11.0；灰带仅列失效时的 judge 标签。50 Hz 保持原增益，判定不可用。\n"
         "仅夹逼带宽阈值 (50, 200] Hz。接触未标定；12.5 mm 的失败主因随时步分叉。")


def f4():
    fig = figure("F4", "三项参数改动后的采样结果", 3.5, bottom=0.24, left=0.14, top=0.83)
    axs = fig.subplots(3, 1, sharex=True, gridspec_kw={"hspace": 0.63})
    source = evidence("G3-第二批")
    groups = [
        ("g3_b2_friction_", "摩擦降低  轮–地 0.8 → 0.5  /  轮–阶 0.6 → 0.5"),
        ("g3_b2_torque_", "轮端限扭降低  0.15 → 0.09 N·m（低扭参考的 0.6 倍）"),
        ("g3_b2_speed_", "接近速度提高  0.15 → 0.25 m/s（增加 0.10 m/s）"),
    ]
    for ax, (prefix, title) in zip(axs, groups):
        ax.set_title(title, loc="left", fontsize=8)
        ax.set(xlim=(8.8, 22.4), ylim=(-.4, 1.25))
        ax.set_yticks([])
        ax.axhline(0, lw=.65, color="#E2E7EA")
        used = [r for r in source if r["repeat"] == "1" and r["case_id"].startswith(prefix)]
        for row in used:
            height = float(row["case_id"].split("_h")[-1].replace("p", "."))
            outcome = row["report_outcome"]
            point(ax, height, 0, outcome)
            ax.text(height + .2, .26, row["failure_primary"] or outcome,
                    color=COLORS[outcome], fontsize=7)
    axs[-1].set_xticks([10, 12.5, 15, 17.5, 20])
    axs[-1].set_xlabel("台阶高度 (mm)")
    save(fig, "F4-parameter-sweeps", "OOMWOO 基准，工程扫描设置，设备参数未标定。仅这三项，不排序；每项各跑 2–3 个高度。\n"
         "原判 v1.10.1，v1.11.0 重判一致。缺同高基准对照，无法估计通过高度变化量。")


def f5(archive):
    summary = rows(EVIDENCE / "2026-11-22_G3-第一批" / "height_h15p0_summary.csv")[0]
    data = rows(archive)
    trigger = float(summary["t_trigger_s"])
    recover = float(summary["t_recover_s"])
    t = np.array([float(r["t_s"]) - trigger for r in data])
    x = np.array([float(r["pos_x_m"]) for r in data])
    x -= x[np.argmin(abs(t))]
    names = [name for name in data[0] if name.startswith("contact_") and name.endswith("_normal_n")]
    force = np.array([max(float(r[name] or 0) for name in names) for r in data])
    assert np.isclose(force[(t >= -1e-8) & (t <= 8)].max(), float(summary["contact_normal_max_n"]))
    threshold = 5 * 10.94
    fig = figure("F5", "越障时程含短促数值峰，恢复时间随判据定义", 3.65, bottom=0.22, top=0.87)
    axf, axx = fig.subplots(2, 1, sharex=True, gridspec_kw={"hspace": .19})
    axf.plot(t, force, color=BLUE, lw=.9)
    axf.axhline(threshold, color=ORANGE, lw=.75, ls="--")
    axf.text(7.94, threshold + 5, "5× 假设静态轮载 = 54.7 N", ha="right", color=ORANGE)
    axf.annotate("145.2 N（数值峰）", (t[np.argmax(force)], force.max()), (1.38, 129),
                 arrowprops={"arrowstyle": "-", "lw": .7})
    axx.plot(t, x, color=GREEN, lw=1.1)
    axx.axvline(0, color=GREY, lw=.7, ls=":")
    axx.axvline(recover, color=BLUE, lw=.7, ls="--")
    axx.annotate(f"恢复  +{recover:.3f} s", xy=(recover, .22), xytext=(1.08, .35), color=BLUE,
                 arrowprops={"arrowstyle": "-", "lw": .7, "color": BLUE})
    axx.text(-.08, .27, "首次触阶", ha="right", color=GREY)
    over = (force > threshold) & (t >= 0) & (t <= 8)
    edges = np.flatnonzero(np.diff(np.r_[False, over, False])).reshape(-1, 2)
    for start, stop in edges:
        for ax in (axf, axx):
            ax.axvspan(t[start] - .001, t[stop - 1] + .001, color=ORANGE, alpha=.3, lw=0)
    axx.set(xlim=(-.85, 8.05), xlabel="相对首次触阶时间 (s)", ylabel="前向位移 (m)")
    axf.set_ylabel("接触对法向力最大值 (N)")
    save(fig, "F5-contact-history", "通用原型正对 15 mm，G3 第一批原始 2 ms 时程；橙带为逐帧 >5×，法向取接触局部坐标。\n"
         "位移以首次触阶为零点；恢复为 judge 诊断。接触及静态轮载未标定，峰值不用于强度估算。")


def f6(ts_rows, first):
    fig = figure("F6", "判据升级对同一时程的影响", 3.25, bottom=0.19, left=0.05, top=0.83)
    ax = fig.add_subplot()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    headers = ["同一时程示例", "v1.9.x", "v1.10.x", "v1.11.0"]
    x_pos = (.00, .44, .63, .82)
    examples = [
        ("原型 15 mm 正对（2 ms）", "blocked", "cleared", "cleared"),
        ("OOMWOO 10 mm，50 Hz（2 ms）", "cleared", "invalid", "invalid"),
        ("OOMWOO 10 mm，50 Hz（1 ms）", "cleared", "blocked", "blocked"),
    ]
    for x, title in zip(x_pos, headers):
        ax.text(x, .92, title, weight="bold")
    for i, example in enumerate(examples):
        y = .76 - i * .15
        ax.axhline(y + .095, lw=.6, c="#DCE5E8")
        for x, label in zip(x_pos, example):
            ax.text(x, y, label, c=COLORS.get(label, "#24353C"))
    latest = evidence("G2") + first + evidence("G3-第二批") + ts_rows
    changes = sum(r["report_outcome"] != r["legacy_report_outcome"] for r in latest)
    assert (changes, len(latest)) == (0, 118)
    ax.text(.00, .20, f"v1.10.x → v1.11.0    全轮 outcome 翻转 {changes}/{len(latest)}", color=BLUE, weight="bold")
    ax.text(.00, .06, "failure_primary 变化 0 格  ·  新增诊断 16 格（G2：12；G3 第一批：4）")
    save(fig, "F6-judge-versions", "上表为同一时程样例。v1.10 改末态读法，v1.11 改用后缘；旧版存在翻转。\n"
         "0/118 仅覆盖后两版重判的留档格，不能用于预测其他工况；设备参数未标定。")


def f7(first):
    fig = figure("F7", "两格斜向回归点贴近后缘零点，仍由横移判无效", 2.9, bottom=0.28, top=0.80)
    ax, check = fig.subplots(1, 2, gridspec_kw={"wspace": .44})
    cases = ["bis_p15_h15p0", "bis_m15_h15p0"]
    case_rows = [next(r for r in first if r["batch"] == case) for case in cases]
    margin = [float(row["new_margin_m"]) * 1000 for row in case_rows]
    tolerance = .02 * 170
    for panel in (ax, check):
        panel.axvline(0, color=GREY, lw=.7, ls=":")
        panel.set_yticks([1, 0], ["+15°", "-15°"] if panel is ax else ["", ""])
        panel.set_ylim(-.46, 1.5)
    ax.axvspan(-20, 20, color="#EAF4F9", zorder=0)
    ax.errorbar(margin, [1, 0], xerr=tolerance, color=BLUE, fmt="o", ms=4, capsize=3)
    ax.set(xlim=(-23, 23), xlabel="后缘余量 (mm)")
    for i, value in enumerate(margin):
        ax.annotate(f"{value:.3f}", (value, 1 - i), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=7, color=BLUE)
    check.errorbar([0, 0], [1, 0], xerr=tolerance, color=GREEN, fmt="o", ms=4, capsize=3)
    check.set(xlim=(-5, 5), xlabel="两种几何派生的偏差 (mm)")
    check.text(.2, 1.29, "两格均为 0 mm", color=GREEN)
    save(fig, "F7-critical-regression", "通用原型 15 mm 台阶，v1.11.0；阴影为 ±20 mm 入列带。误差棒为 2% ≈ ±3.4 mm 自检容差\n"
         "（左图仅作尺度参照）；实测不确定度未标定。两格均横移越界，余量只作诊断。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="Sans-serif font with CJK coverage")
    parser.add_argument("--archive", type=Path, required=True, help="Archived prototype height_h15p0 timeseries.csv")
    args = parser.parse_args()
    fontManager.addfont(args.font)
    plt.rcParams.update({
        "font.family": FontProperties(fname=args.font).get_name(),
        "font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": .65, "xtick.major.width": .65, "ytick.major.width": .65,
        "axes.unicode_minus": False, "axes.labelcolor": "#25363e", "text.color": "#25363e",
        "xtick.color": "#384b53", "ytick.color": "#384b53",
    })
    ts = {}
    ts_rows = []
    for period in (2, 5, 20):
        batch = evidence("G3-时步", f"{period}ms/summary.csv")
        ts_rows.extend(batch)
        ts[period] = {
            (float(row["case_id"].split("_")[1][4:].replace("p", ".")),
             float(row["timestep_s"]) * 1000): row
            for row in batch if row["repeat"] == "1" and row["tier"] == "base"
        }
    first = evidence("G3-第一批")
    f1()
    f2(ts, first)
    f3(ts)
    f4()
    f5(args.archive)
    f6(ts_rows, first)
    f7(first)


if __name__ == "__main__":
    main()
