# -*- coding: utf-8 -*-
"""draw_report_charts.py - 报告专用图: 走资残差锚 + 走资曲线新旧对照。"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for fn in ["Microsoft YaHei", "SimHei", "PingFang SC"]:
    if fn in {f.name for f in font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = fn
        break
plt.rcParams["axes.unicode_minus"] = False

INK="#1f2937"; MUT="#6b7280"; BLUE="#2563eb"; GOLD="#d97706"
RED="#dc2626"; GREEN="#059669"; GRID="#e5e9f0"


def outflow_chart():
    df = pd.read_csv(os.path.join(ROOT, "params", "implied_outflow.csv"),
                     encoding="utf-8-sig", index_col=0, parse_dates=False)
    df.index = pd.PeriodIndex(df.index, freq="M")
    yr = df["resid_t"].resample("Y").sum()
    years = [p.year for p in yr.index]
    vals = yr.values
    fig, ax = plt.subplots(figsize=(12, 5.2), facecolor="white")
    colors = [RED if (y in (2015, 2016)) else BLUE for y in years]
    bars = ax.bar([str(y) for y in years], vals, color=colors, width=0.62, alpha=0.9)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.02, "%.2f" % v,
                ha="center", fontsize=9.5, color=INK)
    ax.axhline(0.997, color=RED, ls="--", lw=1.4)
    ax.text(len(years)-1.4, 1.05, "2015-16 危机档均值 1.00T$/年 (≈5.25% GDP)",
            fontsize=10, color=RED, ha="right")
    ax.set_ylabel("隐含资本外流 (T$/年)", color=INK)
    ax.set_title("官方月度残差拼出的资本外流序列(2015-2026)",
                 fontsize=14, fontweight="bold", color=INK)
    ax.grid(axis="y", color=GRID, alpha=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUT)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "assets", "report_outflow.png"), dpi=150,
                facecolor="white")
    plt.close(fig)
    print("saved assets/report_outflow.png")


def flight_chart():
    import policy_engine as pe
    speeds = np.arange(0.02, 0.121, 0.002)
    p40 = pe.UnifiedParams(openness=0.40)
    p25 = pe.UnifiedParams(openness=0.25)
    new40 = [pe.flight_pct_gdp(s, p40) for s in speeds]
    new25 = [pe.flight_pct_gdp(s, p25) for s in speeds]
    old40 = [0.40 * 13.3 * (0.30*s + 4.0*max(0, s-0.06)**1.5) * 100 for s in speeds]
    fig, ax = plt.subplots(figsize=(12, 5.2), facecolor="white")
    ax.plot(speeds*100, old40, color=MUT, ls="--", lw=1.6, label="旧标定(虚高, 已弃用)")
    ax.plot(speeds*100, new40, color=BLUE, lw=2.4, label="M4 新锚 · 开放度0.40")
    ax.plot(speeds*100, new25, color=GREEN, lw=2.0, label="M4 新锚 · 加严封堵0.25")
    ax.axhline(8.0, color=RED, ls="--", lw=1.4)
    ax.text(11.8, 8.3, "红线 8%GDP(危机档x1.5)", fontsize=10, color=RED, ha="right")
    ax.annotate("10%/年 = 5.3%GDP\n(≈2015-16 危机档)", xy=(10, 5.3),
                xytext=(8.0, 12.5), fontsize=10, color=INK,
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.2))
    ax.set_xlabel("年化升值速度 (%)", color=INK)
    ax.set_ylabel("资本外流强度 (% GDP)", color=INK)
    ax.set_title("走资曲线重标定:从拍脑袋到官方残差锚", fontsize=14,
                 fontweight="bold", color=INK)
    ax.legend(facecolor="white", edgecolor=GRID)
    ax.grid(color=GRID, alpha=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUT)
    ax.set_ylim(0, 34)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "assets", "report_flight.png"), dpi=150,
                facecolor="white")
    plt.close(fig)
    print("saved assets/report_flight.png")


if __name__ == "__main__":
    outflow_chart()
    flight_chart()
