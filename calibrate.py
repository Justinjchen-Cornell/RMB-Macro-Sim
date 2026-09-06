# -*- coding: utf-8 -*-
"""
calibrate.py - Estimate model parameters from real data (2026-09)
=================================================================
  1) fx_realized_stats    : annualized vol + drift of USD/CNY (windows)
  2) equity_inflow_calib  : northbound -> equity_inflow_rate / base
  3) export_value_elasticity : 12m log-diff OLS vs USD/CNY
  4) industry_fx_beta     : ETF proxies vs MKT-adjusted USD/CNY beta

All functions pure (take DataFrames). No network here - use data_loader.
ASCII-only. numpy + pandas only.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252
FX_TODAY = 6.71           # fallback if spot missing


def fx_realized_stats(df: pd.DataFrame) -> dict:
    """Annualized vol/drift over trailing 1/3/5/10y windows."""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date")
    s = d["usdcny"].astype(float)
    rets = np.log(s).diff().dropna()
    last_day = d["date"].max()
    out = {"as_of": str(last_day.date()), "spot": round(float(s.iloc[-1]), 4)}
    for label, days in [("1y", 365), ("3y", 3 * 365), ("5y", 5 * 365),
                        ("10y", 10 * 365), ("all", 40 * 365)]:
        cutoff = last_day - pd.Timedelta(days=days)
        mask = d["date"].iloc[1:].values >= np.datetime64(cutoff)
        rsel = rets.values[mask]
        if len(rsel) < 40:
            continue
        vol = float(np.std(rsel, ddof=1) * np.sqrt(TRADING_DAYS))
        drift = float(np.mean(rsel) * TRADING_DAYS)   # + = CNY depreciates
        out[label] = {"annual_vol": round(vol, 4), "annual_drift": round(drift, 4),
                      "n": int(len(rsel))}
    return out


def equity_inflow_calib(nb: pd.DataFrame, usdcny: float = FX_TODAY) -> dict:
    """
    Northbound history -> annual net inflow & holdings (valid to 2024-08).
    After the 2024-08 disclosure reform no daily northbound data exists
    (dark period) - flagged, not fabricated.
    scope_factor ~1.7 lifts northbound holdings to full foreign-A scope
    (northbound ~60% incl. QFII/other).
    """
    df = nb.copy()
    df["date"] = pd.to_datetime(df["date"])
    old = df[df["date"] < pd.Timestamp("2024-08-19")].copy()
    for c in ["当日成交净买额", "历史累计净买额", "持股市值"]:
        old[c] = pd.to_numeric(old[c].astype(str).str.replace(",", ""), errors="coerce")
    old["year"] = old["date"].dt.year

    yearly = old.groupby("year")["当日成交净买额"].sum() / 10000.0       # T RMB
    net_T = yearly.reindex(range(2015, 2024)).dropna()                   # full years
    ye = old[old["date"].dt.month == 12].groupby("year")["持股市值"].last() / 1e12
    hold_T = ye.reindex(range(2017, 2024)).dropna()                      # T RMB

    mean_net = float(net_T.mean()) if len(net_T) else float("nan")
    mean_hold = float(hold_T.mean()) if len(hold_T) else float("nan")
    scope_factor = 1.7
    full_hold_rmb = mean_hold * scope_factor
    rate_hist = mean_net / full_hold_rmb if full_hold_rmb > 0 else float("nan")

    return {
        "northbound_annual_net_T_rmb_mean": round(mean_net, 3),
        "northbound_holdings_T_rmb_mean": round(mean_hold, 3),
        "full_scope_holdings_T_rmb_est": round(full_hold_rmb, 3),
        "full_scope_holdings_T_usd_est": round(full_hold_rmb / usdcny, 3),
        "historical_rate": round(rate_hist, 4),
        "rate_used_by_model": 0.1112,
        "yearly_net_T_rmb": {str(k): round(float(v), 3) for k, v in net_T.items()},
        "note": ("northbound daily net valid only through 2024-08 (disclosure reform); "
                 "2024-09+ is a dark period - use with scenario judgement"),
    }


def export_value_elasticity(exp: pd.DataFrame, fx: pd.DataFrame) -> dict:
    """
    OLS on 12-month log-diffs:
        d12 ln(exports_usd) = a + b * d12 ln(usdcny) + e
    b > 0 => CNY depreciation correlates with higher export VALUE.
    Note: value elasticity mixes volume + price; model needs volume - advisory.
    """
    e = exp.copy()
    e["month"] = pd.to_datetime(e["month"])
    e = e.set_index("month").sort_index()
    e = e.resample("ME").last()          # month-end alignment
    f = fx.copy()
    f["date"] = pd.to_datetime(f["date"])
    fm = f.set_index("date")["usdcny"].astype(float).resample("ME").last()

    tab = pd.concat([np.log(e["exports_usd"].astype(float)), np.log(fm)], axis=1)
    tab.columns = ["ly", "lx"]
    tab = tab.dropna()
    d = tab.diff(12).dropna()
    if len(d) < 24:
        return {"n": int(len(d)), "error": "insufficient obs"}
    X = np.column_stack([np.ones(len(d)), d["lx"].values])
    beta, _, _, _ = np.linalg.lstsq(X, d["ly"].values, rcond=None)
    resid = d["ly"].values - X @ beta
    dof = len(d) - 2
    se = np.sqrt(np.diag((resid @ resid / dof) * np.linalg.inv(X.T @ X)))
    t_b = beta[1] / se[1]
    r2 = 1 - (resid @ resid) / ((d["ly"].values - d["ly"].mean()) ** 2).sum()
    return {
        "n": int(len(d)),
        "period": [str(d.index[0].date()), str(d.index[-1].date())],
        "beta_d12": round(float(beta[1]), 4),
        "se": round(float(se[1]), 4),
        "t": round(float(t_b), 2),
        "r2": round(float(r2), 4),
        "model_elasticity": -0.45,
        "note": "value elasticity includes price; not auto-applied",
    }


def industry_fx_beta(etf_closes: dict, mkt_closes: pd.DataFrame = None,
                     fx: pd.DataFrame = None) -> dict:
    """
    Monthly regression r_i ~ a + b_m * r_mkt + b_fx * dln(usdcny).
    etf_closes: {industry: DataFrame(date, close)}.
    Returns b_fx (per +1% USDCNY = CNY depreciation), t, r2.
    """
    out = {}
    for name, dfx in etf_closes.items():
        try:
            d = dfx.copy()
            d["date"] = pd.to_datetime(d["date"])
            px = d.set_index("date")["close"].astype(float).resample("M").last()
            ri = np.log(px).diff()
            tab = pd.concat([ri], axis=1)
            tab.columns = ["ri"]
            if mkt_closes is not None:
                m = mkt_closes.copy()
                m["date"] = pd.to_datetime(m["date"])
                rm = np.log(m.set_index("date")["close"].astype(float)
                            .resample("M").last()).diff()
                rm.name = "rm"
                tab = pd.concat([tab, rm], axis=1).dropna()
            if fx is not None:
                f = fx.copy()
                f["date"] = pd.to_datetime(f["date"])
                fx_m = np.log(f.set_index("date")["usdcny"].astype(float)
                              .resample("M").last()).diff()
                fx_m.name = "dfx"
                tab = pd.concat([tab, fx_m], axis=1).dropna()
            else:
                tab = tab.dropna()
            if len(tab) < 30:
                out[name] = {"error": "obs<30", "n": int(len(tab))}
                continue
            cols = list(tab.columns)
            yy = tab["ri"].values
            if "rm" in cols and "dfx" in cols:
                X = np.column_stack([np.ones(len(tab)), tab["rm"], tab["dfx"]])
                names = ["const", "mkt", "fx"]
            elif "dfx" in cols:
                X = np.column_stack([np.ones(len(tab)), tab["dfx"]])
                names = ["const", "fx"]
            else:
                out[name] = {"error": "no fx regressor"}
                continue
            beta, _, _, _ = np.linalg.lstsq(X, yy, rcond=None)
            resid = yy - X @ beta
            dof = len(tab) - X.shape[1]
            se = np.sqrt(np.diag((resid @ resid / dof) * np.linalg.inv(X.T @ X)))
            bidx = names.index("fx")
            r2 = 1 - (resid @ resid) / ((yy - yy.mean()) ** 2).sum()
            out[name] = {
                "n": int(len(tab)),
                "beta_fx_per_1pct": round(float(beta[bidx]), 4),
                "t": round(float(beta[bidx] / se[bidx]), 2),
                "r2": round(float(r2), 4),
                "interpret": ("CNY depreciation HELPS" if beta[bidx] > 0
                              else "CNY depreciation HURTS"),
            }
        except Exception as ex:
            out[name] = {"error": str(ex)[:80]}
    return out
