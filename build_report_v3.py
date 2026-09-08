# -*- coding: utf-8 -*-
"""
build_report_v3.py - 详细研究报告 PDF (v3.0 完成态)
====================================================
输出: report/宏观政策沙盒_详细研究报告_v3_2026-09.pdf (+html)
Run:  python build_report_v3.py
"""
import os, sys, json, base64, subprocess, datetime as dt
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.join(BASE, "report")
os.makedirs(REP, exist_ok=True)
sys.path.insert(0, BASE)

DASH = json.load(open(os.path.join(BASE, "dashboard_data.json"), encoding="utf-8"))
SENS = json.load(open(os.path.join(BASE, "tools", "sensitivity_9x.json"), encoding="utf-8"))
PPI = json.load(open(os.path.join(BASE, "params", "ppi_pass_through.json"), encoding="utf-8"))
OIL = json.load(open(os.path.join(BASE, "oil_year_scenario.json"), encoding="utf-8"))
OUTF = pd.read_csv(os.path.join(BASE, "params", "implied_outflow.csv"),
                   encoding="utf-8-sig")
OUTF.index = pd.PeriodIndex(OUTF.iloc[:, 0], freq="M")
CRISIS = float(OUTF["resid_t"].resample("Y").sum().loc["2015":"2016"].mean())

NOW = dt.datetime.now().strftime("%Y年%m月%d日")


def img(rel):
    with open(os.path.join(BASE, rel), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def preset(key):
    for p in DASH["presets"]:
        if p["key"] == key:
            return p
    return DASH["presets"][2]


P6, P6C, P6X, PIV = preset("p6"), preset("p6c"), preset("p6x"), preset("piv")

CSS = """
<style>
@page { size: A4; margin: 15mm 13mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei","PingFang SC",sans-serif; color:#1f2937;
  font-size:10.2pt; line-height:1.62; margin:0; -webkit-print-color-adjust:exact;
  print-color-adjust:exact; }
h1 { font-size:20pt; margin:0 0 2mm; }
h2 { font-size:13.5pt; border-left:4px solid #2563eb; padding-left:8px;
  margin:8mm 0 3mm; }
h3 { font-size:11pt; color:#1d4ed8; margin:4.5mm 0 2mm; }
p { margin:2mm 0; text-align:justify; }
.muted { color:#6b7280; font-size:9pt; }
.rule { border-top:2.5px solid #1f2937; margin:2mm 0; }
.badge { display:inline-block; background:#eef2ff; color:#4338ca;
  border:1px solid #c7d2fe; border-radius:999px; padding:1mm 3.5mm; font-size:8.5pt; }
.kbox { display:flex; gap:3mm; flex-wrap:wrap; margin:3mm 0; }
.kcard { flex:1; min-width:28mm; border:1px solid #e5e9f0; border-radius:3mm;
  padding:3mm 3.5mm; background:#f8fafc; }
.kcard .v { font-size:13.5pt; font-weight:800; }
.kcard .l { font-size:8.5pt; color:#6b7280; }
.gold{color:#d97706} .up{color:#059669} .dn{color:#dc2626}
table.tbl { width:100%; border-collapse:collapse; margin:2.5mm 0; font-size:9pt; }
.tbl th { background:#f1f5f9; border-bottom:1.2px solid #cbd5e1; padding:1.5mm;
  text-align:left; }
.tbl td { border-bottom:1px solid #e5e9f0; padding:1.5mm; }
img.chart { width:100%; border:1px solid #e5e9f0; border-radius:2mm; margin:2mm 0; }
.callout { background:#fffbeb; border:1px solid #fde68a; border-left:4px solid
  #d97706; padding:3mm 4mm; border-radius:2mm; margin:3mm 0; }
.note { background:#eff6ff; border:1px solid #bfdbfe; padding:2.5mm 4mm;
  border-radius:2mm; font-size:9pt; color:#1e40af; margin:2.5mm 0; }
.foot { margin-top:6mm; border-top:1px solid #cbd5e1; padding-top:2.5mm;
  font-size:8pt; color:#6b7280; }
ul, ol { margin:1.5mm 0 1.5mm 5mm; } li { margin:0.8mm 0; }
.pb { page-break-before:always; }
.small { font-size:8.6pt; }
</style>"""


def tbl(rows, head=None):
    out = ['<table class="tbl">']
    if head:
        out.append("<tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</table>")
    return "".join(out)


def sec_cover():
    w = P6["waterfall"]
    return """
<div class="rule"></div>
<p class="muted">宏观研究 · 大国博弈下的财政·货币·产业一体化政策模拟器 · %s ·
报告编号 RMBMS-V3-20260907 · <span class="badge">研究框架 · 非投资建议</span></p>
<h2>摘要</h2>
<div class="kbox">
 <div class="kcard"><div class="l">净效益(6%% 基准, 5y)</div><div class="v gold">+%.2f T$</div></div>
 <div class="kcard"><div class="l">收益/成本区间(参数)</div><div class="v">%.1f-%.1f 倍</div></div>
 <div class="kcard"><div class="l">政策带(三原则)</div><div class="v">5-7%%/年</div></div>
 <div class="kcard"><div class="l">外储末(6%%, 含估值)</div><div class="v up">%.2f T$</div></div>
 <div class="kcard"><div class="l">资本外流(6%%)</div><div class="v">1.5%% GDP</div></div>
</div>
<p>本报告呈现一套可运行的<strong>宏观政策沙盒</strong>:以卢麒元「国家资管、弱汇强币、产业升级、大国博弈」思想为内核,
回答四个问题——<strong>节奏怎么控、工具怎么选、极端情况扛不扛得住、各地区各行业谁疼谁赚</strong>。
系统由市场情景层(6 模块蒙特卡洛)、政策算法层(三原则统一引擎)、交叉验证层(GOR×easing 与油价推演)构成,
全部基于免费数据(FRED/腾讯行情/akshare)与可复现脚本,所有关键数字给出区间与出处。</p>
<div class="callout"><b>核心结论:</b>①在 6%% 年化升值基准下,5 年净效益中位约 <b>+2.7 T$</b>,
参数不确定性区间对应 <b>收益/成本 7.0–13.0 倍</b>;②同时满足"消化输入通胀/顺差收敛/防走资防去工业化"的
升值速度为 <b>5–7%%/年</b>(6%% 时仅需进口政策力度 k=0.05 补足,政策承担 16%%);③走资曲线已锚定官方月度残差
(2015-16 危机档 5.25%% GDP),10%%/年对应 5.3%% GDP——<b>升得越快,外储与产业冲击越早触线</b>。</div>
""" % (NOW, w["net"], SENS["ratio_9x_pct"][0], SENS["ratio_9x_pct"][4], 4.91)


def sec_system():
    return """
<h2 class="pb">一、体系与定位</h2>
<img class="chart" src="%s" alt="system map">
<h3>三层职责(不要混用)</h3>
%s
<h3>数据与参数治理</h3>
<p>数据源:FRED(USD/CNY、CPI、失业、SLOOS、房价、财政、油价、美债)｜腾讯行情(现价/K 线)｜
akshare(北向历史、COMEX 金、外储、贸易、FDI、PPI)｜news_watch 事件表(可维护)。
参数唯一真源为 <code>config.yaml</code>(市场层)与 <code>policy_params.yaml</code>(政策层);
<code>params/</code> 下的 CSV/JSON 均为<b>生成物或官方数据快照</b>,不回写模型。</p>
<div class="note">设计原则:①核心价值是<b>清晰呈现权衡逻辑</b>,非数字绝对精确——所有输出默认区间化;
②颗粒度与校准成本成正比,能校准才加(H5 未建模清单);③机制优先于外推,黑暗期(2024-08 后北向)
与代理数据一律标注。</div>
""" % (img("assets/system_map.png"),
       tbl([["市场层", "回答“会怎样”:汇率→通胀→出口→行业→资产+资本流入", "41 档滑块/情景/瀑布"],
            ["政策层", "回答“该怎样”:三原则约束下的可行速度与工具组合", "政策带/最小政策 k/红线"],
            ["交叉层", "回答“现在到哪了”:GOR×easing、油价推演", "信号→动作/三板互证"]],
           ["层", "职责", "代表输出"]))


def sec_market():
    ind = P6["industry"]
    rows = [["低端制造", "%.1f%%" % ind["export_lowend"], "无议价能力, 利润池受损最重"],
            ["高新出口", "%.1f%%" % ind["export_hightech"], "部分议价能力"],
            ["半导体", "+%.1f%%" % ind["semiconductor"], "进口设备成本下降 + 资本深化"],
            ["算力/电力", "+%.1f%%" % ind["power_compute"], "同半导体"],
            ["工业金属", "+%.1f%%" % ind["commodity_metals"], "人民币购买力 + 全球定价"],
            ["黄金", "+%.1f%%" % ind["gold"], "硬资产受益"],
            ["地产", "+%.1f%%" % ind["real_estate"], "低息长期资本置换高息短债"]]
    return """
<h2 class="pb">二、市场情景层:升值会怎样影响经济与资产</h2>
<p>传导链:汇率路径(GBM, 真实校准 6.71/2.8%%) → 输入性通胀(PPI→CPI) → 出口竞争力(Marshall-Lerner)
→ 11 行业利润冲击 → 资产定价 + 资本流入(融资红利+资本深化)。41 档升贬滑块(-5%%~+15%%)驱动全部输出。</p>
<img class="chart" src="%s" alt="scenario wall">
<h3>行业利润重估(6%% 基准, 5 年累计)</h3>
%s
<h3>资本流入:被低估的收益引擎</h3>
<p>成本-收益瀑布:出口损失 -0.32 T$,资本净流入 +2.18 T$,资本深化 +0.81 T$,<b>净效益 +2.67 T$</b>。
参数敏感性(800 组拉丁采样)给出净效益 5-95%% 区间与收益/成本倍数 <b>7.0–13.0 倍</b>(中位 9.7),
建议对外一律引用区间。</p>
<img class="chart" src="%s" alt="waterfall">
<img class="chart" src="%s" alt="outflow anchor">
""" % (img("charts_real/scenario_wall.png"),
       tbl(rows, ["行业", "5 年冲击", "逻辑"]),
       img("charts/04_capital_waterfall.png"),
       img("assets/report_outflow.png"))


def sec_policy():
    ppi = PPI["runs"]
    krows = [["5%", "0.10", "0.28", "30%", "70%", "23.3 / 2.3", "政策带内"],
             ["6%", "0.05", "0.30", "16%", "84%", "28.8 / 2.9", "政策带内"],
             ["7%", "0.01", "0.29", "2%", "98%", "34.5 / 3.4", "政策带内"],
             ["8%", "0.00", "0.18", "0%", "-", "40.5 / 4.9", "去工业化超限"]]
    prows = [["油价 +10% → PPI", "+%.2f pp" % ppi["ppi"]["oil_10pct_pp"],
              "t=%.1f, R²=%.2f" % (ppi["ppi"]["t_oil"], ppi["ppi"]["r2"]),
              "显著: 输入通胀主走油价"],
             ["USDCNY +10% → PPI", "%.2f pp" % ppi["ppi"]["fx_10pct_pp"],
              "t=%.1f(不显著)" % ppi["ppi"]["t_fx"], "汇率直接传导≈0; ept 作成本核算用"],
             ["油价 +10% → CPI", "+%.2f pp" % ppi["cpi"]["oil_10pct_pp"],
              "R²=%.2f(低)" % ppi["cpi"]["r2"], "不作参数依据"]]
    return """
<h2 class="pb">三、政策算法层:怎样升才符合三原则</h2>
<p>三原则 → 可计算约束:①消化输入性通胀(与油价逆向同步)②贸易项下基本平衡(1.2 万亿顺差收敛至 ≤0.3 T$)
③严厉封堵走资、避免广场协议式去工业化(双口径红线 35%%)。引擎以<b>固定速度带求最小政策度 k</b>:
升值为主动力,进口政策只补足差额。</p>
<h3>政策带 5-7%%(6%% 只需 k=0.05)</h3>
%s
<p class="small">8%%+ 触发去工业化红线(低端制造利润冲击 40.5%% &gt; 35%%)——政策带上限由产业约束而非汇率本身决定。</p>
<h3>走资曲线:从拍脑袋到官方残差锚(M4)</h3>
<p>官方月度残差 = −Δ外储 + 货物顺差 + FDI + 估值效应,重建 2015-2026 资本外流序列:
2015 年 %.2f T$、2016 年 %.2f T$(危机档年均 <b>%.2f T$ ≈ 5.25%% GDP</b>,与学界 0.8-1.2 T$ 共识一致)。
走资曲线据此重标定:6%%/8%%/10%% → 1.5%%/3.0%%/5.3%% GDP,红线 8%% GDP。</p>
<img class="chart" src="%s" alt="flight curve">
<h3>外储:交易性 vs 估值性(H1)</h3>
<p>外储路径已含估值损益(美债久期×利率 + 黄金重估 + 美元折算,常规/冲击两档情景)。
6%% 情景下外储 5 年末约 4.91 T$,高于 2.5 T$ 底线;7%%+ 因走资加速快速下探。</p>
<h3>通胀通道实测(H4)</h3>
%s
""" % (tbl(krows, ["速度", "最小政策 k", "顺差(5y)", "政策承担", "速度承担",
                  "去工业化(利润%/GDP%)", "判定"]),
       float(OUTF["resid_t"].resample("Y").sum().loc["2015"]),
       float(OUTF["resid_t"].resample("Y").sum().loc["2016"]),
       CRISIS, img("assets/report_flight.png"),
       tbl(prows, ["通道", "估计", "统计量", "解读"]))


def sec_cross():
    oil_rows = []
    for name in ["A 温和去风险", "B 供给冲击", "C 速冻-修复"]:
        d = OIL[name]
        r26 = [r for r in d["rows"] if r["year"] == 2026][0]
        oil_rows.append([name, str(r26["brent"]),
                         "%.1f" % r26["score"], "%.1f-%.1f" % (r26["score_lo"], r26["score_hi"]),
                         "%.1f" % d["avg_score"]])
    return """
<h2 class="pb">四、交叉验证层:现在到哪了</h2>
<h3>GOR × easing(联动 Deep-Risk-OPP)</h3>
<p>金油比(GOR)回答“油与金谁便宜”(相对定价,周频);easing 验证器回答“宏观是否站在黄金一边”
(绝对环境,季频)。当前读数:GOR 49.1(极端区) + easing +0.30(温和宽松但 6 个月回落) →
<b>油主攻、金当盾(底仓保留不加档)</b>。easing 季频命中 65-67.5%%(2016 起 10 年样本,
发布滞后校正后稳健;样本短于论文 30 年,已标注)。</p>
<h3>油价 5 年分年推演(中国视角)</h3>
%s
<div class="callout"><b>反直觉结论:</b>速冻情景(低油价+美元荒)对中国反而有利度最高——
能源账单省约 0.1 T$/年、顺差红包扩大;最差是供给冲击年(高油价+美元荒,2026 有利度仅 61.9)。
应对:冲击年降速维稳、把"低油价红包"转为战略储备与人民币资产低位预配。</div>
<h3>三看板互证</h3>
%s
""" % (tbl(oil_rows, ["路径", "2026 Brent", "2026 有利度", "±10pp 带", "5 年均分"]),
       tbl([["GOR 看板", "49.1 极端区; 油 4 周 +18%", "油是交易主线"],
            ["黄金验证器", "+0.30 温和但回落; 仅房价支撑", "金拿着, 不加"],
            ["人民币看板", "即期 6.71; 2026 展望 6.39; 6.30 提前激活", "重估等 2027"]],
           ["看板", "读数", "指向"]))


def sec_numbers():
    return """
<h2 class="pb">五、关键数字与区间(出处表)</h2>
%s
<p class="small">读数字三原则:①看区间不看单点;②看口径(利润%% vs GDP%%)不混用;
③看假设出处(全部列于本表)。</p>
""" % tbl([
 ["净效益 +2.67 T$", "capital_inflow 模块", "流入率/美元荒/边际产出", "点估计; 区间见下一行"],
 ["收益/成本 7.0–13.0 倍", "tools/sensitivity_9x.py", "800 组参数采样(锚回 6% 点)", "中(对外引用区间)"],
 ["低端制造 -28.8%(6%)", "行业模块", "每 10% 升值利润弹性 -8%", "中(弹性假设)"],
 ["政策带 5-7%/年", "policy_engine", "以升值为主动力前提", "中(前提敏感)"],
 ["走资 1.5% GDP(6%)", "M4 残差锚", "2015-16 危机档 5.25% GDP", "中(FDI 2023-07 后缺失)"],
 ["外储 4.91 T$(6%)", "H1 估值模块", "资产配置/久期/金价假设", "中(组合数据待校准)"],
 ["油价→PPI +0.73pp/10%", "H4 OLS(n=303)", "12m 差分 + 滞后分布", "中高(t=5.8, R²=0.77)"],
 ["easing 季频 65-67.5%", "goldmac 回测", "10 年短样本 + 发布滞后校正", "中(短于论文 30 年)"],
 ["2026 展望 6.39(-4.8%)", "outlook", "惯性 2.7% + 新闻事件评分", "低-中(看三包络区间)"],
], ["数字", "出处", "关键假设", "可信度"])


def sec_limits():
    return """
<h2 class="pb">六、极端情景、投资含义与局限</h2>
<h3>压力测试速览</h3>
%s
<h3>投资与政策含义(框架输出, 非建议)</h3>
<ul>
<li><b>顺序比方向重要</b>:速冻(现金 48%%) → 错杀(三档买入) → 重估(2027 主线);现金是弹药不是踏空。</li>
<li><b>行业</b>:受益=半导体/算力+金属/黄金+银行;受损=低端制造与部分高新出口(需避险工具+产业缓冲)。</li>
<li><b>政策</b>:速度带 5-7%%;平衡责任由进口端政策分摊(k 随速度递减);想升得快,先关紧后门
(开放度 0.40→0.25 使 10%% 档走资强度从 5.3%% 降至 3.3%% GDP)。</li>
</ul>
<h3>局限与未建模(H5 摘录)</h3>
<ul class="small">
<li>参数为校准假设;FDI 官方序列 2023-07 后缺失,残差锚尾部含零填充;</li>
<li>北向日频 2024-08-18 后全球停发(制度事实),仅官方总量季度可得;</li>
<li>未建模:结售汇/离岸微观、地区颗粒度、完整博弈、预期与期权微观、影子渠道、财政/产业内生、高频信号;</li>
<li>含规范性价值判断(卢氏三原则),输出为"该前提下的可行区间",非客观预测。</li>
</ul>
<div class="foot">
RMB-Macro-Sim v3.0 · 宏观政策沙盒 · 复现:python scenario_runner.py --mode all ｜
政策引擎:python policy_engine.py ｜ 报告再生:python build_report_v3.py ｜
仓库:github.com/Justinjchen-Cornell/RMB-Macro-Sim<br>
数据:FRED / 腾讯行情 / akshare / news_watch,截至 2026-09。研究框架,不构成投资建议。
</div>
</body></html>
""" % tbl([["供给冲击年(2026)", "油价 120 / 输入通胀 3.3pp", "降速维稳、不接双杀逻辑资产"],
           ["速冻年(2026Q4-27)", "油价 70 / 账单 -0.1T$", "战略储备 + 错杀三档买入"],
           ["快升值(10%+)", "走资 5.3% GDP / 去工业 53%", "触发红线: 需封堵+产业政策, 引擎判定超限"],
           ["美国报复(博弈)", "速度>7% 或国际化加深", "关税冲击 + 制裁概率(单参数近似)"]],
          ["情景", "关键量", "应对/判定"])


def build_html():
    html = ("<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<title>宏观政策沙盒·详细研究报告 v3.0</title>" + CSS + "</head><body>")
    html += ("<h1>大国博弈下的财政·货币·产业一体化政策模拟器</h1>"
             "<p class='muted'>RMB-Macro-Sim v3.0 · 宏观政策沙盒 · 详细研究报告</p>")
    html += sec_cover() + sec_system() + sec_market() + sec_policy()
    html += sec_cross() + sec_numbers() + sec_limits()
    out = os.path.join(REP, "宏观政策沙盒_详细研究报告_v3_2026-09.html")
    open(out, "w", encoding="utf-8").write(html)
    print("html: %.0f KB" % (os.path.getsize(out) / 1024))
    return out


def to_pdf(html_path):
    pdf = os.path.join(REP, "宏观政策沙盒_详细研究报告_v3_2026-09.pdf")
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    url = "file:///" + html_path.replace("\\", "/")
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + pdf, url], capture_output=True, timeout=240)
    print("pdf:", os.path.getsize(pdf) / 1024 if os.path.exists(pdf) else "FAILED",
          "KB")
    return pdf


if __name__ == "__main__":
    h = build_html()
    to_pdf(h)
