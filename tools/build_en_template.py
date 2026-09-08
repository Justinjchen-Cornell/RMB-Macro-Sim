# -*- coding: utf-8 -*-
"""build_en_template.py - 由中文模板生成英文模板 dashboard_template_en.html
含: 静态 UI 串翻译 + 数据驱动串(引擎判定/节奏)JS 映射 + 语言切换。
Run: python tools/build_en_template.py
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAP = [
 ("RMB-Macro-Sim · 人民币升值宏观情景模拟", "RMB-Macro-Sim · Macro-Policy Sandbox"),
 ("人民币升值宏观情景模拟 · 研究仪表盘", "Macro-Policy Sandbox · Research Dashboard"),
 ("传导链: 汇率 GBM → 输入性通胀 → 出口(Marshall-Lerner) → 11 行业利润 → 资产定价 + 资本流入(融资红利·资本深化)。",
  "Chain: FX (GBM) → import inflation → exports (Marshall-Lerner) → 11-sector profits → asset pricing + capital inflow (financing & deepening)."),
 ("Monte Carlo · 2000 次 × 8 情景", "Monte Carlo · 2000 runs x 8 scenarios"),
 ("🛫 USD/CNY 路径 (中位数 ± 25-75%)", "🛫 USD/CNY path (median ± 25-75%)"),
 ("5 年走势带; 终值标注于曲线末端", "5-year band; end value annotated"),
 ("⚖️ 资本净效益瀑布 (5 年累计, T$)", "⚖️ Net-benefit waterfall (5y, T$)"),
 ("净效益 = 融资红利 + 资本深化 − 出口损失", "Net = financing + deepening − export loss"),
 ("🏭 11 行业 5 年累计利润冲击", "🏭 11-sector 5y cumulative profit shock"),
 ("相对基准情景的利润变化 (正值=受益, 负值=受损)", "Profit change vs baseline (positive = gain, negative = loss)"),
 ("按影响升序 ↓", "Sort ascending ↓"),
 ("按影响降序 ↑", "Sort descending ↑"),
 ("🗺️ 行业 × 年份 冲击热力图", "🗺️ Sector × year shock heatmap"),
 ("Y1–Y5 累计利润冲击(%)", "Y1–Y5 cumulative profit shock (%)"),
 ("行=行业 · 列=年份(累计升值加深) · 颜色深浅=冲击强度", "Rows = sectors · columns = years · color = shock intensity"),
 ("🔮 年度展望: 最可能的人民币升贬路径", "🔮 Annual outlook: most-likely CNY path"),
 ("模型结果 × 国内外新闻事件", "model × news events"),
 ("🧭 信号 → 动作对照", "🧭 Signal → action rules"),
 ("联动 GOR / Deep-Risk-OPP", "linked to GOR / Deep-Risk-OPP"),
 ("🎯 政策算法评估 · 卢氏三原则", "🎯 Policy algorithm · Lu three principles"),
 ("🔗 Deep-Risk-OPP 联动 · GOR × easing", "🔗 Deep-Risk-OPP link · GOR × easing"),
 ("每日 00:00 UTC 刷新", "refreshed daily 00:00 UTC"),
 ("跨站读取金油比相对定价(GOR)与黄金宏观宽松偏向(easing), 与本站人民币情景交叉参考",
  "cross-site read of GOR (relative pricing) and easing (gold macro bias) for cross-reference"),
 ("最可能幅度 = 现实惯性(FRED 实测) + 新闻/事件评分(见 news_watch.yaml, 可增删);",
  "Most-likely = realized inertia (FRED) + news/event scores (news_watch.yaml, editable);"),
 ("区间为近似 25-75%; \"金额\"按每 1 万美元等值人民币变动展示",
  "band ≈ 25-75%; amount = CNY change per USD 10,000"),
 ("阈值触发制; spot 类规则按实时校准自动判定, 其余为人工观察项(建议每日对 GOR 日卡核对 10Y/VIX/中间价)",
  "Threshold-based; spot rules auto-checked, others manual (verify 10Y/VIX/fixing against the GOR daily card)"),
 ("三原则仪表: ①消化输入性通胀(油价+30%情景) ②顺差 1.2T→基本平衡 ③封堵走资、避免去工业化",
  "Three principles: ① absorb import inflation (oil +30%) ② surplus 1.2T → near balance ③ block flight / avoid deindustrialization"),
 ("读取 Deep-Risk-OPP 线上读数 (gor/goldmac)…", "Loading Deep-Risk-OPP live reads (gor/goldmac)…"),
 ("离线或网络不可用 — 联动读数跳过。线上版: justinjchen-cornell.github.io/Deep-Risk-OPP/dashboard.html",
  "Offline — link read skipped. Online: justinjchen-cornell.github.io/Deep-Risk-OPP/dashboard.html"),
 ("联动读数获取失败 — 已跳过", "Link read failed — skipped"),
 ("🎚️ 人民币年化变动(负=贬值,拖动实时联动)", "🎚️ CNY annual move (negative = depreciation)"),
 ("-5% ~ +15% · 步长0.5%(41档) · 400次MC/档 · 回测校准后各档区分度已拉大",
  "-5% ~ +15% · step 0.5% (41 grids) · 400 MC/grid · backtest-calibrated"),
 ("🧭 净效益 (5年)", "🧭 Net benefit (5y)"),
 ("收益 ≈ 损失的 ", "Benefit ≈ cost "),
 (" 倍(参数区间)", "x (parameter band)"),
 ("💰 资本净流入", "💰 Capital inflow"),
 ("A股/债市/FDI 融资红利", "A-share/bond/FDI financing"),
 ("🏗️ 资本深化", "🏗️ Capital deepening"),
 ("GDP 增量贡献", "GDP contribution"),
 ("📉 出口利润损失", "📉 Export profit loss"),
 ("低端/高新出口承压", "low-end/high-tech exports hit"),
 ("🏛️ GDP 当量 (5y累计, 利润口径)", "🏛️ GDP-equivalent (5y, profit basis)"),
 ("负向 ", "negative "),
 (" / 正向 +", " / positive +"),
 ("👷 就业风险暴露当量 (5y)", "👷 Employment exposure (5y)"),
 (" 万人", "0k jobs"),
 ("利润率8%·就业弹性0.5 假设", "8% margin · 0.5 employment elasticity"),
 ("📊 加权利润冲击指数", "📊 Weighted profit-shock index"),
 ("按增加值权重", "by value-added weight"),
 ("⚠️ 综合风险等级", "⚠️ Composite risk tier"),
 ("按负向 GDP 当量: ", "by negative GDP-equivalent: "),
 ("📈 A股加权年化", "📈 A-shares (annualized)"),
 ("🏦 中国国债年化", "🏦 CN 10Y bonds"),
 ("🥇 黄金(人民币计价)", "🥇 Gold (CNY terms)"),
 ("🧱 工业金属年化", "🧱 Industrial metals"),
 ("出口损失", "Export loss"),
 ("融资红利", "Financing"),
 ("资本深化", "Deepening"),
 ("净效益", "Net benefit"),
 ("<th>年份</th><th>最可能年末<br>USD/CNY</th><th>年变动(升值+)</th><th>事件包络区间<br>(弱~强升值)</th><th>每 1 万美元<br>人民币值变动</th><th>节奏</th>",
  "<th>Year</th><th>Likely year-end<br>USD/CNY</th><th>YoY move (apprec+)</th><th>Event envelope<br>(weak~strong)</th><th>CNY change per<br>USD 10k</th><th>Pace</th>"),
 (" 元</td><td><span class='", " CNY</td><td><span class='"),
 ("新闻/事件权重: ", "News/event weights: "),
 ("<th>规则</th><th>触发条件</th><th>动作 (与框架联动)</th><th>当前状态</th>",
  "<th>Rule</th><th>Trigger</th><th>Action (framework-linked)</th><th>Status</th>"),
 ("R1 快速升值激活", "R1 Fast-appreciation activation"),
 ("快速升值路径概率上调 → A股/人民币资产档位+50%(如 9.5%→14%), 资本流入假设切激进档",
  "Raise fast-appreciation probability → A-share/CNY asset tier +50%, capital-inflow assumption to aggressive"),
 ("已触发", "TRIGGERED"),
 ("观察中 (现价 ", "watching (spot "),
 ("R2 升值叙事证伪", "R2 Thesis falsification"),
 ("回到惯性/双向情景 → 人民币资产降回底仓, 等 R1 重新触发",
  "Back to inertia/two-way → CNY assets to base tier, wait for R1"),
 ("R3 政策意图读数", "R3 Policy-intent read"),
 ("中间价 vs 即期 偏强 > 0.3%", "fixing vs spot stronger > 0.3%"),
 ("确认主动升值管理 → 最可能档上调半档(需中间价数据, akshare 可接)",
  "Confirm managed appreciation → raise likely tier half-step (fixing data via akshare)"),
 ("人工观察", "manual watch"),
 ("R4 财政制度切换(GOR tell)", "R4 Fiscal-regime switch (GOR tell)"),
 ("10Y>4.8% 且油价同步上行", "10Y > 4.8% with oil rising"),
 ("弱美元强货币剧本权重上调 → 与 R1 叠加, 黄金美元计价多头",
  "Raise weak-USD/strong-CNY weight → stacks with R1, long USD-gold"),
 ("人工观察 (10Y 4.77 近临界)", "manual watch (10Y 4.77 near trigger)"),
 ("R5 资本流入验证", "R5 Inflow validation"),
 ("北向季度持仓新增 > 0.05T$ / VIX>35", "quarterly foreign holdings +0.05T$ / VIX>35"),
 ("持仓验证→资本假设升一档; VIX>35=速冻 → 全部风险仓位减半, 现金待命",
  "Holdings validate → capital tier up; VIX>35 = freeze → halve risk, hold cash"),
 ("人工观察 (北向 2024-08 后黑暗期)", "manual watch (northbound dark period post 2024-08)"),
 ("当日抓取", "live fetch"),
 ("离线缓存", "offline cache"),
 (" · 波动率(3y) ", " · vol(3y) "),
 (" · 惯性升值 ", " · inertia "),
 (" · FX数据截至 ", " · FX data as of "),
 ("🔁 实时校准: ", "🔁 Live calibration: "),
 ("⚠️ 离线缓存模式: 读数非实时校准(最后在线更新 ", "⚠️ OFFLINE CACHE: reads are not live-calibrated (last online "),
 (")。FRED_API_KEY 缺失或网络不可用时会降级。", "). Degrades when FRED_API_KEY is missing or network is down."),
 ("① 通胀对冲 (油价+30%)", "① Inflation offset (oil +30%)"),
 ("② 顺差 5y 末", "② Surplus, y5"),
 (" 收敛 ", " rebal "),
 (" · 第", " · year "),
 ("年达标", " reached"),
 (" · 未达", " · not reached"),
 ("③ 走资风险 (open ", "③ Flight (%GDP, open "),
 ("去工业化 (利润/GDP侵蚀)", "Deindustrialization (profit/GDP)"),
 ("判定 @ ", "Verdict @ "),
 ("%/年: ", "%/yr: "),
 ("强宽松", "STRONG EASING"),
 ("温和宽松", "MILD EASING"),
 ("温和收紧", "MILD TIGHTENING"),
 ("强收紧", "STRONG TIGHTENING"),
 ("联动数据未齐 — 参考各自读数", "Link data incomplete — read each side"),
 ("油主攻,金当盾 — 黄金底仓保留(双确认)", "Oil leads, gold shields — keep gold base (double-confirm)"),
 ("油靠自身供给故事; 黄金不加档", "Oil on its own supply story; no gold adds"),
 ("黄金重估窗口 — 金可加档", "Gold re-rating window — tier can rise"),
 ("双逆风 — 守现金", "Double headwind — hold cash"),
 ("GOR 中性区: easing 仅辅助观察", "GOR neutral: easing is auxiliary only"),
 ("读数截至 ", "as of "),
 ("GOR=金油相对定价; easing=黄金宏观宽松偏向: 2016-09 起(10y 短样本), 发布滞后+1/2月校正后季频命中仍 65-67.5%(稳健), 月相关 0.10→0.07; 序列为修订后终值 · 慢信号定仓位档, 非择时",
  "GOR = relative pricing; easing = gold macro bias (sample from 2016-09, 10y; release-lag checks keep quarterly hit 65-67.5%; revised-final data; slow signal for position tiers, not timing)"),
 ("受损 -40%", "loss -40%"),
 ("中性 0", "neutral 0"),
 ("受益 +40%", "gain +40%"),
 ("行业 \\ Y", "Sector \\ Y"),
 ("低端制造", "Low-end mfg"),
 ("高新出口", "High-tech exports"),
 ("消费", "Consumer"),
 ("地产", "Property"),
 ("基建", "Infrastructure"),
 ("新能源", "New energy"),
 ("半导体", "Semiconductor"),
 ("工业金属", "Metals"),
 ("算力/电力", "Compute/Power"),
 ("黄金", "Gold"),
 ("银行保险", "Banks/Insurance"),
 ("数据源: FRED / 腾讯行情 / akshare(北向), 截至 2026-09 ｜ 生成时间: ", "Sources: FRED / Tencent / akshare, as of 2026-09 | generated: "),
 ("复现: python run_all.py (图表) · python run_real.py (真实数据校准) · python export_dashboard.py (本页)",
  "Reproduce: python run_all.py · run_real.py · export_dashboard.py"),
 ("⚠️ 免责声明: 研究框架, 不构成投资建议。参数为校准假设, 情景为概率模拟而非预测。",
  "⚠️ Research framework, not investment advice. Parameters are calibrated assumptions; scenarios are probabilistic, not forecasts."),
]


def main():
    zh = open(os.path.join(ROOT, "dashboard_template.html"), encoding="utf-8").read()
    en = zh
    for a, b in MAP:
        en = en.replace(a, b)
    en = en.replace('<html lang="zh-CN">', '<html lang="en">')
    sw_zh = ('<div style="position:absolute;top:14px;right:18px;font-size:12px">'
             '<a href="index_en.html" style="color:#2563eb;text-decoration:none">'
             '🌐 English</a></div>')
    sw_en = ('<div style="position:absolute;top:14px;right:18px;font-size:12px">'
             '<a href="index.html" style="color:#2563eb;text-decoration:none">'
             '🌐 中文</a></div>')
    if 'index_en.html' not in zh:
        zh = zh.replace('<body>', '<body>' + sw_zh, 1)
        open(os.path.join(ROOT, "dashboard_template.html"), "w", encoding="utf-8").write(zh)
    if 'index.html' not in en.split('<script>')[0]:
        en = en.replace('<body>', '<body>' + sw_en, 1)
    vmap = ('var VERDICT_EN={"政策带内":"Within policy band",'
            '"边缘(微调工具或速度)":"Marginal (tune tools/speed)",'
            '"走资超限 - 加严封堵或降速":"Flight breach - tighten or slow",'
            '"去工业化超限(双口径) - 需政策分摊":"Deindustrialization breach - share burden",'
            '"顺差收敛不足 - 提高速度或进口政策":"Surplus not converging - speed or import policy",'
            '"其它约束未满足(外储/财政/通胀)":"Other constraint unmet (reserves/fiscal/inflation)",'
            '"升值加速":"Accelerating","升值平稳":"Steady","升值趋缓":"Fading",'
            '"双向波动/贬值风险":"Two-way / depreciation risk"};'
            'function enV(s){return VERDICT_EN[s]||s;}')
    en = en.replace("let polOpen = 0.40;", vmap + "\nlet polOpen = 0.40;", 1)
    en = en.replace("'<b style=\"color:'+vc+'\">'+v+'</b>'",
                    "'<b style=\"color:'+vc+'\">'+enV(v)+'</b>'")
    en = en.replace('r.pace+"</span>', 'enV(r.pace)+"</span>')
    open(os.path.join(ROOT, "dashboard_template_en.html"), "w", encoding="utf-8").write(en)
    print("dashboard_template_en.html written: %.0f KB" % (len(en) / 1024.0))
    print("zh switcher added:", 'index_en.html' in zh)


    POST = [
     ("开放度 0.40", "Openness 0.40"),
     ("加严封堵 0.25", "Tightened 0.25"),
     (" <span class='tagchip'>滑块模式 · ", " <span class='tagchip'>slider mode · "),
     ('" ｜ 累计升值 "', '" | cumulative "'),
     ('"% ｜ USD/CNY 5 年终值 <b>"', '"% | USD/CNY y5 end <b>"'),
     ("⚠️ offline cache模式: 读数非实时校准(最后在线更新 ", "⚠️ OFFLINE CACHE: reads not live-calibrated (last online "),
     (")。FRED_API_KEY 缺失或网络不可用时会降级。", "). Degrades when FRED_API_KEY missing or offline."),
    ]
    for a, b in POST:
        en = en.replace(a, b)
    # post: EN preset labels/notes for chips & meta
    plabel = ('var PLABEL={p0:"No appreciation 0%",p3:"Slow 3%",p6:"Base 6%",'
              'p10:"Fast 10%",p6c:"6% + conservative capital",'
              'p6x:"6% + aggressive drain",p6r:"Real-calibrated 6%",'
              'piv:"Realized inertia 2.7%"};'
              'var PNOTE={p0:"base params, zero-drift control",'
              'p3:"base params, mild appreciation",'
              'p6:"base params (config.yaml), policy-driven",'
              'p10:"aggressive, accelerated transition",'
              'p6c:"inflow at historical norm (6.5%/yr)",'
              'p6x:"peak dollar-scarcity (15%/yr)",'
              'p6r:"calibrated: spot 6.71 + 3y vol 2.84%",'
              'piv:"realized 3y drift 2.7%/yr"};'
              'function enLabel(p){return PLABEL[p.key]||(p.rate_pct!=null?"Custom "+p.rate_pct+"%":p.label);}'
              'function enNote(p){return PNOTE[p.key]||(p.rate_pct!=null?"base params + speed "+p.rate_pct+"% (400 MC)":p.note);}')
    en = en.replace("let polOpen = 0.40;", plabel + chr(10) + "let polOpen = 0.40;", 1)
    en = en.replace("b.textContent=p.label;", "b.textContent=enLabel(p);")
    en = en.replace('"<b>"+esc(p.label)+"</b> · "+esc(p.note)+',
                    '"<b>"+esc(enLabel(p))+"</b> · "+esc(enNote(p))+')
    open(os.path.join(ROOT, "dashboard_template_en.html"), "w", encoding="utf-8").write(en)
    print("EN labels/notes wired")

    en = en.replace("+v+'</b>", "+enV(v)+'</b>")
    en = en.replace(sw_zh, "", 1)
    open(os.path.join(ROOT, "dashboard_template_en.html"), "w", encoding="utf-8").write(en)
    print("verdict EN + switcher deduped")

    POST2 = [
     ("中位数路径", "Median path"),
     ("25-75% 分位", "25-75% band"),
     ("三包络: 下沿=仅贬值类事件(最弱升值) / 最可能=全部事件 / 上沿=仅升值类事件(最强升值)。",
      "Three envelopes: low = depreciation-side events only (weakest), base = all events, high = appreciation-side only (strongest)."),
     ("事件表 news_watch.yaml 可增删(影响合计 +3.2pp / -1.0pp); \"金额\"按每 1 万美元等值人民币变动。",
      "Edit news_watch.yaml to add/remove events (impact +3.2pp / -1.0pp); amount = CNY per USD 10k."),
    ]
    for a, b in POST2:
        en = en.replace(a, b)
    tier = ('var TIER_EN={"高":"High","中":"Mid","低":"Low"};'
            'function enTier(v){return TIER_EN[v]||v;}')
    en = en.replace("var PLABEL=", tier + chr(10) + "var PLABEL=", 1)
    en = en.replace("(c.l.indexOf(\"风险\")>=0?tierCls(c.v):\"\")+\">\"+c.v+",
                    "(c.l.indexOf(\"风险\")>=0?tierCls(c.v):\"\")+\">\"+(c.l.indexOf(\"风险\")>=0?enTier(c.v):c.v)+")

    # POST3: tier selector fix + event name map + residual label cleanup
    evfn = ('var EVMAP=[["美元流动性稀缺窗口","USD liquidity scarcity window"],'
            '["向心坍缩","centripetal collapse"],'
            '["弱美元强货币财政剧本","Weak-USD/strong-CNY playbook"],'
            '["防火墙","firewall"],'
            '["人民币资产重估叙事","RMB re-rating narrative"],'
            '["外资预强策略","pre-positioning"],'
            '["美债长端高位","UST long-end elevated"],'
            '["美联储宽松","Fed easing"],["购债压力","buyback pressure"],'
            '["速冻期短期美元回流风险","Freeze-phase USD repatriation"],'
            '["北向资金历史常态支撑","Northbound historical-norm support"],'
            '["日美协调干预","JP-US coordination"],'
            '["联储鹰派反扑","hawkish pushback"],'
            '["北向资金历史常态支撑","Northbound historical-norm support"],'
            '["VIX 跳升/全球去杠杆","VIX spike / global deleveraging"],'
            '["年均流入","annual avg inflow"],["后黑暗期","dark period after"]];'
            'function enEvent(s){EVMAP.forEach(function(p){s=s.split(p[0]).join(p[1]);});return s;}')
    en = en.replace("var TIER_EN=", evfn + chr(10) + "var TIER_EN=", 1)
    en = en.replace('(c.l.indexOf("风险")>=0?tierCls(c.v):"")+' + chr(39) + '">' + chr(39) + '+c.v+',
                    '(c.l.indexOf("tier")>=0?tierCls(c.v):"")+' + chr(39) + '">' + chr(39) + '+(c.l.indexOf("tier")>=0?enTier(c.v):c.v)+')
    en = en.replace('esc(e.name)+', 'esc(enEvent(e.name))+')
    for a, b in [("按negative GDP 当量: ", "by negative GDP-equivalent: "),
                 ("按负向 GDP 当量: ", "by negative GDP-equivalent: ")]:
        en = en.replace(a, b)


    # POST4: prefer payload _en fields; residual literal fixes
    en = en.replace('function enLabel(p){return PLABEL[p.key]||(p.rate_pct!=null?"Custom "+p.rate_pct+"%":p.label);}',
                    'function enLabel(p){return p.label_en||PLABEL[p.key]||(p.rate_pct!=null?"Custom "+p.rate_pct+"%":p.label);}')
    en = en.replace('function enNote(p){return PNOTE[p.key]||(p.rate_pct!=null?"base params + speed "+p.rate_pct+"% (400 MC)":p.note);}',
                    'function enNote(p){return p.note_en||PNOTE[p.key]||(p.rate_pct!=null?"base params + speed "+p.rate_pct+"% (400 MC)":p.note);}')
    en = en.replace('note.textContent=P.insight||"";', 'note.textContent=(P.insight_en||P.insight||"");')
    en = en.replace("🧭 联动动作: ", "🧭 Linked action: ")
    en = en.replace("manual watch (北向 2024-08 后黑暗期)", "manual watch (northbound dark period post 2024-08)")
    en = en.replace("北向 2024-08 后黑暗期", "northbound dark period post 2024-08")
    en = en.replace('"收敛 ", "rebal "') if False else en
    en = en.replace("收敛 ", "rebal ")
    for a, b in [("收盘", "close"), ("近临界", "near trigger")]:
        en = en.replace(a, b)
    # footer exact strings (with emoji prefix)
    en = en.replace("📊 数据源: FRED / 腾讯行情 / akshare(北向), 截至 2026-09 ｜ 生成时间: ",
                    "📊 Sources: FRED / Tencent / akshare, as of 2026-09 | generated: ")
    en = en.replace("⚠️ 免责声明: 研究框架, 不构成投资建议。参数为校准假设, 情景为概率模拟而非预测。",
                    "⚠️ Research framework, not investment advice. Parameters are calibrated assumptions; scenarios are probabilistic, not forecasts.")

    open(os.path.join(ROOT, "dashboard_template_en.html"), "w", encoding="utf-8").write(en)
    print("POST4 saved")





if __name__ == "__main__":
    main()
