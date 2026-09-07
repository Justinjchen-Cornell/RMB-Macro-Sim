# -*- coding: utf-8 -*-
"""draw_maps.py - RMB-Macro-Sim v3.0 simplified system map (zh/en)."""
import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

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
GREEN = "#059669"; PUR = "#7c3aed"; LINE = "#e5e9f0"

T = {
"zh": {
 "title": "RMB-Macro-Sim v3.0 · 体系图(简化版)",
 "sub": "免费数据 → 两个引擎 + 一个交叉验证 → 一个仪表盘",
 "data": "① 数据: FRED · 腾讯行情 · akshare · news_watch(新闻事件表)",
 "m_t": "② 市场引擎 会怎样?",
 "m_b": ["汇率 → 通胀/出口/行业", "资产 + 资本流入", "41 档滑块情景"],
 "p_t": "③ 政策引擎 该怎样?",
 "p_b": ["卢氏三原则量化", "双口径红线 · 最小政策度 k", "政策带 5-7%/年"],
 "c_t": "④ 交叉验证 现在到哪?",
 "c_b": ["GOR × easing 联动", "5 年油价分年推演"],
 "prod": "⑤ 产品: Dashboard(政策卡/热力/展望/信号) · 中英 PDF · 日卡/周报",
 "flow": "一条流: easing +0.30 → 金是盾不加 ∥ USD/CNY 6.71 → 6.39(2026) ∥ GOR 49.1 → 油主攻 → 50% 仓, 48% 现金等速冻 → 错杀三档 → 2027 重估",
},
"en": {
 "title": "RMB-Macro-Sim v3.0 · System Map (simplified)",
 "sub": "Free data → two engines + one cross-check → one dashboard",
 "data": "① Data: FRED · Tencent · akshare · news_watch",
 "m_t": "② Market engine — what happens?",
 "m_b": ["FX → inflation/exports/sectors", "assets + capital inflows", "41-grid scenarios"],
 "p_t": "③ Policy engine — what should?",
 "p_b": ["Lu 3 principles quantified", "dual redlines · min-policy k", "band 5-7%/yr"],
 "c_t": "④ Cross-check — where now?",
 "c_b": ["GOR × easing link", "5-year oil drill-down"],
 "prod": "⑤ Products: Dashboard · CN/EN PDFs · daily/weekly content",
 "flow": "easing +0.30 → gold holds ∥ USD/CNY 6.71 → 6.39 (2026) ∥ GOR 49.1 → oil leads → 50% in, 48% cash → 3 tranches → 2027 re-rating",
},
}

def box(ax, x, y, w, h, fc, ec, title, subs, tc, title_s=15.5, sub_s=12):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=10",
                       fc=fc, ec=ec, lw=1.6)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h - 20, title, ha="center", va="top",
            fontsize=title_s, fontweight="bold", color=tc)
    yy = y + h - 46
    for s in subs:
        ax.text(x + w / 2, yy, s, ha="center", va="top", fontsize=sub_s, color=INK)
        yy -= 24

def arrow(ax, x1, y1, x2, y2, color=BLUE, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=16, color=color, lw=2.2,
                                 linestyle=ls))

def draw(lang, out):
    t = T[lang]
    fig, ax = plt.subplots(figsize=(14.4, 8.0), facecolor="white")
    ax.set_xlim(0, 14.4); ax.set_ylim(0, 8.0); ax.axis("off")
    ax.text(0.4, 7.62, t["title"], fontsize=20, fontweight="bold", color=INK)
    ax.text(0.4, 7.25, t["sub"], fontsize=12.5, color=MUT)

    box(ax, 0.4, 6.15, 13.6, 0.85, "#f8fafc", LINE, t["data"], [], INK,
        title_s=14, sub_s=12)

    box(ax, 0.4, 3.9, 4.2, 2.0, "#eef4ff", BLUE, t["m_t"], t["m_b"], BLUE)
    box(ax, 5.1, 3.9, 4.2, 2.0, "#fdf3e7", GOLD, t["p_t"], t["p_b"], GOLD)
    box(ax, 9.8, 3.9, 4.2, 2.0, "#f3ecfb", PUR, t["c_t"], t["c_b"], PUR)

    box(ax, 0.4, 2.35, 13.6, 0.95, "#f0fdf4", GREEN, t["prod"], [], GREEN,
        title_s=14, sub_s=12)

    ax.add_patch(FancyBboxPatch((0.4, 0.45), 13.6, 1.4,
                 boxstyle="round,pad=0,rounding_size=10",
                 fc="#fffbeb", ec="#fde68a", lw=1.4))
    ax.text(0.4 + 13.6 / 2, 1.5, t["flow"], ha="center", va="center",
            fontsize=12, fontweight="bold", color="#92400e")

    arrow(ax, 7.2, 6.15, 2.5, 5.9)
    arrow(ax, 7.2, 6.15, 7.2, 5.9)
    arrow(ax, 7.2, 6.15, 11.9, 5.9)
    arrow(ax, 2.5, 3.9, 2.5, 3.3)
    arrow(ax, 7.2, 3.9, 7.2, 3.3)
    arrow(ax, 11.9, 3.9, 11.9, 3.3)

    fig.savefig(out, dpi=170, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("saved", out)

if __name__ == "__main__":
    draw("zh", "assets/system_map.png")
    draw("en", "assets/system_map_en.png")
