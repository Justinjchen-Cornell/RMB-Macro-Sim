"""
可视化脚本 (Visualization)
======================
基于 model.py 的输出，生成一套完整的宏观场景推演图表。
设计风格：深色金融风（呼应 PPT 模板）

运行: python visualize.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib import font_manager

# ── 中文字体自动探测 (跨平台: Windows/macOS/Linux) ──────────
_CJK_FONTS = ["Microsoft YaHei", "SimHei", "PingFang SC",
              "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Source Han Sans SC"]

def _setup_cjk_font():
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CJK_FONTS:
        if name in available:
            rcParams["font.family"] = name
            return name
    return None

_setup_cjk_font()

# ── 全局样式 ──────────────────────────────────────────────────
rcParams["axes.unicode_minus"] = False
rcParams["figure.dpi"] = 150
rcParams["axes.titleweight"] = "bold"
rcParams["font.size"] = 10

# 浅色研报风配色 (券商研报: 纸白底 + 墨色文字 + 高识别度色)
BG = "#ffffff"           # 画布纸白
PANEL = "#f8fafc"        # 面板微灰
GRID = "#e5e9f0"         # 细分隔线
TEXT = "#1f2937"         # 墨色正文
MUTED = "#6b7280"        # 次级文字
ACCENT_GOLD = "#d97706"  # 金/净效益
ACCENT_RED = "#dc2626"   # 损失/下行
ACCENT_GREEN = "#059669" # 收益/上行
ACCENT_BLUE = "#2563eb"  # 主色(汇率/A股)
ACCENT_VIOLET = "#7c3aed"
ACCENT_CYAN = "#0891b2"


def setup_ax(ax):
    """统一浅色研报轴样式"""
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#cbd5e1")
        ax.spines[s].set_linewidth(0.8)
    ax.grid(color=GRID, alpha=0.6, lw=0.7)


def plot_fx_scenarios(all_paths: dict, save_path: str):
    """汇率路径对比 (多情景)"""
    fig, ax = plt.subplots(figsize=(11, 6), facecolor=BG)
    setup_ax(ax)

    colors = {"快速升值(10%)": ACCENT_RED, "基准(6%)": ACCENT_GOLD,
              "慢速升值(3%)": ACCENT_GREEN, "不升值(0%)": ACCENT_BLUE}
    years = range(6)

    for name, path in all_paths.items():
        median = np.median(path, axis=0)
        ax.plot(years, median, color=colors[name], lw=2.5, label=name)
        p25 = np.percentile(path, 25, axis=0)
        p75 = np.percentile(path, 75, axis=0)
        ax.fill_between(years, p25, p75, color=colors[name], alpha=0.12)

    ax.axhline(6.7108, color=TEXT, ls="--", alpha=0.5, lw=1)
    ax.text(0.1, 7.25, "基准 6.71", color=TEXT, fontsize=9)

    ax.set_title("USD/CNY 路径模拟：四种升值情景对比", color=TEXT, fontsize=15, fontweight="bold", pad=15)
    ax.set_xlabel("年", color=TEXT)
    ax.set_ylabel("USD/CNY", color=TEXT)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=10, loc="upper right")
    fig.tight_layout()
    fig.savefig(save_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def plot_industry_heatmap(industry_df: pd.DataFrame, save_path: str):
    """行业利润热力图 (年份 × 行业)"""
    fig, ax = plt.subplots(figsize=(13, 7), facecolor=BG)
    setup_ax(ax)

    # 转置: 行=行业, 列=年份
    data = industry_df.T.values
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=-0.15, vmax=0.15)

    ax.set_xticks(range(len(industry_df)))
    ax.set_xticklabels(industry_df.index, color=TEXT)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels(industry_df.columns, color=TEXT, fontsize=9)

    # 数值标注
    for i in range(len(data)):
        for j in range(len(data[i])):
            val = data[i][j]
            color = "white" if abs(val) > 0.08 else TEXT
            ax.text(j, i, f"{val:.1%}", ha="center", va="center", color=color, fontsize=8)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("利润冲击", color=TEXT)
    cbar.ax.yaxis.set_tick_params(color=TEXT)
    cbar.outline.set_edgecolor(GRID)

    ax.set_title("行业利润冲击热力图 (行=行业, 列=年份)", color=TEXT, fontsize=15, fontweight="bold", pad=15)
    fig.tight_layout()
    fig.savefig(save_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def plot_asset_radar(asset_data: dict, save_path: str):
    """资产收益雷达图 (多角度对比)"""
    from math import pi

    fig, ax = plt.subplots(figsize=(8, 8), facecolor=BG, subplot_kw=dict(polar=True))
    ax.set_facecolor(PANEL)

    categories = list(asset_data.keys())
    N = len(categories)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    values = list(asset_data.values())
    values += values[:1]

    ax.plot(angles, values, color=ACCENT_GOLD, lw=2.5)
    ax.fill(angles, values, color=ACCENT_GOLD, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color=TEXT, fontsize=11)
    ax.set_ylim(0, 0.15)
    ax.spines["polar"].set_color(GRID)
    ax.grid(color=GRID, alpha=0.5)
    ax.tick_params(colors=TEXT)

    ax.set_title("资产收益结构对比 (5年中位年化)", color=TEXT, fontsize=14, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(save_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def plot_transmission_chain(save_path: str):
    """传导链条示意图"""
    fig, ax = plt.subplots(figsize=(14, 5), facecolor=BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.axis("off")

    steps = [
        ("汇率升值\n(政策/市场)", ACCENT_GOLD, 1.5),
        ("输入性通胀\nPPI→CPI", ACCENT_RED, 4.0),
        ("出口竞争力\nMarshall-Lerner", ACCENT_BLUE, 6.5),
        ("行业利润重估\n赢家 vs 输家", ACCENT_GREEN, 9.0),
        ("资产价格\n权益/债券/商品", ACCENT_GOLD, 11.5),
    ]

    for i, (text, color, x) in enumerate(steps):
        # 方框
        rect = plt.Rectangle((x - 1.0, 1.2), 2.0, 1.6, facecolor=PANEL,
                             edgecolor=color, lw=2.5, transform=ax.transData)
        ax.add_patch(rect)
        ax.text(x, 2.0, text, ha="center", va="center", color=TEXT, fontsize=10, fontweight="bold")

        # 箭头
        if i < len(steps) - 1:
            next_x = steps[i + 1][2]
            ax.annotate("", xy=(next_x - 1.1, 2.0), xytext=(x + 1.1, 2.0),
                       arrowprops=dict(arrowstyle="-|>", color=TEXT, lw=2))

    ax.text(7, 3.5, "宏观传导链条：人民币升值 → 资产重估", ha="center", color=TEXT, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(save_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def plot_capital_waterfall(capital: dict, save_path: str):
    """
    成本-收益瀑布图: 出口损失 → 融资红利 → 资本深化 → 净效益 (T$)
    capital: ScenarioEngine.run()['capital_inflow'] 或 CapitalInflowModule.compute() 输出
    """
    fig, ax = plt.subplots(figsize=(11, 6.2), facecolor=BG)
    setup_ax(ax)

    labels = ["出口部门\n利润损失", "资本净流入\n(融资红利)", "资本深化\n(GDP增量)", "净效益"]
    vals = [capital["export_loss"], capital["cumulative_inflow"],
            capital["deepening_gain"], capital["net_benefit"]]

    # 瀑布步进
    start = 0.0
    steps = [0.0]
    for v in vals[:-1]:
        start += v
        steps.append(start)
    start += vals[-1]

    colors = [ACCENT_RED, ACCENT_GREEN, ACCENT_GREEN, ACCENT_GOLD]
    x = np.arange(len(labels))
    bottoms = [0.0]
    # 负项从0向下, 正项从当前累计起点向上
    seg_bottoms = [0.0]
    seg_heights = [vals[0]]
    acc = vals[0]
    for v in vals[1:-1]:
        if v >= 0:
            seg_bottoms.append(acc)
        else:
            seg_bottoms.append(acc + v)
        seg_heights.append(v)
        acc += v
    seg_bottoms.append(acc if vals[-1] >= 0 else 0.0)
    seg_heights.append(vals[-1])

    bars = ax.bar(x, seg_heights, bottom=seg_bottoms, width=0.58,
                  color=colors, alpha=0.88, edgecolor="none")
    for i, (v, b) in enumerate(zip(vals, seg_bottoms)):
        y_pos = b + (v if v >= 0 else 0) + (0.06 if v >= 0 else -0.06)
        va = "bottom" if v >= 0 else "top"
        ax.text(x[i], y_pos, f"{v:+.2f} T$", ha="center", va=va,
                fontsize=12, fontweight="bold", color=TEXT)
    # 虚线连接累计线
    cum = 0.0
    for i in range(len(vals) - 1):
        cum += vals[i]
        ax.plot([x[i] + 0.3, x[i + 1] - 0.3], [cum, cum], color=GRID, ls="--", lw=1.2)

    ax.axhline(0, color=TEXT, lw=1, alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, color=TEXT)
    ax.set_ylabel("T$ (5年累计)", color=TEXT)
    ax.set_title("人民币升值净效益瀑布 — 出口成本 vs 资本流入收益", fontsize=14, color=TEXT)
    ax.set_ylim(min(min(vals), -0.6), max(acc, 3.2) * 1.12)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor=BG)
    plt.close(fig)


def plot_capital_inflow_trends(capital: dict, save_path: str):
    """
    三渠道年度流入堆叠图 (A股/债市/FDI, T$/年) + 存量线
    capital: ScenarioEngine.run()['capital_inflow']
    """
    by = capital["by_year"]                 # 行: Y1..Y5
    years = list(range(1, len(by) + 1))
    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=BG)
    setup_ax(ax)

    ax.stackplot(years,
                 by["equity"], by["bond"], by["fdi"],
                 labels=["A股", "中国债市", "FDI"],
                 colors=[ACCENT_GOLD, ACCENT_BLUE, ACCENT_GREEN], alpha=0.85)

    ax.plot(years, by["total"], color=TEXT, lw=2, marker="o",
            markersize=5, label="年度总流入")
    for x, t in zip(years, by["total"]):
        ax.annotate(f"{t:.2f}", (x, t), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, color=TEXT)
    ax.legend(facecolor=PANEL, labelcolor=TEXT, loc="upper left")
    ax.set_xlabel("年份", color=TEXT)
    ax.set_ylabel("净流入 (T$)", color=TEXT)
    ax.set_title("全球资本涌入人民币资产 — 分渠道年度净流入 (美元流动性稀缺情景)",
                 fontsize=13, color=TEXT)
    ax.set_xticks(years)
    ax.set_ylim(0, float(by["total"].max()) * 1.5)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, facecolor=BG)
    plt.close(fig)


def plot_sensitivity_table(sensitivity_df: pd.DataFrame, save_path: str):
    """敏感性分析表格图"""
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=BG)
    ax.axis("off")

    # 表格
    n_rows, n_cols = sensitivity_df.shape
    tbl = ax.table(cellText=sensitivity_df.round(3).values,
                   rowLabels=sensitivity_df.index,
                   colLabels=sensitivity_df.columns,
                   cellLoc="center", rowLoc="center",
                   loc="center")

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1.2, 1.8)

    # 样式
    for (row, col), cell in tbl.get_celld().items():
        cell.set_facecolor(PANEL)
        cell.set_text_props(color=TEXT)
        cell.set_edgecolor(GRID)
        if row == 0:  # 表头
            cell.set_facecolor("#2a2a5a")
            cell.set_text_props(color=ACCENT_GOLD, fontweight="bold")
        elif col > 0:  # 数据列，根据正负着色
            val = sensitivity_df.values[row - 1, col - 1]
            if val < 0:
                cell.set_text_props(color=ACCENT_RED)
            else:
                cell.set_text_props(color=ACCENT_GREEN)

    ax.set_title("敏感性分析：升值速度 → 行业利润 & 资产收益", color=TEXT, fontsize=14, fontweight="bold", pad=15)
    fig.tight_layout()
    fig.savefig(save_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    """独立运行演示 (无需 model.py 也能生成示意图)"""
    import os
    out_dir = "/data/workspace/macro_sim/charts"
    os.makedirs(out_dir, exist_ok=True)

    # 传导链条
    plot_transmission_chain(f"{out_dir}/chain.png")
    print("[✓] chain.png")

    # 示意热力图
    np.random.seed(42)
    industries = ["export_lowend", "export_hightech", "domestic_consumption",
                  "real_estate", "new_energy", "semiconductor",
                  "commodity_metals", "power_compute", "gold", "bank_insurance"]
    demo_df = pd.DataFrame(
        np.random.uniform(-0.12, 0.12, (5, len(industries))),
        index=[f"Y{i}" for i in range(5)],
        columns=industries
    )
    plot_industry_heatmap(demo_df, f"{out_dir}/heatmap.png")
    print("[✓] heatmap.png")

    # 示意雷达
    plot_asset_radar(
        {"A股加权": 0.08, "中国国债": 0.025, "黄金": 0.12, "工业金属": 0.07},
        f"{out_dir}/radar.png"
    )
    print("[✓] radar.png")

    # 示意敏感性表
    sens = pd.DataFrame({
        "低端制造": [-0.14, -0.08, -0.04, 0.0],
        "半导体": [0.06, 0.04, 0.02, 0.0],
        "金属/黄金": [0.12, 0.08, 0.04, 0.0],
        "A股加权": [0.05, 0.03, 0.01, 0.0],
    }, index=["快速(10%)", "基准(6%)", "慢速(3%)", "不升值"])
    plot_sensitivity_table(sens, f"{out_dir}/sensitivity.png")
    print("[✓] sensitivity.png")

    print(f"\n图表已保存至 {out_dir}/")


# ──────────────────────────────────────────────────────────────
#  情景巨幕图 (Scenario Wall) — 一张图讲完 A/B/C 三情景对比
# ──────────────────────────────────────────────────────────────
def plot_scenario_wall(scenarios: dict, save_path: str,
                       row_labels: list = None,
                       title: str = None):
    """
    scenarios: {"A_原假设": results, "B_实测参数": results, "C_现实惯性": results}
    3 x 3 布局:
      行 = 情景 | 列 = [USD/CNY 路径带 | 行业利润冲击(Y5) | 资本净效益瀑布(T$)]
    """
    names = list(scenarios.keys())
    n = len(names)
    fig, axes = plt.subplots(n, 3, figsize=(15.5, 3.1 * n), facecolor=BG)
    if n == 1:
        axes = axes.reshape(1, -1)

    col_heads = ["USD/CNY 路径 (中位+25-75%)",
                 "行业利润冲击 Y5 (相对基准)",
                 "资本净效益瀑布 (5年累计, T$)"]
    for c, ch in enumerate(col_heads):
        axes[0][c].set_title(ch, fontsize=11.5, pad=10, color=TEXT)

    order_inds = ["export_lowend", "export_hightech", "new_energy",
                  "domestic_consumption", "real_estate", "infrastructure",
                  "semiconductor", "commodity_metals", "power_compute",
                  "bank_insurance", "gold"]

    for i, (name, r) in enumerate(scenarios.items()):
        # col 0: fx fan
        ax = axes[i][0]
        fx = r["fx_path"]
        yrs = list(range(fx.shape[1]))
        med = np.median(fx, axis=0)
        lo = np.percentile(fx, 25, axis=0)
        hi = np.percentile(fx, 75, axis=0)
        ax.plot(yrs, med, color=ACCENT_BLUE, lw=2.2)
        ax.fill_between(yrs, lo, hi, color=ACCENT_BLUE, alpha=0.14)
        ax.set_ylim(float(med.min()) * 0.97, float(med.max()) * 1.03)
        ax.annotate("终值 %.2f" % med[-1], xy=(yrs[-1], med[-1]),
                    xytext=(4, 4), textcoords="offset points",
                    fontsize=9, color=ACCENT_BLUE, fontweight="bold")
        setup_ax(ax)

        # col 1: industry bars
        ax = axes[i][1]
        fin = r["industry_profit"].iloc[-1]
        fin = fin.reindex([k for k in order_inds if k in fin.index]).dropna()
        vals = fin.values
        cols = [ACCENT_RED if v < 0 else ACCENT_GREEN for v in vals]
        bars = ax.barh(range(len(vals)), vals * 100, color=cols, alpha=0.88, height=0.62)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels([k.replace("_", " ") for k in fin.index], fontsize=8.5, color=TEXT)
        for bi, v in enumerate(vals):
            ax.text(v * 100 + (0.4 if v >= 0 else -0.4), bi, ("%+.0f%%" % (v * 100)),
                    va="center", ha="left" if v >= 0 else "right",
                    fontsize=8, color=MUTED)
        ax.axvline(0, color="#94a3b8", lw=0.8)
        ax.set_xlim(-40, 22)
        setup_ax(ax)

        # col 2: waterfall
        ax = axes[i][2]
        cap = r["capital_inflow"]
        labels = ["出口损失", "融资红利", "资本深化", "净效益"]
        vals_w = [cap["export_loss"], cap["cumulative_inflow"],
                  cap["deepening_gain"], cap["net_benefit"]]
        xs = np.arange(4)
        bottoms = [0.0]
        acc = vals_w[0]
        bottoms.append(acc)
        acc += vals_w[1]
        bottoms.append(acc)
        acc += vals_w[2]
        bottoms.append(0.0 if vals_w[3] >= 0 else vals_w[3])
        colors_w = [ACCENT_RED, ACCENT_GREEN, ACCENT_GREEN, ACCENT_GOLD]
        ax.bar(xs, vals_w, bottom=bottoms, width=0.55, color=colors_w, alpha=0.9)
        for xi, v in enumerate(vals_w):
            yp = bottoms[xi] + (v if v >= 0 else 0) + 0.05
            va = "bottom" if v >= 0 else "top"
            ax.text(xi, yp, "%+.2f" % v, ha="center", va=va, fontsize=9,
                    fontweight="bold", color=TEXT)
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, fontsize=9, color=TEXT)
        ax.axhline(0, color="#94a3b8", lw=0.8)
        ax.set_ylim(min(min(vals_w), -0.8), 3.4)
        setup_ax(ax)

        # row label
        fig.text(0.006, (n - i - 0.5) / n, name, rotation=90, va="center", ha="center",
                 fontsize=10.5, fontweight="bold", color=MUTED)

    if title:
        fig.suptitle(title, fontsize=14.5, fontweight="bold", color=TEXT, y=0.995)
    fig.tight_layout(rect=[0.025, 0.01, 1, 0.975 if title else 0.99])
    fig.savefig(save_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print("  [scenario_wall] %s" % save_path)
