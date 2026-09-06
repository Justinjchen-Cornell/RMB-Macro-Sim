# -*- coding: utf-8 -*-
"""
run_real.py - Real-data calibrated simulation pipeline (2026-09)
================================================================
  Step 1  load/fetch real data            (data_loader)
  Step 2  calibrate FX / northbound / export / industry  (calibrate)
  Step 3  run 3 scenarios:
            A  baseline assumptions (spot 7.20, vol 4%, apprec 6%)
            B  real-calibrated        (spot ~6.71, vol from history, apprec 6%)
            C  real inertia           (B + apprec = trailing 3y realized drift)
  Step 4  print comparison + save calib_results.json

Usage:  python run_real.py [--refresh] [--skip-industry] [--charts]
ASCII prints only (report md authored separately).
"""

import os
import sys
import json
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from data_loader import ensure_data, fetch_tencent_kline
from calibrate import (fx_realized_stats, equity_inflow_calib,
                       export_value_elasticity, industry_fx_beta)
from model import MacroParams, ScenarioEngine
from capital_inflow import CapitalConfig

REFRESH = "--refresh" in sys.argv
SKIP_IND = "--skip-industry" in sys.argv
MAKE_CHARTS = "--charts" in sys.argv

ETF_MAP = {
    "export_hightech": "sh515050",    # 通信ETF (tech exporters)
    "domestic_consumption": "sz159928",
    "real_estate": "sh512200",
    "new_energy": "sh516160",
    "semiconductor": "sh512480",
    "commodity_metals": "sh512400",
    "power_compute": "sz159995",      # 芯片ETF (AI compute proxy)
    "gold": "sh518880",
    "bank_insurance": "sh512800",
}
MKT_CODE = "sh510300"


def _s(d):  # safe scalar
    return d if d == d else None


def main():
    print("=" * 66)
    print("  macro_sim REAL-DATA pipeline (2026-09)")
    print("=" * 66)

    # ── Step 1: data ────────────────────────────────
    data = ensure_data(refresh=REFRESH)
    fx = data["fx_fred"]
    exports = data["exports_cn"]
    nb = data["northbound"]
    spot = float(data["spot"]["whUSDCNY"]["price"])
    print("\n[1] data ready | USD/CNY spot = %.4f (Tencent)" % spot)

    # ── Step 2: calibrate ───────────────────────────
    fx_stats = fx_realized_stats(fx)
    print("\n[2] FX realized stats (USD/CNY daily, FRED DEXCHUS):")
    print("    spot(last) = %.4f  as_of=%s" % (fx_stats.get("spot", 0), fx_stats.get("as_of", "")))
    for k in ["1y", "3y", "5y", "10y"]:
        if k in fx_stats:
            v = fx_stats[k]
            print("    %-4s annual_vol=%.2f%%  drift=%.2f%%  n=%d"
                  % (k, v["annual_vol"] * 100, v["annual_drift"] * 100, v["n"]))

    eq = equity_inflow_calib(nb, usdcny=spot)
    print("\n[2b] Northbound -> equity channel calibration:")
    for kk in ["northbound_annual_net_T_rmb_mean", "northbound_holdings_T_rmb_mean",
               "full_scope_holdings_T_rmb_est", "full_scope_holdings_T_usd_est",
               "historical_rate", "rate_used_by_model"]:
        print("    %-34s %s" % (kk, eq.get(kk)))

    ex = export_value_elasticity(exports, fx)
    print("\n[2c] Export value elasticity (12m log-diff OLS):")
    for kk in ["n", "period", "beta_d12", "se", "t", "r2"]:
        print("    %-10s %s" % (kk, ex.get(kk)))
    print("    note:", ex.get("note", ""))

    ind = {}
    if not SKIP_IND:
        print("\n[2d] Industry FX betas (ETF monthly vs MKT + USD/CNY, fetching...)")
        closes = {}
        for name, code in ETF_MAP.items():
            try:
                closes[name] = fetch_tencent_kline(code, start="2019-01-01")
            except Exception as e:
                print("    fetch fail", name, str(e)[:60])
        mkt = fetch_tencent_kline(MKT_CODE, start="2019-01-01")
        ind = industry_fx_beta(closes, mkt_closes=mkt, fx=fx)
        for name, r in sorted(ind.items()):
            if "error" in r:
                print("    %-22s error %s" % (name, r["error"]))
            else:
                print("    %-22s beta_fx=%.4f t=%+.2f r2=%.2f  (%s)"
                      % (name, r["beta_fx_per_1pct"], r["t"], r["r2"], r["interpret"]))

    # ── Step 3: scenarios ───────────────────────────
    print("\n[3] simulating...")
    vol3y = fx_stats.get("3y", {}).get("annual_vol", 0.04)
    drift3y = fx_stats.get("3y", {}).get("annual_drift", 0.0)   # + = CNY deprec
    drift_inertia = max(-0.10, min(0.10, -drift3y))             # 升值取正
    print("    real vol(3y)=%.2f%%  real drift(3y)=%.2f%%  -> inertia apprec=%.2f%%"
          % (vol3y * 100, drift3y * 100, drift_inertia * 100))

    N, SEED = 2000, 42
    scen = {
        "A_assumption": dict(cny_spot=7.20, cny_annual_apprec=0.06, cny_vol=0.04),
        "B_realvol":    dict(cny_spot=spot, cny_annual_apprec=0.06,
                             cny_vol=vol3y if vol3y < 0.15 else 0.04),
        "C_inertia":    dict(cny_spot=spot, cny_annual_apprec=drift_inertia,
                             cny_vol=vol3y if vol3y < 0.15 else 0.04),
    }
    out = {}
    for name, ov in scen.items():
        p = MacroParams(cny_spot=ov["cny_spot"],
                        cny_annual_apprec=ov["cny_annual_apprec"],
                        cny_vol=ov["cny_vol"],
                        n_simulations=N, seed=SEED)
        r = ScenarioEngine(p).run()
        out[name] = r
        cap = r["capital_inflow"]
        print("  %-14s fx5y=%.3f lowend=%+.1f%% semi=%+.1f%% gold=%+.1f%% | "
              "eq_ret=%+.1f%% | inflow=%.2f net=%.2f T$"
              % (name, np.median(r["fx_path"], axis=0)[-1],
                 r["industry_profit"]["export_lowend"].iloc[-1] * 100,
                 r["industry_profit"]["semiconductor"].iloc[-1] * 100,
                 r["industry_profit"]["gold"].iloc[-1] * 100,
                 float(r["equity_return"].iloc[-1]) * 100,
                 cap["cumulative_inflow"], cap["net_benefit"]))

    # ── Step 4: persist ─────────────────────────────
    summaries = {}
    for name, r in out.items():
        cap = r["capital_inflow"]
        summaries[name] = {
            "fx_5y_median": round(float(np.median(r["fx_path"], axis=0)[-1]), 3),
            "apprec_5y_median_pct": round(float(np.median(r["appreciation"], axis=0)[-1]), 1),
            "industry_final_pct": {k: round(float(v) * 100, 1)
                                   for k, v in r["industry_profit"].iloc[-1].items()},
            "equity_ret_pct": round(float(r["equity_return"].iloc[-1]) * 100, 1),
            "bond_ret_pct": round(float(r["bond_return"]) * 100, 1),
            "gold_ret_pct": round(float(np.median(r["gold_return"])) * 100, 1),
            "capital": {"export_loss": round(cap["export_loss"], 3),
                        "inflow": round(cap["cumulative_inflow"], 3),
                        "deepening": round(cap["deepening_gain"], 3),
                        "net": round(cap["net_benefit"], 3)},
        }
    cal = {"fx_stats": fx_stats, "equity": eq, "export": ex,
           "industry": ind, "spot": spot,
           "scenarios": summaries}
    with open(os.path.join(BASE, "calib_results.json"), "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=1)
    print("\n[4] calib_results.json saved")

    if MAKE_CHARTS:
        from visualize import plot_capital_waterfall, plot_scenario_wall
        os.makedirs(os.path.join(BASE, "charts_real"), exist_ok=True)
        for name in ["B_realvol", "C_inertia"]:
            cap = out[name]["capital_inflow"]
            plot_capital_waterfall(cap, os.path.join(BASE, "charts_real",
                                                     "waterfall_%s.png" % name))
        wall = {"A 原假设(7.20/6%)": out["A_assumption"],
                "B 实测参数(6.71/6%)": out["B_realvol"],
                "C 现实惯性(6.71/2.7%)": out["C_inertia"]}
        plot_scenario_wall(wall, os.path.join(BASE, "charts_real",
                                              "scenario_wall.png"),
                           title="RMB-Macro-Sim · 三情景对比 (2000 次 Monte Carlo)")
        print("    charts_real/ scenario_wall + waterfall_B/C saved")

    print("\n" + "=" * 66)
    print("  done. Details -> calib_results.json ; report md authored separately")
    print("=" * 66)


if __name__ == "__main__":
    main()
