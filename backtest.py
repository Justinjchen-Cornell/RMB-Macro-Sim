# -*- coding: utf-8 -*-
"""
backtest.py - Empirical diagnostics & channel validation
=========================================================
1) northbound_flow_reg : does capital inflow actually follow CNY moves?
   (yearly northbound net 2015-2023 vs USD/CNY annual change, lag 0/1)
2) sector_episodes     : realized sector ETF behavior around CNY episodes
   (2019-2026, 6m windows) - check vs model priors & measured betas
3) diag_flatness       : why is net benefit nearly flat over 0-10%?
   decomposes export loss / inflow / net across -5%..+15% drifts and
   reveals saturation artifacts (profit clip, attractiveness cap).

Usage: python backtest.py
"""
import os
import sys
import json
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from data_loader import _load, fetch_tencent_kline
from calibrate import equity_inflow_calib
from model import MacroParams, ScenarioEngine, load_project_config
from dataclasses import replace

RAW = os.path.join(BASE, "data", "raw")


def _fx_series():
    df = _load("fred_dexchus")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def northbound_flow_reg():
    nb = _load("northbound")
    fx = _fx_series()
    fx["date"] = pd.to_datetime(fx["date"])
    old = nb.copy()
    old["date"] = pd.to_datetime(old["date"])
    old = old[old["date"] < pd.Timestamp("2024-08-19")].copy()
    old["net"] = pd.to_numeric(old["当日成交净买额"].astype(str)
                               .str.replace(",", ""), errors="coerce")
    old["year"] = old["date"].dt.year
    yearly = old.groupby("year")["net"].sum() / 10000.0          # T RMB
    fxm = fx.set_index("date")["usdcny"].astype(float).resample("YE").last()
    fxm.index = fxm.index.year                                # align with int years
    fx_chg = fxm.pct_change() * 100                            # + = CNY deprec
    tab = pd.concat([yearly.rename("nb_net_Trmb"),
                     fx_chg.rename("fx_chg_pct")], axis=1).dropna()
    tab["fx_chg_lag1"] = tab["fx_chg_pct"].shift(1)
    tab = tab.dropna(subset=["fx_chg_lag1"])
    out = {"n": int(len(tab))}
    for col, name in [("fx_chg_pct", "same_year"), ("fx_chg_lag1", "lag1_year")]:
        x = tab[col].values
        y = tab["nb_net_Trmb"].values
        if len(x) > 3:
            c = np.corrcoef(x, y)[0, 1]
            A = np.column_stack([np.ones(len(x)), x])
            b, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            res = y - A @ b
            dof = len(y) - 2
            se = np.sqrt(np.diag((res @ res / dof) * np.linalg.inv(A.T @ A)))
            out[name] = {"corr": round(float(c), 3),
                         "beta_Trmb_per_pct_fx": round(float(b[1]), 4),
                         "t": round(float(b[1] / se[1]), 2),
                         "n": int(len(x))}
    return out


def _etf(name, code):
    try:
        return fetch_tencent_kline(code, start="2019-01-01")
    except Exception as e:
        print("  etf fetch fail", name, str(e)[:60])
        return None


def sector_episodes():
    fx = _fx_series()
    fx = fx[fx["date"] >= "2018-06-01"]                       # ETF 代理自2019起
    fxm = fx.set_index("date")["usdcny"].astype(float).resample("ME").last()
    chg6 = fxm.pct_change(6) * 100
    # 找 6 个月 |变动|>4% 的非重叠窗口
    eps = []
    used_end = None
    for dt_, v in chg6.items():
        if abs(v) < 4.0:
            continue
        start = dt_ - pd.DateOffset(months=5)
        if used_end is None or start >= used_end:
            eps.append({"start": start, "end": dt_, "chg": round(float(v), 2)})
            used_end = dt_
            if len(eps) >= 10:
                break
    etfs = {"semiconductor": "sh512480", "metals": "sh512400",
            "gold": "sh518880", "banks": "sh512800",
            "hightech": "sh515050", "mkt": "sh510300"}
    closes = {k: _etf(k, c) for k, c in etfs.items()}
    rows = []
    for ep in eps:
        r = {"start": str(ep["start"].date()), "end": str(ep["end"].date()),
             "fx_chg6_pct": ep["chg"],
             "type": "appreciation" if ep["chg"] < 0 else "depreciation"}
        for name in ["semiconductor", "metals", "gold", "banks", "hightech"]:
            df = closes.get(name)
            m = closes.get("mkt")
            if df is None or m is None:
                continue
            seg = df[(df["date"] >= ep["start"]) & (df["date"] <= ep["end"])]
            segm = m[(m["date"] >= ep["start"]) & (m["date"] <= ep["end"])]
            if len(seg) > 3 and len(segm) > 3:
                ret = seg["close"].iloc[-1] / seg["close"].iloc[0] - 1
                retm = segm["close"].iloc[-1] / segm["close"].iloc[0] - 1
                r[name] = round(float((ret - retm) * 100), 2)
            else:
                r[name] = None
        rows.append(r)
    return rows


def diag_flatness():
    """现状 vs 建议参数: 净效益及其分解随升值速度 (负=贬值)。"""
    mp, cc = load_project_config()
    rates = np.arange(-0.05, 0.151, 0.025)
    rows = []
    for rate in rates:
        p = replace(mp, cny_annual_apprec=float(rate),
                    n_simulations=400, seed=7)
        r = ScenarioEngine(p, capital_cfg=cc).run()
        cap = r["capital_inflow"]
        rows.append({"rate_pct": round(rate * 100, 1),
                     "loss": round(cap["export_loss"], 3),
                     "inflow": round(cap["cumulative_inflow"], 3),
                     "deepening": round(cap["deepening_gain"], 3),
                     "net": round(cap["net_benefit"], 3),
                     "lowend": round(r["industry_profit"]
                                     ["export_lowend"].iloc[-1] * 100, 1)})
    return rows


def main():
    print("=" * 64)
    print("  backtest.py - empirical diagnostics")
    print("=" * 64)
    out = {}
    out["northbound_fx"] = northbound_flow_reg()
    print("\n[1] Northbound net inflow vs CNY move (yearly, T RMB):")
    print(json.dumps(out["northbound_fx"], ensure_ascii=False, indent=1))
    out["episodes"] = sector_episodes()
    print("\n[2] FX episodes 2019-2026 (6m windows):")
    for r in out["episodes"]:
        print("  %s->%s fx%+.1f%% %-13s semi=%s metals=%s gold=%s banks=%s tech=%s"
              % (r["start"], r["end"], r["fx_chg6_pct"], r["type"],
                 r.get("semiconductor"), r.get("metals"), r.get("gold"),
                 r.get("banks"), r.get("hightech")))
    out["flatness_current"] = diag_flatness()
    print("\n[3] Flatness diagnosis (current params): rate% | loss | inflow | net | lowend")
    for r in out["flatness_current"]:
        print("  %+5.1f  %+6.3f  %+6.3f  %+6.3f  %+6.1f"
              % (r["rate_pct"], r["loss"], r["inflow"], r["net"], r["lowend"]))
    with open(os.path.join(BASE, "data", "backtest_out.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("\n[4] saved -> data/backtest_out.json")


if __name__ == "__main__":
    main()
