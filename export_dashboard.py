# -*- coding: utf-8 -*-
"""
export_dashboard.py - Preset scenarios -> dashboard.html (single file)
=====================================================================
Runs 8 preset scenarios (2000 MC each, fixed seed), collects compact
results, and injects them into dashboard_template.html to produce:
  dashboard.html   (self-contained, double-click to open)
  index.html       (copy for GitHub Pages)
  dashboard_data.json (raw data for external use)

Usage:  python export_dashboard.py
"""
import os
import json
import sys
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from model import MacroParams, ScenarioEngine, load_project_config
from capital_inflow import CapitalConfig
from dataclasses import replace

N, SEED = 2000, 42
REAL_SPOT = 6.7108
REAL_VOL = 0.0284          # 3y realized
INERTIA_APPREC = 0.027     # 3y realized drift (appreciation)

# 升值漂移 0.06 基准下确定性路径中位终值约对应情景数值,由引擎计算


def build_presets(n_sim: int = N, seed: int = SEED, live: dict = None) -> list:
    base_p, base_cap = load_project_config()
    presets = []
    if live:
        base_p = replace(base_p, cny_spot=live.get("spot", REAL_SPOT),
                         cny_vol=live.get("vol3y", REAL_VOL))

    def add(key, label, params, cap_cfg=None, note=""):
        eng = ScenarioEngine(params, capital_cfg=cap_cfg or base_cap)
        r = eng.run()
        fx = r["fx_path"]
        yrs = list(range(fx.shape[1]))
        cap = r["capital_inflow"]
        industry = {k: round(float(v) * 100, 1)
                    for k, v in r["industry_profit"].iloc[-1].items()}
        presets.append({
            "key": key, "label": label, "note": note,
            "fx_median": [round(float(np.median(fx[:, t])), 4) for t in yrs],
            "fx_lo": [round(float(np.percentile(fx[:, t], 25)), 4) for t in yrs],
            "fx_hi": [round(float(np.percentile(fx[:, t], 75)), 4) for t in yrs],
            "fx_5y": round(float(np.median(fx[:, -1])), 3),
            "apprec_5y_pct": round(float(np.median(r["appreciation"], axis=0)[-1]), 1),
            "industry": industry,
            "waterfall": {"loss": round(cap["export_loss"], 3),
                          "inflow": round(cap["cumulative_inflow"], 3),
                          "deepening": round(cap["deepening_gain"], 3),
                          "net": round(cap["net_benefit"], 3)},
            "returns": {"equity": round(float(r["equity_return"].iloc[-1]) * 100, 1),
                        "bond": round(float(r["bond_return"]) * 100, 1),
                        "gold": round(float(np.median(r["gold_return"])) * 100, 1),
                        "metal": round(float(np.median(r["commodity_return"])) * 100, 1)},
        })

    p0 = replace(base_p, cny_annual_apprec=0.00, n_simulations=n_sim, seed=seed)
    p3 = replace(base_p, cny_annual_apprec=0.03, n_simulations=n_sim, seed=seed)
    p6 = replace(base_p, cny_annual_apprec=0.06, n_simulations=n_sim, seed=seed)
    p10 = replace(base_p, cny_annual_apprec=0.10, n_simulations=n_sim, seed=seed)

    # 保守资本: 北向历史常态 6.5% 流入率 + 弱美元荒
    cap_con = replace(base_cap, equity_inflow_rate=0.065,
                      dollar_drain_boost=0.20)
    # 激进资本: 升值+美元荒情景上限
    cap_agg = replace(base_cap, equity_inflow_rate=0.15,
                      dollar_drain_boost=0.90, bond_inflow_rate=0.12)

    live_apprec = live.get("inertia_apprec", INERTIA_APPREC) if live else INERTIA_APPREC
    p6r = replace(base_p, cny_spot=base_p.cny_spot, cny_vol=base_p.cny_vol,
                  cny_annual_apprec=0.06, n_simulations=n_sim, seed=seed)
    piv = replace(base_p, cny_spot=base_p.cny_spot, cny_vol=base_p.cny_vol,
                  cny_annual_apprec=live_apprec,
                  n_simulations=n_sim, seed=seed)

    add("p0", "不升值 0%", p0, note="基准参数, 汇率零漂移对照")
    add("p3", "慢速升值 3%", p3, note="基准参数, 温和升值")
    add("p6", "基准情景 6%", p6, note="基准参数 (config.yaml), 政策驱动升值")
    add("p10", "快速升值 10%", p10, note="激进升值, 转型加速情景")
    add("p6c", "6% + 保守资本", p6, cap_cfg=cap_con,
        note="资本流入按北向历史常态 (6.5%/年, 弱美元荒)")
    add("p6x", "6% + 激进美元荒", p6, cap_cfg=cap_agg,
        note="美元流动性稀缺峰值情景 (15%/年, 强美元荒)")
    add("p6r", "实测校准 6%", p6r, note="实测: 即期6.71 + 3y波动2.84%, 6%情景")
    add("piv", "现实惯性 2.7%", piv, note="实测: 近3年实际升值漂移 2.7%/年")
    return presets


def get_live():
    """Best-effort live calibration. Falls back gracefully on any failure."""
    live = {"spot": REAL_SPOT, "vol3y": REAL_VOL,
            "inertia_apprec": INERTIA_APPREC, "as_of": None,
            "live": False, "note": "offline defaults"}
    try:
        from data_loader import ensure_data
        from calibrate import fx_realized_stats
        data = ensure_data(refresh=True)
        fx = data.get("fx_fred")
        if fx is not None and len(fx) > 60:
            st = fx_realized_stats(fx)
            live["as_of"] = st.get("as_of")
            vol = st.get("3y", {}).get("annual_vol")
            drift1 = st.get("1y", {}).get("annual_drift")
            drift3 = st.get("3y", {}).get("annual_drift")
            if vol and vol < 0.15:
                live["vol3y"] = round(float(vol), 4)
            if drift3 is not None:
                live["inertia_apprec"] = round(max(-0.10, min(0.10, -float(drift3))), 4)
            live["drift1y"] = round(float(drift1), 4) if drift1 is not None else None
        sp = data.get("spot", {})
        if sp.get("whUSDCNY") and sp["whUSDCNY"].get("price"):
            live["spot"] = float(sp["whUSDCNY"]["price"])
        live["live"] = True
        live["note"] = "live FRED/Tencent"
    except Exception as e:
        live["note"] = "live failed (%s) - offline defaults" % type(e).__name__
    return live


def export(html_out: str = None, live: dict = None) -> dict:
    presets = build_presets(live=live)
    payload = {
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_simulations": N,
        "disclaimer": "研究框架, 不构成投资建议。数据源: FRED / 腾讯行情 / akshare, 截至 2026-09。",
        "presets": presets,
        "live": live or {"spot": REAL_SPOT, "vol3y": REAL_VOL,
                         "inertia_apprec": INERTIA_APPREC, "live": False,
                         "note": "offline defaults"},
    }
    if html_out is None:
        html_out = os.path.join(BASE, "dashboard.html")
    tpl = os.path.join(BASE, "dashboard_template.html")
    with open(tpl, encoding="utf-8") as f:
        html = f.read()
    token = "/*__DASH_DATA__*/"
    assert token in html, "template token missing"
    html = html.replace(token, "const DASH_DATA = " + json.dumps(
        payload, ensure_ascii=False, indent=1) + ";")

    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(BASE, "dashboard_data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # quick sanity: parse back embedded JSON
    with open(html_out, encoding="utf-8") as f:
        blob = f.read()
    head = blob.index("const DASH_DATA = ") + len("const DASH_DATA = ")
    js = blob[head: blob.index(";\n", head)]
    back = json.loads(js)
    print("dashboard.html written: %.1f KB, presets=%d"
          % (os.path.getsize(html_out) / 1024.0, len(back["presets"])))
    return back


if __name__ == "__main__":
    live = get_live() if ("--live" in sys.argv) else None
    if live and live.get("live"):
        print("live calibration: spot=%.4f vol3y=%.4f inertia=%.4f as_of=%s"
              % (live["spot"], live["vol3y"], live["inertia_apprec"], live.get("as_of")))
    export(live=live)
