# -*- coding: utf-8 -*-
"""
build_report.py - Generate detailed Chinese research report (HTML + PDF)
=========================================================================
Combines engine scenario data (dashboard_data.json) + calibration results
(calib_results.json) + charts into a professional research-report styled
HTML, then converts to PDF via headless Microsoft Edge.

Usage:  python build_report.py   (writes report/*.html and *.pdf)
"""
import os, io, json, base64, subprocess, datetime, sys

BASE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.join(BASE, "report")
os.makedirs(REP, exist_ok=True)
sys.path.insert(0, BASE)

DASH = json.load(open(os.path.join(BASE, "dashboard_data.json"), encoding="utf-8"))
CAL = json.load(open(os.path.join(BASE, "calib_results.json"), encoding="utf-8"))

def img64(rel):
    p = os.path.join(BASE, rel)
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def g(key):
    return DASH["presets"].find(lambda x: False) if False else None

def preset(key):
    for x in DASH["presets"]:
        if x["key"] == key:
            return x
    return DASH["presets"][2]

def fmt_t(v):
    return ("%+.2f" % v) + " T$"

NOW = datetime.datetime.now().strftime("%Y年%m月%d日")

P6 = preset("p6")
P0 = preset("p0")
P10 = preset("p10")
P6C = preset("p6c")
P6X = preset("p6x")
P6R = preset("p6r")
PIV = preset("piv")

IND_CN = {"export_lowend": "低端制造", "export_hightech": "高新出口",
          "domestic_consumption": "消费", "real_estate": "地产",
          "infrastructure": "基建", "new_energy": "新能源",
          "semiconductor": "半导体", "commodity_metals": "工业金属",
          "power_compute": "算力/电力", "gold": "黄金",
          "bank_insurance": "银行保险"}

# ---------------- helpers ----------------
def table(rows, head=None, cls="tbl"):
    out = ['<table class="%s">' % cls]
    if head:
        out.append("<thead><tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>")
    out.append("<tbody>")
    for r in rows:
        tds = []
        for c in r:
            c = str(c)
            css = ""
            if c.startswith("+"):
                css = ' class="up"'
            elif c.startswith("-") and "%" in c or c.startswith("-") and "T$" in c:
                css = ' class="dn"'
            tds.append("<td%s>%s</td>" % (css, c))
        out.append("<tr>" + "".join(tds) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)

# ---------------- industry rows helper ----------------
def ind_rows(p, order=None):
    items = sorted(p["industry"].items(), key=lambda kv: kv[1], reverse=True)
    if order:
        items = [(k, p["industry"][k]) for k in order if k in p["industry"]]
    rows = []
    for k, v in items:
        rows.append([IND_CN.get(k, k), ("%+.1f%%" % v)])
    return rows

# ---------------- HTML head ----------------
def head_css():
    return """
<style>
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
  color: #1f2937; line-height: 1.62; margin: 0; font-size: 10.5pt;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 21pt; margin: 0 0 2mm; line-height: 1.25; }
h2 { font-size: 14pt; border-left: 4px solid #2563eb; padding-left: 8px;
  margin: 9mm 0 3mm; }
h3 { font-size: 11.5pt; margin: 5mm 0 2mm; color: #1d4ed8; }
p { margin: 2mm 0; text-align: justify; }
.muted { color: #6b7280; font-size: 9pt; }
.tagline { color: #6b7280; font-size: 10.5pt; margin-bottom: 4mm; }
.rule { border-top: 2.5px solid #1f2937; margin: 2mm 0; }
.rule2 { border-top: 1px solid #cbd5e1; margin: 2mm 0; }
.cov { display: flex; justify-content: space-between; align-items: flex-end; }
.badge { display: inline-block; background: #eef2ff; color: #4338ca;
  border: 1px solid #c7d2fe; border-radius: 999px; padding: 1mm 3.5mm;
  font-size: 8.5pt; font-weight: 600; }
.kbox { display: flex; gap: 3mm; flex-wrap: wrap; margin: 3mm 0; }
.kcard { flex: 1; min-width: 30mm; border: 1px solid #e5e9f0; border-radius: 3mm;
  padding: 3mm 4mm; background: #f8fafc; }
.kcard .v { font-size: 15pt; font-weight: 800; }
.kcard .l { font-size: 8.5pt; color: #6b7280; }
.gold { color: #d97706; } .up { color: #059669; } .dn { color: #dc2626; }
.tbl { width: 100%; border-collapse: collapse; margin: 2.5mm 0; font-size: 9pt; }
.tbl th { background: #f1f5f9; border-bottom: 1.2px solid #cbd5e1; padding: 1.6mm;
  text-align: left; }
.tbl td { border-bottom: 1px solid #e5e9f0; padding: 1.6mm; }
.tbl tr:nth-child(even) td { background: #fafbfc; }
img.chart { width: 100%; border: 1px solid #e5e9f0; border-radius: 2mm;
  margin: 2mm 0; }
.callout { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid
  #d97706; padding: 3mm 4mm; border-radius: 2mm; margin: 3mm 0; }
.note { background: #eff6ff; border: 1px solid #bfdbfe; padding: 2.5mm 4mm;
  border-radius: 2mm; font-size: 9pt; color: #1e40af; margin: 2.5mm 0; }
.foot { margin-top: 6mm; border-top: 1px solid #cbd5e1; padding-top: 2.5mm;
  font-size: 8pt; color: #6b7280; }
.small { font-size: 8.5pt; }
ul { margin: 1.5mm 0 1.5mm 5mm; }
li { margin: 1mm 0; }
.pb { page-break-before: always; }
</style>"""

HEAD = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>人民币升值宏观影响量化研究报告</title>%s</head><body>
<div class="cov">
  <div><h1>人民币升值宏观影响量化研究报告</h1>
  <div class="tagline">RMB-Macro-Sim · 蒙特卡洛情景模拟 × 真实数据校准 · 6 模块传导模型</div></div>
  <div><span class="badge">研究框架 · 非投资建议</span></div>
</div>
<div class="rule"></div>
<p class="muted">%s · RMB-Macro-Sim ｜ 数据源: FRED / 腾讯行情 / akshare(北向) ｜
生成: %s ｜ 报告编号: RMBMS-2026-0906</p>
""" % (head_css(), "宏观研究 | 人民币资产重估专题", NOW)

# ---------------- charts ----------------
IMG_CHAIN = img64("charts/03_chain.png")
IMG_WALL = img64("charts_real/scenario_wall.png")
IMG_HEAT = img64("charts/02_heatmap.png")
IMG_WF = img64("charts/04_capital_waterfall.png")
IMG_INF = img64("charts/05_capital_inflows.png")
IMG_RADAR = img64("charts/06_radar.png")

# ---------------- sections ----------------
def sec_summary():
    w = P6["waterfall"]
    mult = abs(w["net"] / w["loss"])
    return """
<h2>一、摘要与核心结论</h2>
<div class="kbox">
  <div class="kcard"><div class="l">净效益 (5年累计, 基准6%%情景)</div>
    <div class="v gold">%s</div></div>
  <div class="kcard"><div class="l">资本净流入 (融资红利)</div>
    <div class="v up">%s</div></div>
  <div class="kcard"><div class="l">资本深化 (GDP增量)</div>
    <div class="v up">%s</div></div>
  <div class="kcard"><div class="l">出口部门利润损失</div>
    <div class="v dn">%s</div></div>
  <div class="kcard"><div class="l">收益/成本倍数</div>
    <div class="v">%.1f×</div></div>
</div>
<div class="callout"><b>一句话结论:</b> 在 6%% 年化升值的基准情景下,
人民币升值 5 年累计的<u>净社会经济效益约 %s(≈出口损失的 %.1f 倍)</u>——
升值的成本(出口部门利润受损)被资本流入带来的融资红利与资本深化收益大幅覆盖;
这一结论对升值速度不敏感: 即使按近 3 年现实惯性 2.7%%/年,净效益仍达 %s。</div>
<ul>
<li><b>总量层面:</b> 升值不是"广场协议式去工业化"的重演。本模型将"美元流动性稀缺→
人民币资产成为最优容器"纳入收益侧后,净效应由负转正且量级可观。</li>
<li><b>结构层面:</b> 低端制造 5 年累计利润冲击约 %s(最受伤),半导体与资源品受益
(分别为 %s、%s); 升值本质是一次"行业利润再分配 + 资产负债表重估"。</li>
<li><b>校准层面:</b> 即期 USD/CNY 已至 6.71(基准 7.20 已偏离 7%%); 近 1 年实际升值
约 6.2%%/年,与基准情景假设几乎重合 —— 情景不是空想,而是正在发生的政策事实。</li>
<li><b>资产层面:</b> A股加权年化 +8.1%%,人民币计价黄金 -5.0%%(美元金仍正收益),
工业金属 +2.0%%,国债 -0.7%%; 人民币资产重估主线: 新质生产力(半导体/算力)+ 硬资产。</li>
</ul>
""" % (fmt_t(w["net"]), fmt_t(w["inflow"]), fmt_t(w["deepening"]),
       fmt_t(w["loss"]), mult, fmt_t(w["net"]), mult, fmt_t(PIV["waterfall"]["net"]),
       "%+.1f%%" % P6["industry"]["export_lowend"],
       "%+.1f%%" % P6["industry"]["semiconductor"],
       "%+.1f%%" % P6["industry"]["commodity_metals"])

def sec_method():
    rows = [["ExchangeRate", "GBM + 升值漂移", "USD/CNY 路径 (n×T)"],
            ["Inflation", "PPI 传递 + CPI 滞后", "输入性通胀路径"],
            ["Export", "Marshall-Lerner 弹性", "出口量变化"],
            ["IndustryProfit", "汇率×敏感度+通胀+出口+利率", "11 行业利润冲击"],
            ["AssetPrice", "加权权益+久期+因子", "股/债/金/商品年化"],
            ["CapitalInflow", "存量×吸引力×美元荒时序", "三渠道流入+净效益瀑布"]]
    return """
<h2>二、模型与方法</h2>
<p>模型以一条传导链贯穿: <b>汇率路径 → 输入性通胀 → 出口竞争力 → 行业利润 →
资产价格 + 资本流入</b>, 每个环节均为可独立替换的模块, 参数集中于 config.yaml。
核心输出为 5 年窗口、2000 次蒙特卡洛模拟的中位数路径与 25-75%% 分位区间。</p>
<img class="chart" src="%s" alt="传导链">
%s
<div class="note">相比第一代模型(只算升值成本), v2.0 补上被低估的收益引擎:
全球美元流动性稀缺(2026-2027 向心坍缩窗口)下, 人民币资产凭实体+低估+政策可控
成为最优容器, 外资涌入带来 ①融资红利 ②资本深化 ③估值重估。
净效益 = 资本净流入 + 资本深化 + 出口利润损失(负项)。</div>
""" % (IMG_CHAIN, table(rows, ["模块", "算法", "输出"]))

def sec_calib():
    fx = CAL["fx_stats"]
    eq = CAL["equity"]
    ex = CAL["export"]
    ind = CAL["industry"]
    fxrows = []
    for k in ["1y", "3y", "5y", "10y"]:
        if k in fx:
            fxrows.append([k + "窗口", "%.2f%%" % (fx[k]["annual_vol"] * 100),
                           "%.2f%%" % (fx[k]["annual_drift"] * 100),
                           "%d" % fx[k]["n"]])
    indrows = [["高新出口(通信代理)", "%.2f" % ind["export_hightech"]["beta_fx_per_1pct"],
                "%+.2f" % ind["export_hightech"]["t"]],
               ["半导体", "%.2f" % ind["semiconductor"]["beta_fx_per_1pct"],
                "%+.2f" % ind["semiconductor"]["t"]],
               ["有色金属", "%.2f" % ind["commodity_metals"]["beta_fx_per_1pct"],
                "%+.2f" % ind["commodity_metals"]["t"]],
               ["银行保险", "%.2f" % ind["bank_insurance"]["beta_fx_per_1pct"],
                "%+.2f" % ind["bank_insurance"]["t"]],
               ["黄金", "%.2f" % ind["gold"]["beta_fx_per_1pct"],
                "%+.2f" % ind["gold"]["t"]]]
    return """
<h2>三、真实数据校准(2026-09)</h2>
<h3>3.1 汇率事实</h3>
%s
<p class="small">波动率定义: 日对数收益年化标准差; 漂移为负 = 人民币升值。
即期(腾讯 2026-09-06): <b>USD/CNY 6.7108</b>。</p>
<h3>3.2 资本流入(北向资金, 2015-2024.08 有效区间)</h3>
<p class="small">北向年均净流入 %s T 人民币; 持股均值 %s T 人民币; ×1.7 折算全口径
外资 → 存量约 %s T$(模型基准 0.55 同量级); 历史常态流入率 <b>%.1f%%/年</b>,
模型基准 11.1%% 属"升值+美元荒"情景值, 并在保守/激进两档间做敏感性。</p>
<h3>3.3 出口弹性(1993-2026, 402 组 12 月差分)</h3>
<p class="small">USD 计价出口总值对汇率弹性 %s(t=%s, R²=%.2f)——
统计上不显著, 支持"出口商美元定价+全球需求主导"; 模型保留出口<b>数量</b>弹性 -0.45
(总值含价格混响, 数量渠道未被证伪)。</p>
<h3>3.4 行业汇率 β(2019-2026 月频, ETF 代理, 市场调整)</h3>
%s
<p class="small">β_fx 含义: USD/CNY 每 +1%%(人民币贬值)该行业超额月收益的变化。
方向证据: 银行(显著)、有色与出口链方向与模型一致; 半导体方向相反(国产替代期遮蔽
进口成本渠道)——顾问级结果, 未自动改写模型参数。</p>
""" % (table(fxrows, ["窗口", "年化波动率", "年化漂移", "样本"]),
       "%.2f" % eq["northbound_annual_net_T_rmb_mean"],
       "%.2f" % eq["northbound_holdings_T_rmb_mean"],
       "%.2f" % eq["full_scope_holdings_T_usd_est"],
       eq["historical_rate"] * 100,
       "%.2f" % ex["beta_d12"], "%+.1f" % ex["t"], ex["r2"],
       table(indrows, ["行业(代理)", "β_fx(+1%贬值)", "t 值"]))

def sec_scenarios():
    rows = [["A · 原假设(7.20 / 6% / vol4%)", "%.3f" % P6["fx_5y"], "%.1f%%" % P6["apprec_5y_pct"],
             "%+.1f%%" % P6["industry"]["export_lowend"], fmt_t(P6["waterfall"]["net"])],
            ["B · 实测参数(6.71 / 6% / vol2.8%)", "%.3f" % P6R["fx_5y"], "%.1f%%" % P6R["apprec_5y_pct"],
             "%+.1f%%" % P6R["industry"]["export_lowend"], fmt_t(P6R["waterfall"]["net"])],
            ["C · 现实惯性(6.71 / 2.7% / vol2.8%)", "%.3f" % PIV["fx_5y"], "%.1f%%" % PIV["apprec_5y_pct"],
             "%+.1f%%" % PIV["industry"]["export_lowend"], fmt_t(PIV["waterfall"]["net"])]]
    presets_rows = [["不升值 0%%", "%.3f" % P0["fx_5y"], "%+.1f%%" % P0["industry"]["export_lowend"],
                     fmt_t(P0["waterfall"]["net"])],
                    ["慢速升值 3%%", "%.3f" % P6["fx_5y"] if False else "%.3f" % preset("p3")["fx_5y"],
                     "%+.1f%%" % preset("p3")["industry"]["export_lowend"],
                     fmt_t(preset("p3")["waterfall"]["net"])],
                    ["基准情景 6%%", "%.3f" % P6["fx_5y"], "%+.1f%%" % P6["industry"]["export_lowend"],
                     fmt_t(P6["waterfall"]["net"])],
                    ["快速升值 10%%", "%.3f" % P10["fx_5y"], "%+.1f%%" % P10["industry"]["export_lowend"],
                     fmt_t(P10["waterfall"]["net"])],
                    ["6%% + 保守资本", "%.3f" % P6C["fx_5y"], "%+.1f%%" % P6C["industry"]["export_lowend"],
                     fmt_t(P6C["waterfall"]["net"])],
                    ["6%% + 激进美元荒", "%.3f" % P6X["fx_5y"], "%+.1f%%" % P6X["industry"]["export_lowend"],
                     fmt_t(P6X["waterfall"]["net"])]]
    return """
<h2 class="pb">四、情景结果: 升值速度与资本流入双重敏感性</h2>
<img class="chart" src="%s" alt="三情景对比">
%s
<h3>4.2 升值速度敏感性(基准资本假设)</h3>
%s
<h3>4.3 资本流入情景敏感性(6%% 升值)</h3>
<p class="small">北向历史常态(保守, 6.5%%/年)下净效益 %s; 美元荒峰值(激进,
15%%/年)下净效益 %s —— 资本流入强度是净效益最大的放大器, 也提示政策的着力点:
<b>维持开放与预期管理, 让资本"想来、敢来、留得住"</b>。</p>
""" % (IMG_WALL,
       table(rows, ["情景", "USD/CNY 终值", "5年累计升值", "低端制造冲击", "净效益"]),
       table(presets_rows[:4], ["情景", "USD/CNY 终值", "低端制造 5y", "净效益"]),
       fmt_t(P6C["waterfall"]["net"]), fmt_t(P6X["waterfall"]["net"]))

def sec_industry():
    rows = ind_rows(P6, order=["export_lowend", "export_hightech", "new_energy",
                               "domestic_consumption", "infrastructure", "real_estate",
                               "bank_insurance", "semiconductor", "power_compute",
                               "gold", "commodity_metals"])
    return """
<h2 class="pb">五、行业利润重估(6%% 基准情景, 5 年累计)</h2>
%s
<p>结构性含义: <b>低端制造 -%s</b>(无议价能力, 利润池受损最重)、<b>高新出口 -%s</b>
(部分议价)、<b>半导体 +%s / 算力电力 +%s</b>(进口设备成本下降 + 资本深化受益)、
<b>工业金属 +%s / 黄金 +%s</b>(人民币购买力 + 全球硬资产定价)、
<b>地产 +%s</b>(低息长期资本置换高息短债的资产负债表修复)。
这正是"人民币资产重估"叙事的微观基础 —— 升值完成一次 <u>新旧动能之间的利润再分配</u>,
受损部门需要产业政策缓冲, 受益部门获得全球资本加持。</p>
<img class="chart" src="%s" alt="行业热力图">
""" % (table(rows, ["行业", "5年累计利润冲击"]),
       "%.1f" % abs(P6["industry"]["export_lowend"]),
       "%.1f" % abs(P6["industry"]["export_hightech"]),
       "%.1f" % P6["industry"]["semiconductor"],
       "%.1f" % P6["industry"]["power_compute"],
       "%.1f" % P6["industry"]["commodity_metals"],
       "%.1f" % P6["industry"]["gold"],
       "%.1f" % P6["industry"]["real_estate"], IMG_HEAT)

def sec_capital():
    return """
<h2 class="pb">六、资本流入: 被低估的收益引擎</h2>
<img class="chart" src="%s" alt="净效益瀑布">
<img class="chart" src="%s" alt="分渠道流入">
<h3>6.1 六条正向外溢渠道</h3>
<ol>
<li><b>融资成本下降</b> — 外资压低长端利率, 民企与科创直接受益;</li>
<li><b>技术外溢 + FDI</b> — 高端制造升级与供应链跃迁;</li>
<li><b>资本市场深化</b> — A股/债市国际化, 直接融资支持新质生产力;</li>
<li><b>财富效应</b> — 资产重估修复居民与企业资产负债表;</li>
<li><b>人民币国际化</b> — 结算与储备需求上升, 金融自主性增强;</li>
<li><b>债务结构优化</b> — 低息长期资本置换高息短债。</li>
</ol>
<div class="callout">闭环: 美国财政陷阱 → 高利率造成美元流动性稀缺 → 全球资本寻找容器
→ 人民币资产(实体+低估+可控)成为最优容器 → 估值重构 + 资本深化 → 低息长期资本
反哺实体 → 避免去工业化, 完成产业升级。</div>
""" % (IMG_WF, IMG_INF)

def sec_assets():
    rows = [["A股加权(年化)", "%+.1f%%" % P0["returns"]["equity"], "%+.1f%%" % P6["returns"]["equity"],
             "%+.1f%%" % P10["returns"]["equity"], "%+.1f%%" % P6R["returns"]["equity"]],
            ["中国国债", "%+.1f%%" % P0["returns"]["bond"], "%+.1f%%" % P6["returns"]["bond"],
             "%+.1f%%" % P10["returns"]["bond"], "%+.1f%%" % P6R["returns"]["bond"]],
            ["黄金(人民币计价)", "%+.1f%%" % P0["returns"]["gold"], "%+.1f%%" % P6["returns"]["gold"],
             "%+.1f%%" % P10["returns"]["gold"], "%+.1f%%" % P6R["returns"]["gold"]],
            ["工业金属", "%+.1f%%" % P0["returns"]["metal"], "%+.1f%%" % P6["returns"]["metal"],
             "%+.1f%%" % P10["returns"]["metal"], "%+.1f%%" % P6R["returns"]["metal"]]]
    return """
<h2>七、资产价格含义(5 年, 中位数情景)</h2>
%s
<p>A股受"新质生产力盈利增长 + 外资估值重估"双驱动, 在全部升值速度下均维持
+8%% 上下的年化; 人民币计价黄金被汇率拖累(美元金仍受益于去美元化与央行购金);
国债利率小幅上行带来资本损失(票息 1.7%% 托底)。<b>组合含义: 权益(新质生产力+资源)
优于利率资产; 人民币资产作为"非美久期"的配置价值随升值进程上升。</b></p>
<img class="chart" src="%s" alt="资产收益雷达">
""" % (table(rows, ["资产", "0%", "6%", "10%", "实测校准6%"]), IMG_RADAR)

def sec_concl():
    return """
<h2 class="pb">八、政策与投资含义</h2>
<ul>
<li><b>升值节奏</b>: "慢升比快升好"的证据有限 —— 净效益对 3-10%% 速度不敏感,
真正敏感的是<b>资本是否流入</b>。政策重心应放在: 预期管理(避免单边押注)、
开放承诺(北向/债市可进入性)、以及受损部门的产业政策缓冲(低端制造 -%s)。</li>
<li><b>行业选择</b>: 受益主线 = 半导体/算力 + 工业金属/黄金(硬资产) + 银行(利差修复);
受损主线 = 低端制造与部分高新出口 —— 后者需汇率避险工具与转产支持。</li>
<li><b>资产配置</b>: A股(新质生产力+资源) > 工业金属 > 国债; 黄金以美元计价配置
为宜(人民币计价被升值对冲)。48%% 现金仓位观点来自 GOR 框架对全球速冻窗口的防御,
与本模型的长期重估主线不矛盾 —— 顺序是"先活下来, 再重估"。</li>
</ul>
<h3>风险与局限</h3>
<ul class="small">
<li>模型参数为校准假设: 资本流入强度(保守 6.5%% ↔ 激进 15%%/年)是最大不确定项;
</li>
<li>北向资金 2024-08 披露改革后无日频数据("黑暗期"), 流入情景含外推成分;</li>
<li>行业利润冲击为弹性模型近似, 未含企业避险/转产等二阶行为;</li>
<li>出口弹性用总值检验(不显著), 数量渠道待贸易量数据重估;</li>
<li>极端情景(美元荒演变为流动性危机)下, 黄金与 A股或短期同跌 —— 模型未内生刻画
"速冻期"路径依赖; 建议与 GOR 框架速冻预案联用。</li>
</ul>
<div class="foot">
RMB-Macro-Sim · 研究框架, 不构成投资建议 ｜ 复现: python run_all.py / run_real.py /
export_dashboard.py / build_report.py ｜ 仓库: github.com/Justinjchen-Cornell/RMB-Macro-Sim
<br>数据: FRED DEXCHUS/出口, 腾讯行情(USD/CNY + ETF), akshare 北向资金; 截至 2026-09-06。
</div>
</body></html>
""" % ("%.1f" % abs(P6["industry"]["export_lowend"]))

def build_html():
    html = HEAD
    html += sec_summary()
    html += sec_method()
    html += sec_calib()
    html += sec_scenarios()
    html += sec_industry()
    html += sec_capital()
    html += sec_assets()
    html += sec_concl()
    out_html = os.path.join(REP, "人民币升值宏观影响研究报告_2026-09-06.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print("html written: %.0f KB" % (os.path.getsize(out_html) / 1024.0))
    return out_html

def to_pdf(html_path):
    pdf_path = os.path.join(REP, "人民币升值宏观影响研究报告_2026-09-06.pdf")
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    url = "file:///" + html_path.replace("\\", "/")
    cmd = [edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
           "--print-to-pdf=" + pdf_path, url]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if os.path.exists(pdf_path):
        print("pdf written: %.0f KB -> %s" % (os.path.getsize(pdf_path) / 1024.0, pdf_path))
    else:
        print("PDF FAILED:", r.stderr.decode("utf-8", "ignore")[:400])
    return pdf_path

if __name__ == "__main__":
    h = build_html()
    to_pdf(h)
