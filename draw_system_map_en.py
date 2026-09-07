# -*- coding: utf-8 -*-
"""draw_system_map_en.py - RMB-Macro-Sim v3.0 system architecture (EN)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

for fn in ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"]:
    if fn in {f.name for f in font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = fn
        break

INK = "#1f2937"; MUT = "#6b7280"; BLUE = "#2563eb"; GOLD = "#d97706"
GREEN = "#059669"; RED = "#dc2626"; PUR = "#7c3aed"; LINE = "#e5e9f0"

def box(ax, x, y, w, h, fc, ec, title, subs, ts=15, ss=11.5, tc=INK):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=10",
                       fc=fc, ec=ec, lw=1.6)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h - 26, title, ha="center", va="top",
            fontsize=ts, fontweight="bold", color=tc)
    yy = y + h - 52
    for s in subs:
        ax.text(x + 16, yy, s, ha="left", va="top", fontsize=ss, color=INK)
        yy -= 26

def arrow(ax, x1, y1, x2, y2, color=BLUE, style="-|>", lw=2.2, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=18, color=color, lw=lw,
                                 linestyle=ls))

fig, ax = plt.subplots(figsize=(20, 12.6), facecolor="white")
ax.set_xlim(0, 20); ax.set_ylim(0, 12.6); ax.axis("off")

# 标题
ax.text(0.5, 12.25, "RMB-Macro-Sim v3.0 · System Architecture", ha="left",
        fontsize=26, fontweight="bold", color=INK)
ax.text(0.5, 11.92, "Market scenarios × Policy algorithm × Cross-validation → Products  |  2026-09",
        ha="left", fontsize=13.5, color=MUT)

# ---- 行 A: 数据源 ----
box(ax, 0.5, 10.9, 19.0, 0.9, "#f8fafc", LINE, "① Data & Inputs",
    ["FRED (USD/CNY, CPI, unemployment, SLOOS, housing, fiscal, oil, UST) | Tencent (spot, K-lines) | akshare (northbound, COMEX gold) | news_watch (editable event table)",
     "Single param source: config.yaml (market) + policy_engine params (policy - to be unified)  |  Light research style"],
    ts=16, ss=11.5)

# ---- 行 B: 三大引擎列 ----
box(ax, 0.5, 7.55, 6.6, 3.0, "#eef4ff", BLUE, "② Market Scenario Engine",
    ["FX path (GBM, real-calibrated 6.71 / 2.8%)", "Import inflation (PPI → CPI)", "Export competitiveness (Marshall-Lerner)",
     "11-sector profit shocks", "Asset pricing (A-shares/bonds/gold/metals)", "Capital inflow (financing + deepening)"],
    ts=16, ss=11.5, tc=BLUE)
box(ax, 7.45, 7.55, 6.2, 3.0, "#fdf3e7", GOLD, "③ Policy Algorithm Engine",
    ["Lu 3-principles unified (policy_engine)", "Dual-metric deindustrialization (profit/GDP)", "Layered oil→CPI inflation (EPT 0.35)",
     "S-curve capital + reserves floor + retaliation", "4 import tools (procurement capped)", "Min-policy-k → policy band 5-7%"],
    ts=16, ss=11.5, tc=GOLD)
box(ax, 13.95, 7.55, 5.55, 3.0, "#f3ecfb", PUR, "④ Cross-Validation",
    ["Deep-Risk-OPP: GOR × easing link", "Gold macro validator (67.5% quarterly)",
     "5-year oil drill-down (China lens)", "Three boards: oil leads · gold shields · RMB waits"],
    ts=16, ss=11.5, tc=PUR)

# ---- 行 C: 表达/产品 ----
box(ax, 0.5, 4.35, 19.0, 2.8, "#f0fdf4", GREEN, "⑤ Products & Expression",
    ["Dashboard (single file): 41-grid slider −5~15% | heatmap | 3-envelope outlook | signal→action | policy card | GOR×easing",
     "Reports: CN/EN PDF (9/8 pages) | replication & unification docs | oil drill-down",
     "Content: daily card (4:5) | 1:1 cards | headline library | GOR Pulse Weekly #001-#006",
     "QA: real-data calibration | backtests | 17+3 tests"],
    ts=16, ss=11.5, tc=GREEN)

# ---- 行 D: 一条逻辑流示例 ----
p = FancyBboxPatch((0.5, 2.0), 19.0, 1.9, boxstyle="round,pad=0,rounding_size=10",
                   fc="#fffbeb", ec="#fde68a", lw=1.4)
ax.add_patch(p)
ax.text(0.9, 3.55, "One logic flow to read it all:", fontsize=15, fontweight="bold", color="#92400e")
flow = ("FRED → easing +0.30 (mild, fading; housing only) → rate war not over → gold holds "
        "∥ USD/CNY 6.71 → 2026 outlook 6.39 (−4.8%); 6.30 = early trigger → RMB waits 2027 "
        "∥ GOR 49.1 (extreme) → oil leads → engine 50% (oil30/gold8/A9/cash50) → freeze window: 48% cash ammo → 3 tranches → 2027 re-rating")
ax.text(0.9, 2.85, flow, fontsize=13.5, color=INK)
ax.text(0.9, 2.18, "Sequencing beats direction: freeze (cash) → bargain (3 tranches) → re-rating (2027)  |  policy band 5-7%/yr (6%: k=0.05)",
        fontsize=13.5, fontweight="bold", color="#92400e")

# ---- 主链箭头 ----
arrow(ax, 3.8, 10.9, 3.8, 10.56)                      # 数据→市场
arrow(ax, 10.5, 10.9, 10.5, 10.56)                    # 数据→政策
arrow(ax, 16.7, 10.9, 16.7, 10.56)                    # 数据→交叉
arrow(ax, 3.8, 7.55, 3.8, 7.17)                       # 市场→产品
arrow(ax, 10.5, 7.55, 10.5, 7.17)                     # 政策→产品
arrow(ax, 16.7, 7.55, 16.7, 7.17)                     # 交叉→产品
arrow(ax, 7.1, 8.6, 7.45, 8.6, color=RED, ls="--")    # 市场↔政策(双口径喂给)
arrow(ax, 7.45, 8.2, 7.1, 8.2, color=RED, ls="--")
arrow(ax, 13.95, 8.6, 13.6, 8.6, color=PUR, ls="--")  # 政策↔交叉
arrow(ax, 13.6, 8.2, 13.95, 8.2, color=PUR, ls="--")

fig.savefig("assets/system_map_en.png", dpi=170, facecolor="white",
            bbox_inches="tight")
plt.close(fig)
print("assets/system_map_en.png saved")
