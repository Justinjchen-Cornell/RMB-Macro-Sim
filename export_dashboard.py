# -*- coding: utf-8 -*-
"""
export_dashboard.py - Preset scenarios -> dashboard.html (single file)
=====================================================================
Runs preset scenarios (2000 MC each, fixed seed), plus a custom
appreciation-rate grid (0-10%, step 0.5%, 600 MC) powering the dashboard
slider, and computes per-scenario macro risk (GDP-equivalent impact,
employment exposure). Injects everything into dashboard_template.html.

Usage:  python export_dashboard.py            (offline / cached data)
        python export_dashboard.py --live     (fetch FRED/Tencent first)
Outputs: dashboard.html / index.html / dashboard_data.json
"""
import os
import json
import sys
import datetime as dt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from model import MacroParams, ScenarioEngine, load_project_config
from capital_inflow import CapitalConfig
from dataclasses import replace

N, SEED = 2000, 42
GRID_N, GRID_SEED = 400, 7
REAL_SPOT = 6.7108
REAL_VOL = 0.0284          # 3y realized vol
INERTIA_APPREC = 0.027     # 3y realized drift (appreciation)

# ── 行业宏观元数据 (用于 GDP / 就业当量, 现实量级近似) ──────────
#   va_share: 增加值占 GDP 比重 | emp_share: 占城镇就业比重
#   来源近似: 国家统计局口径 + 行业结构估算 (2025 前后); 文档中标注为近似
IND_META = {
    "export_lowend":       {"va": 0.060, "emp": 0.090, "name_cn": "低端制造"},
    "export_hightech":     {"va": 0.080, "emp": 0.060, "name_cn": "高新出口"},
    "domestic_consumption": {"va": 0.120, "emp": 0.140, "name_cn": "消费"},
    "real_estate":         {"va": 0.065, "emp": 0.070, "name_cn": "地产"},
    "infrastructure":      {"va": 0.050, "emp": 0.060, "name_cn": "基建"},
    "new_energy":          {"va": 0.025, "emp": 0.020, "name_cn": "新能源"},
    "semiconductor":       {"va": 0.012, "emp": 0.008, "name_cn": "半导体"},
    "commodity_metals":    {"va": 0.022, "emp": 0.015, "name_cn": "工业金属"},
    "power_compute":       {"va": 0.035, "emp": 0.020, "name_cn": "算力/电力"},
    "gold":                {"va": 0.002, "emp": 0.001, "name_cn": "黄金"},
    "bank_insurance":      {"va": 0.060, "emp": 0.025, "name_cn": "银行保险"},
}
MARGIN = 0.08              # 利润占增加值假设 (统一近似)
EMP_ELAST = 0.50           # 利润冲击对就业的传导弹性 (5年, 保守)
URBAN_EMP_WAN = 46000.0    # 城镇就业总量 (万人)


def macro_risk(industry_pct: dict) -> dict:
    """行业 5y 累计利润冲击(百分点) → 宏观风险当量 (近似, 非预测)。"""
    w_profit = 0.0     # 加权利润冲击指数 (%)
    gdp_cum = 0.0      # GDP 当量 (百分点, 5年累计, 利润口径)
    emp_wan = 0.0      # 就业风险暴露当量 (万人, 5年)
    detail = {}
    for k, v in industry_pct.items():
        m = IND_META.get(k)
        if not m:
            continue
        w_profit += m["va"] * v
        gdp_cum += m["va"] * v * MARGIN
        emp_wan += m["emp"] * v * EMP_ELAST / 100.0 * URBAN_EMP_WAN
        detail[k] = {"va": m["va"], "emp": m["emp"],
                     "gdp_pt": m["va"] * v * MARGIN,
                     "emp_wan": m["emp"] * v * EMP_ELAST / 100.0 * URBAN_EMP_WAN}
    neg_gdp = sum(max(0, -d["gdp_pt"]) for d in detail.values())
    pos_gdp = sum(max(0, d["gdp_pt"]) for d in detail.values())
    # 风险等级: 看负向 GDP 当量与净额
    if neg_gdp >= 0.15:
        tier = "高"
    elif neg_gdp >= 0.06:
        tier = "中"
    else:
        tier = "低"
    return {"w_profit_pct": round(w_profit, 2),
            "gdp_cum_pt": round(gdp_cum, 3),
            "gdp_neg_pt": round(-neg_gdp, 3),
            "gdp_pos_pt": round(pos_gdp, 3),
            "emp_exposed_wan": round(emp_wan, 1),
            "risk_tier": tier,
            "detail": detail}


def snapshot(r) -> dict:
    """Extract compact per-scenario result + heat series + macro risk."""
    fx = r["fx_path"]
    yrs = list(range(fx.shape[1]))
    cap = r["capital_inflow"]
    df = r["industry_profit"]
    ind_final = {k: round(float(v) * 100, 1)
                 for k, v in df.iloc[-1].items()}
    ind_series = {}
    for k in df.columns:
        ind_series[k] = [round(float(v) * 100, 2) for v in df[k].iloc[1:]]
    return {
        "fx_median": [round(float(np.median(fx[:, t])), 4) for t in yrs],
        "fx_lo": [round(float(np.percentile(fx[:, t], 25)), 4) for t in yrs],
        "fx_hi": [round(float(np.percentile(fx[:, t], 75)), 4) for t in yrs],
        "fx_5y": round(float(np.median(fx[:, -1])), 3),
        "apprec_5y_pct": round(float(np.median(r["appreciation"], axis=0)[-1]), 1),
        "industry": ind_final,
        "ind_series": ind_series,
        "macro": macro_risk(ind_final),
        "waterfall": {"loss": round(cap["export_loss"], 3),
                      "inflow": round(cap["cumulative_inflow"], 3),
                      "deepening": round(cap["deepening_gain"], 3),
                      "net": round(cap["net_benefit"], 3)},
        "returns": {"equity": round(float(r["equity_return"].iloc[-1]) * 100, 1),
                    "bond": round(float(r["bond_return"]) * 100, 1),
                    "gold": round(float(np.median(r["gold_return"])) * 100, 1),
                    "metal": round(float(np.median(r["commodity_return"])) * 100, 1)},
    }


def build_presets(n_sim: int = N, seed: int = SEED, live: dict = None) -> list:
    base_p, base_cap = load_project_config()
    if live:
        base_p = replace(base_p, cny_spot=live.get("spot", REAL_SPOT),
                         cny_vol=live.get("vol3y", REAL_VOL))
    presets = []

    EN = {
        "p0": ("No appreciation 0%", "base params, zero-drift control"),
        "p3": ("Slow 3%", "base params, mild appreciation"),
        "p6": ("Base 6%", "base params (config.yaml), policy-driven"),
        "p10": ("Fast 10%", "aggressive, accelerated transition"),
        "p6c": ("6% + conservative capital", "inflow at historical norm (6.5%/yr, weak drain)"),
        "p6x": ("6% + aggressive drain", "peak dollar-scarcity (15%/yr, strong drain)"),
        "p6r": ("Real-calibrated 6%", "calibrated: spot 6.71 + 3y vol 2.84%"),
        "piv": ("Realized inertia 2.7%", "realized 3y drift 2.7%/yr"),
    }

    def add(key, label, params, cap_cfg=None, note=""):
        r = ScenarioEngine(params, capital_cfg=cap_cfg or base_cap).run()
        s = snapshot(r)
        en = EN.get(key, (label, note))
        s.update({"key": key, "label": label, "note": note,
                  "label_en": en[0], "note_en": en[1]})
        presets.append(s)

    p0 = replace(base_p, cny_annual_apprec=0.00, n_simulations=n_sim, seed=seed)
    p3 = replace(base_p, cny_annual_apprec=0.03, n_simulations=n_sim, seed=seed)
    p6 = replace(base_p, cny_annual_apprec=0.06, n_simulations=n_sim, seed=seed)
    p10 = replace(base_p, cny_annual_apprec=0.10, n_simulations=n_sim, seed=seed)
    cap_con = replace(base_cap, equity_inflow_rate=0.065, dollar_drain_boost=0.20)
    cap_agg = replace(base_cap, equity_inflow_rate=0.15,
                      dollar_drain_boost=0.90, bond_inflow_rate=0.12)

    add("p0", "不升值 0%", p0, note="基准参数, 汇率零漂移对照")
    add("p3", "慢速升值 3%", p3, note="基准参数, 温和升值")
    add("p6", "基准情景 6%", p6, note="基准参数 (config.yaml), 政策驱动升值")
    add("p10", "快速升值 10%", p10, note="激进升值, 转型加速情景")
    add("p6c", "6% + 保守资本", p6, cap_cfg=cap_con,
        note="资本流入按北向历史常态 (6.5%/年, 弱美元荒)")
    add("p6x", "6% + 激进美元荒", p6, cap_cfg=cap_agg,
        note="美元流动性稀缺峰值情景 (15%/年, 强美元荒)")
    add("p6r", "实测校准 6%", p6, note="实测: 即期6.71 + 3y波动2.84%, 6%情景")
    add("piv", "现实惯性 2.7%", piv(p6, live),
        note="实测: 近3年实际升值漂移 2.7%/年")
    return presets


def piv(p6, live):
    """Re-derive inertia preset params from the live-adjusted base."""
    inertia = (live or {}).get("inertia_apprec", INERTIA_APPREC)
    return replace(p6, cny_annual_apprec=inertia)


def build_grid(step: float = 0.005, n_sim: int = GRID_N, seed: int = GRID_SEED,
               live: dict = None) -> list:
    """Appreciation-rate grid powering the dashboard slider (0..10%)."""
    base_p, base_cap = load_project_config()
    if live:
        base_p = replace(base_p, cny_spot=live.get("spot", REAL_SPOT),
                         cny_vol=live.get("vol3y", REAL_VOL))
    out = []
    rates = np.arange(-0.05, 0.15001, step)   # 2026-09: 覆盖贬值(-5%)至超速升值(15%)
    for rate in rates:
        p = replace(base_p, cny_annual_apprec=float(rate),
                    n_simulations=n_sim, seed=seed)
        r = ScenarioEngine(p, capital_cfg=base_cap).run()
        s = snapshot(r)
        s.update({"key": "custom", "rate_pct": round(float(rate) * 100, 1),
                  "label": "自定义 %.1f%%" % (rate * 100),
                  "note": "基准参数 + 升值速度 %.1f%% (400 次 MC)" % (rate * 100),
                  "label_en": "Custom %.1f%%" % (rate * 100),
                  "note_en": "base params + speed %.1f%% (400 MC)" % (rate * 100)})
        out.append(s)
    return out


def get_live():
    """Best-effort live calibration; graceful fallback on any failure."""
    live = {"spot": REAL_SPOT, "vol3y": REAL_VOL, "inertia_apprec": INERTIA_APPREC,
            "as_of": None, "live": False, "note": "offline defaults"}
    try:
        from data_loader import ensure_data
        from calibrate import fx_realized_stats
        data = ensure_data(refresh=True)
        fx = data.get("fx_fred")
        if fx is not None and len(fx) > 60:
            st = fx_realized_stats(fx)
            live["as_of"] = st.get("as_of")
            vol = st.get("3y", {}).get("annual_vol")
            d1 = st.get("1y", {}).get("annual_drift")
            d3 = st.get("3y", {}).get("annual_drift")
            if vol and vol < 0.15:
                live["vol3y"] = round(float(vol), 4)
            if d3 is not None:
                live["inertia_apprec"] = round(max(-0.10, min(0.10, -float(d3))), 4)
            live["drift1y"] = round(float(d1), 4) if d1 is not None else None
        sp = data.get("spot", {})
        if sp.get("whUSDCNY") and sp["whUSDCNY"].get("price"):
            live["spot"] = float(sp["whUSDCNY"]["price"])
        live["live"] = True
        live["note"] = "live FRED/Tencent"
    except Exception as e:
        live["note"] = "live failed (%s) - offline defaults" % type(e).__name__
    return live


def _net_band():
    """9x 参数区间(来自 tools/sensitivity_9x.json; 失败回落静态值)。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "tools", "sensitivity_9x.json")
        d = json.load(open(p, encoding="utf-8"))
        r = d["ratio_9x_pct"]
        return {"lo": r[0], "med": r[2], "hi": r[4],
                "note": d.get("note", "")}
    except Exception:
        return {"lo": 7.0, "med": 9.7, "hi": 13.0, "note": "fallback static"}


def _policy_rows(grid):
    """卢氏三原则 dials per grid rate (统一 policy_engine, 双口径, open .40/.25)。"""
    import policy_engine as pe
    rows = []
    for g in grid:
        low = g["industry"].get("export_lowend", 0.0)
        rate = g["rate_pct"] / 100.0
        def ev_at(op):
            p = pe.UnifiedParams(openness=op)
            # 拨盘行 = 纯速度口径(政策工具为零; 政策分摊见 insight/k 解)
            return pe.evaluate(rate, p, pe.ImportTools(0, 0, 0, 0),
                               profit_shock_pct=low)
        e40 = ev_at(0.40); e25 = ev_at(0.25)
        by = None
        for t in range(1, 13):
            if pe.trade_surplus_t(rate, pe.UnifiedParams(), t) <= 0.3:
                by = t
                break
        rows.append({"r": g["rate_pct"],
                     "ia": e40["inflation"]["absorbed_pct"],
                     "se": e40["surplus_t"], "rp": max(
                         0, round((1 - e40["surplus_t"] / 1.2) * 100, 1)),
                     "by": by if by else -1,
                     "di": e40["deind"]["profit_shock_pct"],
                     "dg": e40["deind"]["gdp_erode_pt"],
                     "f40": e40["flight_gdp_pct"], "v40": e40["verdict"],
                     "f25": e25["flight_gdp_pct"], "v25": e25["verdict"]})
    return {"rows": rows,
            "oil_scen": "油价+30%, 5y; EPT 0.35 分层",
            "insight": ("[政策带前提: 以升值为主动力, 进口政策只补足差额] 统一引擎(V2a利润 x V2b GDP x V3工具 x V4外储): 双口径红线均35 - "
                        "利润口径 6%=28.8 带内 / 8%=40.5 破线; GDP侵蚀口径 6%=2.9。"
                        "固定速度带最小政策度: 6% 只需 k=0.05(政策承担16%, 速度84%, "
                        "财政0.04%GDP); 5% 需 k=0.10(政策30%)。8%+ 去工业化(利润)超限。"),
            "insight_en": ("[Premise: appreciation-led; import policy only tops up] Unified engine (V2a profit x V2b GDP x V3 tools x V4 reserves): dual redlines at 35 - profit basis 6%=28.8 inside / 8%=40.5 breach; GDP-erosion 6%=2.9. Fixed-speed min-policy-k: 6% needs k=0.05 (policy 16%, speed 84%, fiscal 0.04%GDP); 5% needs k=0.10 (policy 30%). 8%+ breaches deindustrialization (profit).")}


def _outlook(live):
    from outlook import compute as oc
    spot = (live or {}).get("spot", REAL_SPOT)
    vol = (live or {}).get("vol3y", REAL_VOL)
    inert = (live or {}).get("inertia_apprec", INERTIA_APPREC)
    o = oc(spot0=spot, vol=vol, inertia=inert)
    for r in o["rows"]:
        r["level"] = float(r["level"]); r["band_lo"] = float(r["band_lo"])
        r["band_hi"] = float(r["band_hi"]); r["usd10k_cny"] = float(r["usd10k_cny"])
        r["chg_pct"] = float(r["chg_pct"]); r["drift"] = float(r["drift"])
    for ev in o["events"]:
        if "date" in ev:
            ev["date"] = str(ev["date"])
    return o


def export(html_out: str = None, live: dict = None) -> dict:
    presets = build_presets(live=live)
    grid = build_grid(live=live)
    payload = {
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_simulations": N,
        "grid_n": GRID_N,
        "disclaimer": "研究框架, 不构成投资建议。数据源: FRED / 腾讯行情 / akshare, 截至 2026-09。"
                      "GDP/就业为利润冲击的当量近似(利润率8%、就业弹性0.5), 非预测。",
        "disclaimer_en": "Research framework, not investment advice. Sources: FRED / Tencent / akshare, as of 2026-09. GDP/employment are profit-shock equivalents (8% margin, 0.5 elasticity), not forecasts.",
        "macro_meta": {"margin": MARGIN, "emp_elast": EMP_ELAST,
                       "urban_emp_wan": URBAN_EMP_WAN,
                       "note": "GDP当量 = 增加值权重×利润冲击×利润率; 就业当量 = 就业权重×冲击×弹性"},
        "presets": presets,
        "grid": grid,
        "policy": _policy_rows(grid),
        "net_band": _net_band(),
        "outlook": _outlook(live),
        "live": live or {"spot": REAL_SPOT, "vol3y": REAL_VOL,
                         "inertia_apprec": INERTIA_APPREC, "live": False,
                         "note": "offline defaults"},
    }
    if html_out is None:
        html_out = os.path.join(BASE, "dashboard.html")
    token = "/*__DASH_DATA__*/"
    blob = "const DASH_DATA = " + json.dumps(payload, ensure_ascii=False,
                                             indent=1) + ";"
    # zh
    with open(os.path.join(BASE, "dashboard_template.html"),
              encoding="utf-8") as f:
        html = f.read()
    assert token in html, "template token missing"
    html = html.replace(token, blob)
    for out_name in (html_out, os.path.join(BASE, "index.html")):
        with open(out_name, "w", encoding="utf-8") as f:
            f.write(html)
    # en
    en_tpl = os.path.join(BASE, "dashboard_template_en.html")
    if os.path.exists(en_tpl):
        with open(en_tpl, encoding="utf-8") as f:
            en_html = f.read()
        en_html = en_html.replace(token, blob)
        for out_name in (os.path.join(BASE, "dashboard_en.html"),
                         os.path.join(BASE, "index_en.html")):
            with open(out_name, "w", encoding="utf-8") as f:
                f.write(en_html)
    with open(os.path.join(BASE, "dashboard_data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("dashboard written: %.1f KB | presets=%d grid=%d"
          % (os.path.getsize(html_out) / 1024.0, len(presets), len(grid)))
    return payload


if __name__ == "__main__":
    # 默认总是使用实时校准(含最新 spot)；--live 仅为兼容参数(强制刷新数据源)
    live = get_live()
    if live and live.get("live"):
        print("live calibration: spot=%.4f vol3y=%.4f inertia=%.4f as_of=%s"
              % (live["spot"], live["vol3y"], live["inertia_apprec"],
                 live.get("as_of")))
    export(live=live)
