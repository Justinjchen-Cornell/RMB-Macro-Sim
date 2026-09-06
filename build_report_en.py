# -*- coding: utf-8 -*-
"""
build_report_en.py - English research report (HTML + PDF)
=========================================================
Shares data layer with build_report.py; renders English charts via viz_en.py
and converts to PDF with headless Edge. Outputs into report/.

Usage: python build_report_en.py
"""
import os, sys, subprocess, datetime
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.join(BASE, "report")
sys.path.insert(0, BASE)
os.makedirs(REP, exist_ok=True)

import build_report as zh          # data helpers + tables (no side effects at import)
from model import MacroParams, ScenarioEngine, load_project_config
from dataclasses import replace
from viz_en import plot_capital_waterfall_en, plot_capital_inflow_trends_en, \
    plot_scenario_wall_en

P6 = zh.preset("p6"); P0 = zh.preset("p0"); P10 = zh.preset("p10")
P3 = zh.preset("p3"); P6C = zh.preset("p6c"); P6X = zh.preset("p6x")
P6R = zh.preset("p6r"); PIV = zh.preset("piv")

REAL_SPOT = 6.7108
REAL_VOL = 0.0284
INERTIA = 0.027

IND_EN = {"export_lowend": "Low-end mfg", "export_hightech": "High-tech exports",
          "domestic_consumption": "Consumer", "real_estate": "Property",
          "infrastructure": "Infrastructure", "new_energy": "New energy",
          "semiconductor": "Semiconductor", "commodity_metals": "Metals",
          "power_compute": "Compute/Power", "gold": "Gold",
          "bank_insurance": "Banks/Insurance"}

NOW = datetime.datetime.now().strftime("%Y-%m-%d")


def css():
    return """
<style>
@page { size: A4; margin: 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  color: #1f2937; line-height: 1.62; margin: 0; font-size: 10.5pt;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 20pt; margin: 0 0 2mm; line-height: 1.28; }
h2 { font-size: 13.5pt; border-left: 4px solid #2563eb; padding-left: 8px;
  margin: 9mm 0 3mm; }
h3 { font-size: 11pt; margin: 5mm 0 2mm; color: #1d4ed8; }
p { margin: 2mm 0; text-align: justify; }
.muted { color: #6b7280; font-size: 9pt; }
.tagline { color: #6b7280; font-size: 10.5pt; margin-bottom: 4mm; }
.rule { border-top: 2.5px solid #1f2937; margin: 2mm 0; }
.cov { display: flex; justify-content: space-between; align-items: flex-end; }
.badge { background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe;
  border-radius: 999px; padding: 1mm 3.5mm; font-size: 8.5pt; font-weight: 600; }
.kbox { display: flex; gap: 3mm; flex-wrap: wrap; margin: 3mm 0; }
.kcard { flex: 1; min-width: 30mm; border: 1px solid #e5e9f0; border-radius: 3mm;
  padding: 3mm 4mm; background: #f8fafc; }
.kcard .v { font-size: 14pt; font-weight: 800; }
.kcard .l { font-size: 8.5pt; color: #6b7280; }
.gold { color: #d97706; } .up { color: #059669; } .dn { color: #dc2626; }
.tbl { width: 100%; border-collapse: collapse; margin: 2.5mm 0; font-size: 9pt; }
.tbl th { background: #f1f5f9; border-bottom: 1.2px solid #cbd5e1; padding: 1.6mm;
  text-align: left; }
.tbl td { border-bottom: 1px solid #e5e9f0; padding: 1.6mm; }
img.chart { width: 100%; border: 1px solid #e5e9f0; border-radius: 2mm;
  margin: 2mm 0; }
.callout { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid
  #d97706; padding: 3mm 4mm; border-radius: 2mm; margin: 3mm 0; }
.note { background: #eff6ff; border: 1px solid #bfdbfe; padding: 2.5mm 4mm;
  border-radius: 2mm; font-size: 9pt; color: #1e40af; margin: 2.5mm 0; }
.foot { margin-top: 6mm; border-top: 1px solid #cbd5e1; padding-top: 2.5mm;
  font-size: 8pt; color: #6b7280; }
.small { font-size: 8.5pt; }
ul, ol { margin: 1.5mm 0 1.5mm 5mm; }
li { margin: 1mm 0; }
.pb { page-break-before: always; }
</style>"""

HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>RMB Appreciation Macro Impact Report</title>%s</head><body>
<div class="cov">
  <div><h1>RMB Appreciation: A Quantified Macro Assessment</h1>
  <div class="tagline">RMB-Macro-Sim · Monte Carlo scenario simulation × real-data
  calibration · 6-module transmission model · Capital-inflow module</div></div>
  <span class="badge">Research framework · Not investment advice</span>
</div>
<div class="rule"></div>
<p class="muted">Macro Research | RMB Asset Revaluation Special ｜ %s ｜
Sources: FRED, Tencent Finance, akshare (northbound) ｜ Report ID: RMBMS-2026-0906-EN</p>
""" % (css(), NOW)

def ind_rows_en(p, order=None):
    items = order if order else sorted(p["industry"].keys(),
                                       key=lambda k: p["industry"][k], reverse=True)
    rows = []
    for k in items:
        if k in p["industry"]:
            rows.append([IND_EN.get(k, k), "%+.1f%%" % p["industry"][k]])
    return rows


def render_en_charts():
    mp, cc = load_project_config()
    N, SEED = 2000, 42
    pA = replace(mp, cny_annual_apprec=0.06, n_simulations=N, seed=SEED)
    pB = replace(mp, cny_spot=REAL_SPOT, cny_vol=REAL_VOL, cny_annual_apprec=0.06,
                 n_simulations=N, seed=SEED)
    pC = replace(mp, cny_spot=REAL_SPOT, cny_vol=REAL_VOL, cny_annual_apprec=INERTIA,
                 n_simulations=N, seed=SEED)
    rA = ScenarioEngine(pA, capital_cfg=cc).run()
    rB = ScenarioEngine(pB, capital_cfg=cc).run()
    rC = ScenarioEngine(pC, capital_cfg=cc).run()
    plot_scenario_wall_en({"A  Original (7.20/6%)": rA,
                           "B  Real-calibrated (6.71/6%)": rB,
                           "C  Inertia (6.71/2.7%)": rC},
                          os.path.join(BASE, "charts_real", "scenario_wall_en.png"),
                          title="RMB-Macro-Sim - Three-scenario comparison (2,000 MC runs)")
    plot_capital_waterfall_en(rB["capital_inflow"],
                              os.path.join(BASE, "charts_real", "waterfall_en.png"))
    plot_capital_inflow_trends_en(rB["capital_inflow"],
                                  os.path.join(BASE, "charts_real", "inflows_en.png"))
    return [os.path.join(BASE, "charts_real", "scenario_wall_en.png"),
            os.path.join(BASE, "charts_real", "waterfall_en.png"),
            os.path.join(BASE, "charts_real", "inflows_en.png")]

def sec_exec():
    w = P6["waterfall"]
    mult = abs(w["net"] / w["loss"])
    return """
<h2>Executive summary</h2>
<div class="kbox">
  <div class="kcard"><div class="l">Net benefit (5y, 6%% base)</div>
    <div class="v gold">%s</div></div>
  <div class="kcard"><div class="l">Capital inflow (financing)</div>
    <div class="v up">%s</div></div>
  <div class="kcard"><div class="l">Capital deepening</div>
    <div class="v up">%s</div></div>
  <div class="kcard"><div class="l">Export profit loss</div>
    <div class="v dn">%s</div></div>
  <div class="kcard"><div class="l">Benefit / cost</div>
    <div class="v">%.1fx</div></div>
</div>
<div class="callout"><b>One-line thesis:</b> under a controlled 6%% annual RMB
appreciation, the 5-year net socio-economic benefit is %s (about %.1f times the
export-sector cost). Losses in low-end manufacturing are more than offset by
financing and capital-deepening gains as global capital migrates into RMB
assets. The result is robust to pace: even at the realized 2.7%%-per-year
inertia path the net benefit stays %s.</div>
<ul>
<li><b>Aggregate:</b> not a Plaza-style deindustrialization replay. Once
dollar-scarcity inflow enters the revenue side, net effects turn positive at
meaningful scale.</li>
<li><b>Structure:</b> low-end manufacturing takes about a %s five-year profit
shock; semiconductors and hard assets benefit (%s, %s). Appreciation is a profit
reallocation plus balance-sheet revaluation.</li>
<li><b>Calibration:</b> USD/CNY is already 6.71 (a 7.20 base would be ~7%%
stale). Realized 1y drift is about -6.2%% per year - the "6%% scenario" is
current policy fact, not fiction.</li>
<li><b>Assets:</b> A-shares +8.1%% annualized; CNY gold -5.0%% (USD gold stays
positive); metals +2.0%%; CN 10Y bonds -0.7%%.</li>
</ul>
""" % (zh.fmt_t(w["net"]), zh.fmt_t(w["inflow"]), zh.fmt_t(w["deepening"]),
       zh.fmt_t(w["loss"]), mult, zh.fmt_t(w["net"]), mult,
       zh.fmt_t(PIV["waterfall"]["net"]),
       "%+.1f%%" % P6["industry"]["export_lowend"],
       "%+.1f%%" % P6["industry"]["semiconductor"],
       "%+.1f%%" % P6["industry"]["commodity_metals"])

def sec_method():
    rows = [["ExchangeRate", "GBM + appreciation drift", "USD/CNY paths"],
            ["Inflation", "PPI pass-through + CPI lag", "Import-inflation path"],
            ["Export", "Marshall-Lerner", "Export volume change"],
            ["IndustryProfit", "FX x sensitivity + CPI + exports + rates",
             "11-sector profit shocks"],
            ["AssetPrice", "Weighted equity + duration + factors",
             "A-share/bond/gold/commodity"],
            ["CapitalInflow", "Stock x attractiveness x dollar-drain",
             "3-channel inflows + net waterfall"]]
    return """
<h2>1. Model and method</h2>
<p>Transmission chain: FX path, import inflation, export competitiveness,
industry profits, then asset prices plus capital inflows. Each stage is an
independent module; all parameters live in a single config.yaml. Outputs are
5-year windows from 2,000 Monte Carlo paths (median with 25-75%% bands).</p>
%s
<div class="note">v2.0 adds the revenue engine: with global dollar liquidity
scarce (2026-2027 centripetal window), RMB assets become the preferred
container. Inflows deliver financing, capital deepening and revaluation.
Net benefit = inflow + deepening + export loss (negative).</div>
""" % zh.table(rows, ["Module", "Algorithm", "Output"])

def sec_calib():
    fx = zh.CAL["fx_stats"]; eq = zh.CAL["equity"]; ex = zh.CAL["export"]
    ind = zh.CAL["industry"]
    fxrows = []
    for k in ["1y", "3y", "5y", "10y"]:
        if k in fx:
            fxrows.append([k + " window", "%.2f%%" % (fx[k]["annual_vol"] * 100),
                           "%.2f%%" % (fx[k]["annual_drift"] * 100),
                           "%d" % fx[k]["n"]])
    indrows = [["High-tech exports", "%.2f" % ind["export_hightech"]["beta_fx_per_1pct"],
                "%+.2f" % ind["export_hightech"]["t"]],
               ["Semiconductor", "%.2f" % ind["semiconductor"]["beta_fx_per_1pct"],
                "%+.2f" % ind["semiconductor"]["t"]],
               ["Metals", "%.2f" % ind["commodity_metals"]["beta_fx_per_1pct"],
                "%+.2f" % ind["commodity_metals"]["t"]],
               ["Banks/Insurance", "%.2f" % ind["bank_insurance"]["beta_fx_per_1pct"],
                "%+.2f" % ind["bank_insurance"]["t"]],
               ["Gold", "%.2f" % ind["gold"]["beta_fx_per_1pct"],
                "%+.2f" % ind["gold"]["t"]]]
    return """
<h2>2. Real-data calibration (Sep 2026)</h2>
<h3>2.1 FX facts (FRED DEXCHUS, daily)</h3>
%s
<p class="small">Vol = annualized std of daily log returns; negative drift =
CNY appreciation. Spot (Tencent, 2026-09-06): <b>6.7108</b>.</p>
<h3>2.2 Capital inflow (northbound, valid through 2024-08)</h3>
<p class="small">Northbound annual net inflow averaged %s T RMB with holdings of
%s T RMB. Scaled by 1.7 to full foreign scope (northbound about 60%%), the
foreign A-share base is about %s T$ (model base 0.55 in the same ballpark).
Historical normal inflow rate: %.1f%% per year; the 11.1%% base is a scenario
value for appreciation plus dollar drain, stress-tested below.</p>
<h3>2.3 Export elasticity (1993-2026, 402 twelve-month diffs)</h3>
<p class="small">USD-value export elasticity to FX is %s (t=%s, R2=%.2f) -
statistically insignificant, consistent with USD invoicing and demand-driven
exports. The model keeps a volume elasticity of -0.45 (value mixes price
effects; the volume channel is not falsified).</p>
<h3>2.4 Industry FX betas (2019-2026 monthly, ETF proxies, market-adjusted)</h3>
%s
<p class="small">Beta = excess monthly return per +1%% USD/CNY (CNY
depreciation). Directional support for model priors: banks (significant),
metals, export chains; semiconductor is opposite-signed (domestic-substitution
era) - advisory only.</p>
""" % (zh.table(fxrows, ["Window", "Annual vol", "Annual drift", "Obs"]),
       "%.2f" % eq["northbound_annual_net_T_rmb_mean"],
       "%.2f" % eq["northbound_holdings_T_rmb_mean"],
       "%.2f" % eq["full_scope_holdings_T_usd_est"],
       eq["historical_rate"] * 100,
       "%.2f" % ex["beta_d12"], "%+.1f" % ex["t"], ex["r2"],
       zh.table(indrows, ["Industry (proxy)", "Beta per +1% dep", "t-stat"]))

def sec_scenarios(img_wall):
    rows = [["A  Original (7.20 / 6% / vol4%)", "%.3f" % P6["fx_5y"],
             "%.1f%%" % P6["apprec_5y_pct"],
             "%+.1f%%" % P6["industry"]["export_lowend"],
             zh.fmt_t(P6["waterfall"]["net"])],
            ["B  Real-calibrated (6.71 / 6% / vol2.8%)", "%.3f" % P6R["fx_5y"],
             "%.1f%%" % P6R["apprec_5y_pct"],
             "%+.1f%%" % P6R["industry"]["export_lowend"],
             zh.fmt_t(P6R["waterfall"]["net"])],
            ["C  Inertia (6.71 / 2.7% / vol2.8%)", "%.3f" % PIV["fx_5y"],
             "%.1f%%" % PIV["apprec_5y_pct"],
             "%+.1f%%" % PIV["industry"]["export_lowend"],
             zh.fmt_t(PIV["waterfall"]["net"])]]
    prerows = [["No appreciation (0%)", "%.3f" % P0["fx_5y"],
                "%+.1f%%" % P0["industry"]["export_lowend"],
                zh.fmt_t(P0["waterfall"]["net"])],
               ["Slow 3%", "%.3f" % P3["fx_5y"],
                "%+.1f%%" % P3["industry"]["export_lowend"],
                zh.fmt_t(P3["waterfall"]["net"])],
               ["Base 6%", "%.3f" % P6["fx_5y"],
                "%+.1f%%" % P6["industry"]["export_lowend"],
                zh.fmt_t(P6["waterfall"]["net"])],
               ["Fast 10%", "%.3f" % P10["fx_5y"],
                "%+.1f%%" % P10["industry"]["export_lowend"],
                zh.fmt_t(P10["waterfall"]["net"])]]
    caprows = [["Conservative (6.5%/yr, weak drain)",
                zh.fmt_t(P6C["waterfall"]["net"])],
               ["Base (11.1%/yr)", zh.fmt_t(P6["waterfall"]["net"])],
               ["Aggressive (15%/yr, strong drain)",
                zh.fmt_t(P6X["waterfall"]["net"])]]
    return """
<h2 class="pb">3. Scenario results - pace and capital sensitivity</h2>
<img class="chart" src="%s" alt="scenario wall">
%s
<h3>3.2 Pace sensitivity (base capital assumptions)</h3>
%s
<h3>3.3 Capital-inflow sensitivity (6%% appreciation)</h3>
%s
<p class="small">Inflow strength is the largest amplifier of net benefit -
and the policy lever: keep the market open and expectations managed so that
capital wants to come, dares to stay.</p>
""" % (img_wall, zh.table(rows, ["Scenario", "USD/CNY end", "5y apprec",
                                 "Low-end mfg", "Net benefit"]),
       zh.table(prerows, ["Scenario", "USD/CNY end", "Low-end 5y", "Net benefit"]),
       zh.table(caprows, ["Capital regime", "Net benefit (5y)"]))

def sec_industry():
    order = ["export_lowend", "export_hightech", "new_energy",
             "domestic_consumption", "infrastructure", "real_estate",
             "bank_insurance", "semiconductor", "power_compute", "gold",
             "commodity_metals"]
    rows = ind_rows_en(P6, order=order)
    return """
<h2>4. Industry profit reallocation (6%% base, 5y cumulative)</h2>
%s
<p>Structural read: low-end manufacturing %s (no pricing power); high-tech
exports %s (partial pricing power); semiconductor %s and compute/power %s gain
from cheaper imported equipment plus capital deepening; metals %s and gold %s
gain from RMB purchasing power and global hard-asset pricing; property %s
benefits from balance-sheet repair as low-cost long capital replaces short
expensive debt. Appreciation is a profit reallocation between old and new
economy - losers need industrial-policy buffers, winners get global capital
endorsement.</p>
""" % (zh.table(rows, ["Sector", "5y profit shock"]),
       "%+.1f%%" % P6["industry"]["export_lowend"],
       "%+.1f%%" % P6["industry"]["export_hightech"],
       "%+.1f%%" % P6["industry"]["semiconductor"],
       "%+.1f%%" % P6["industry"]["power_compute"],
       "%+.1f%%" % P6["industry"]["commodity_metals"],
       "%+.1f%%" % P6["industry"]["gold"],
       "%+.1f%%" % P6["industry"]["real_estate"])

def sec_capital(img_wf, img_in):
    return """
<h2 class="pb">5. Capital inflow - the under-appreciated revenue engine</h2>
<img class="chart" src="%s" alt="waterfall">
<img class="chart" src="%s" alt="inflows">
<h3>5.1 Six positive spillover channels</h3>
<ol>
<li><b>Lower funding costs</b> - foreign money flattens the long end for
private and innovation credit;</li>
<li><b>Technology spillovers via FDI</b> - upgrading the high-end supply chain;</li>
<li><b>Capital-market deepening</b> - internationalized A-shares and bonds
finance new-quality productivity;</li>
<li><b>Wealth effects</b> - revaluation repairs household and corporate
balance sheets;</li>
<li><b>RMB internationalization</b> - settlement and reserve demand, financial
autonomy;</li>
<li><b>Debt-structure optimization</b> - cheap long capital replaces expensive
short debt.</li>
</ol>
<div class="callout">The loop: US fiscal trap makes dollar liquidity scarce -
global capital searches for a container - RMB assets (real economy, cheap,
policy-controllable) become the preferred one - revaluation plus capital
deepening - cheap long capital flows back to the real economy - upgrading, not
deindustrialization.</div>
""" % (img_wf, img_in)

def sec_assets():
    rows = [["A-shares (annualized)", "%+.1f%%" % P0["returns"]["equity"],
             "%+.1f%%" % P6["returns"]["equity"],
             "%+.1f%%" % P10["returns"]["equity"],
             "%+.1f%%" % P6R["returns"]["equity"]],
            ["CN 10Y bonds", "%+.1f%%" % P0["returns"]["bond"],
             "%+.1f%%" % P6["returns"]["bond"],
             "%+.1f%%" % P10["returns"]["bond"],
             "%+.1f%%" % P6R["returns"]["bond"]],
            ["Gold (CNY terms)", "%+.1f%%" % P0["returns"]["gold"],
             "%+.1f%%" % P6["returns"]["gold"],
             "%+.1f%%" % P10["returns"]["gold"],
             "%+.1f%%" % P6R["returns"]["gold"]],
            ["Industrial metals", "%+.1f%%" % P0["returns"]["metal"],
             "%+.1f%%" % P6["returns"]["metal"],
             "%+.1f%%" % P10["returns"]["metal"],
             "%+.1f%%" % P6R["returns"]["metal"]]]
    return """
<h2>6. Asset implications (5y, median scenario)</h2>
%s
<p>A-shares compound at about +8%% across all appreciation speeds (new-quality
productivity earnings plus foreign re-rating). CNY-denominated gold is dragged
by the exchange rate (USD gold still benefits from de-dollarization and central
bank buying). Bonds suffer modest capital losses (1.7%% coupon as the floor).
<b>Portfolio read: equity (productivity + resources) beats rates; RMB assets
rise as the cleanest "non-dollar duration".</b></p>
""" % zh.table(rows, ["Asset", "0%", "6%", "10%", "Real-cal. 6%"])

def sec_concl():
    return """
<h2 class="pb">7. Policy and investment implications</h2>
<ul>
<li><b>Pace:</b> the net benefit is not very sensitive to 3-10%% appreciation -
what matters is whether capital flows in. Policy should focus on expectation
management, openness (northbound/bond access), and industrial buffers for the
most exposed sectors (low-end manufacturing %s).</li>
<li><b>Sectors:</b> winners are semiconductors/compute, metals and gold (hard
assets), banks (spread repair); losers are low-end manufacturing and part of
high-tech exports - FX hedging tools and conversion support needed.</li>
<li><b>Allocation:</b> A-shares (productivity + resources) over metals over
bonds; gold best held in USD terms during RMB appreciation. The 48%%-cash
posture from the GOR framework is a freeze-window defense, not a rejection of
this revaluation thesis - survive first, revalue second.</li>
</ul>
<h3>Risks and limitations</h3>
<ul class="small">
<li>Inflow intensity (conservative 6.5%% to aggressive 15%% per year) is the
largest uncertainty and is assumed, not measured post-2024;</li>
<li>Northbound daily data ended at the 2024-08 disclosure reform - a dark
period, extrapolated with scenario judgment;</li>
<li>Industry shocks are elasticity approximations without hedging or
conversion behavior;</li>
<li>Export elasticity tested on value (insignificant); volume channel awaits
quantity data;</li>
<li>In a dollar-liquidity crisis, gold and A-shares could fall together; the
model does not endogenize freeze-phase path dependence - combine with the GOR
framework freeze playbook.</li>
</ul>
<div class="foot">
RMB-Macro-Sim · Research framework, not investment advice ｜ Reproduce:
python run_all.py / run_real.py / export_dashboard.py / build_report_en.py ｜
Repo: github.com/Justinjchen-Cornell/RMB-Macro-Sim
<br>Data: FRED (DEXCHUS, exports), Tencent Finance (USD/CNY + ETF), akshare
(northbound), as of 2026-09-06.
</div>
</body></html>
""" % ("%+.1f%%" % P6["industry"]["export_lowend"])

def pdf_convert(html_path, pdf_path):
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge):
        edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    url = "file:///" + html_path.replace("\\", "/")
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + pdf_path, url], capture_output=True,
                   timeout=180)
    return os.path.exists(pdf_path)

def main():
    charts = render_en_charts()
    html = HEAD + sec_exec() + sec_method() + sec_calib()
    html += sec_scenarios(zh.img64(charts[0]))
    html += sec_industry()
    html += sec_capital(zh.img64(charts[1]), zh.img64(charts[2]))
    html += sec_assets() + sec_concl()
    html_path = os.path.join(REP, "RMB_Appreciation_Impact_Report_2026-09-06.html")
    pdf_path = os.path.join(REP, "RMB_Appreciation_Impact_Report_2026-09-06.pdf")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("en html: %.0f KB" % (os.path.getsize(html_path) / 1024.0))
    ok = pdf_convert(html_path, pdf_path)
    print("en pdf: %s %.0f KB" % ("OK" if ok else "FAILED",
                                  os.path.getsize(pdf_path) / 1024.0 if ok else 0))
    return pdf_path

if __name__ == "__main__":
    main()
