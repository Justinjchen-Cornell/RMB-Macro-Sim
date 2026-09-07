# -*- coding: utf-8 -*-
"""draw_system_map.py - RMB-Macro-Sim v3.0 体系架构图 (浅色研报风)."""
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
ax.text(0.5, 12.25, "RMB-Macro-Sim v3.0 · 体系架构图", ha="left",
        fontsize=26, fontweight="bold", color=INK)
ax.text(0.5, 11.92, "人民币宏观政策模拟:市场情景 × 政策算法 × 交叉验证 → 表达层  |  2026-09",
        ha="left", fontsize=13.5, color=MUT)

# ---- 行 A: 数据源 ----
box(ax, 0.5, 10.9, 19.0, 0.9, "#f8fafc", LINE, "① 数据与输入",
    ["FRED(USD/CNY·CPI·失业·SLOOS·房价·财政·油价·美债)｜腾讯行情(现价·K线)｜akshare(北向·COMEX金)｜news_watch(新闻/事件表·可维护)",
     "唯一参数真源: config.yaml(市场层) + policy_engine 参数类(政策层, 待并入同一真源)"],
    ts=16, ss=11.5)

# ---- 行 B: 三大引擎列 ----
box(ax, 0.5, 7.55, 6.6, 3.0, "#eef4ff", BLUE, "② 市场情景引擎(Market)",
    ["FX 路径 (GBM, 真实校准 6.71/2.8%)", "输入性通胀 (PPI→CPI)", "出口竞争力 (Marshall-Lerner)",
     "11 行业利润冲击", "资产定价 (A股/债/金/金属)", "资本流入 (融资红利+深化)"],
    ts=16, ss=11.5, tc=BLUE)
box(ax, 7.45, 7.55, 6.2, 3.0, "#fdf3e7", GOLD, "③ 政策算法引擎(Policy)",
    ["卢氏三原则统一 (policy_engine)", "双口径去工业 (利润/GDP侵蚀)", "分层油价通胀 (EPT 0.35)",
     "S型资本 + 外储底线 + 报复博弈", "四类进口政策工具 (采购封顶)", "最小政策度 k → 政策带 5-7%"],
    ts=16, ss=11.5, tc=GOLD)
box(ax, 13.95, 7.55, 5.55, 3.0, "#f3ecfb", PUR, "④ 交叉验证层(Cross)",
    ["Deep-Risk-OPP: GOR × easing 联动", "黄金宏观验证器 (季频命中67.5%)",
     "5年油价分年推演(中国视角)", "三看板互证: 油矛·金盾·人民币"],
    ts=16, ss=11.5, tc=PUR)

# ---- 行 C: 表达/产品 ----
box(ax, 0.5, 4.35, 19.0, 2.8, "#f0fdf4", GREEN, "⑤ 表达层(产品)",
    ["Dashboard(单文件): 41档滑块 -5~15% ｜ 行业热力图 ｜ 三包络年度展望 ｜ 信号→动作 ｜ 政策算法卡 ｜ GOR×easing 联动",
     "报告: 中文/英文 PDF (9/8 页) ｜ 复刻报告 ｜ 政策统一文档 ｜ 油价推演",
     "传播: 日卡(4:5) ｜ 结论卡(1:1) ｜ 标题库 ｜ GOR Pulse Weekly #001-#006",
     "验证: 真实数据校准(FRED/腾讯/北向) ｜ 回测诊断(北向回归/汇率窗口/平缓性) ｜ 17+3 测试"],
    ts=16, ss=11.5, tc=GREEN)

# ---- 行 D: 一条逻辑流示例 ----
p = FancyBboxPatch((0.5, 2.0), 19.0, 1.9, boxstyle="round,pad=0,rounding_size=10",
                   fc="#fffbeb", ec="#fde68a", lw=1.4)
ax.add_patch(p)
ax.text(0.9, 3.55, "读一条逻辑流(示例):", fontsize=15, fontweight="bold", color="#92400e")
flow = ("FRED 读数 → easing 分 +0.30(温和宽松, 6m 回落, 仅房价支撑) → 利率战未结束 → 金是盾不加档 "
        "∥ USD/CNY 6.71(即期) → 2026 展望 6.39(-4.8%), 6.30=提前激活线 → 人民币等 2027 "
        "∥ GOR 49.1(极端) → 油主攻 → 引擎仓 50%(油30/金8/A9/现金50) → 速冻窗口 48% 现金=弹药 → 错杀三档 → 2027 重估")
ax.text(0.9, 2.85, flow, fontsize=13.5, color=INK)
ax.text(0.9, 2.18, "顺序比方向重要: 速冻(现金) → 错杀(三档买入) → 重估(2027 主线) ｜ 政策带 5-7%/年(6%: k=0.05)",
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

fig.savefig("assets/system_map.png", dpi=170, facecolor="white",
            bbox_inches="tight")
plt.close(fig)
print("assets/system_map.png saved")
