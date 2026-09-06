# -*- coding: utf-8 -*-
"""
test_real_calib.py - offline unit tests for calibrate.py (no network)
Run: python test_real_calib.py
"""
import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from calibrate import fx_realized_stats, equity_inflow_calib, export_value_elasticity


def test_fx_stats_recovers_vol():
    """Synthetic daily FX with known 5% annual vol, no drift."""
    n = 3 * 252
    np.random.seed(1)
    rets = np.random.normal(0.0, 0.05 / np.sqrt(252), n)
    px = 7.0 * np.exp(np.cumsum(rets))
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    df = pd.DataFrame({"date": dates, "usdcny": px})
    st = fx_realized_stats(df)
    assert "1y" in st and "3y" in st
    v = st["3y"]["annual_vol"]
    assert 0.035 < v < 0.068, f"vol {v} out of expected band around 0.05"
    # sampling error of annualized drift ~ vol/sqrt(years) ~ 2.9%
    assert abs(st["3y"]["annual_drift"]) < 0.07, "drift should be ~0"
    print("✓ test_fx_stats_recovers_vol  (vol=%.4f)" % v)


def test_export_elasticity_recovers_beta():
    """Synthetic monthly: d12 ln(exports) = 0.7 * d12 ln(usdcny) + e"""
    np.random.seed(2)
    months = pd.date_range("2010-01-31", periods=180, freq="ME")
    lx = np.cumsum(np.random.normal(0.01, 0.03, 180))      # fx path
    d12x = np.concatenate([np.zeros(12), lx[12:] - lx[:-12]])
    e = np.random.normal(0, 0.03, 180)
    ly = np.cumsum(np.random.normal(0.01, 0.05, 180))
    # impose relation on 12m diffs via level construction
    ly12 = ly
    for i in range(12, 180):
        target = ly12[i - 12] + 0.7 * (lx[i] - lx[i - 12]) + e[i]
        ly12[i] = target
    exp = pd.DataFrame({"month": months, "exports_usd": np.exp(ly12)})
    fx = pd.DataFrame({"date": pd.date_range("2010-01-01", periods=180, freq="ME"),
                       "usdcny": np.exp(lx)})
    fx["date"] = pd.to_datetime(fx["date"]).shift(0)
    out = export_value_elasticity(exp, fx)
    assert out.get("n", 0) >= 100
    b = out["beta_d12"]
    assert abs(b - 0.7) < 0.25, f"beta {b} not near 0.7"
    print("✓ test_export_elasticity_recovers_beta  (beta=%.3f t=%.2f)" % (b, out["t"]))


def test_equity_calib_sane():
    """Crafted northbound-like frame -> positive mean net / holdings / rate"""
    dates = []
    net_all, hold_all = [], []
    for y in range(2015, 2024):
        d = pd.Timestamp(year=y, month=12, day=31)
        dates.append(d)
        net_all.append(2000.0)          # 2000亿/year net
        hold_all.append(1.5e12)         # 1.5T RMB holdings
    nb = pd.DataFrame({"date": dates, "当日成交净买额": net_all,
                       "历史累计净买额": [np.nan] * 9,
                       "持股市值": hold_all})
    out = equity_inflow_calib(nb, usdcny=6.71)
    assert out["northbound_annual_net_T_rmb_mean"] == 0.2, out
    assert out["northbound_holdings_T_rmb_mean"] == 1.5, out
    assert 0.0 < out["historical_rate"] < 1.0
    assert out["full_scope_holdings_T_usd_est"] > 0.3
    print("✓ test_equity_calib_sane  (rate=%.4f)" % out["historical_rate"])


if __name__ == "__main__":
    print("=" * 46)
    print("  calibrate.py offline tests")
    print("=" * 46)
    test_fx_stats_recovers_vol()
    test_export_elasticity_recovers_beta()
    test_equity_calib_sane()
    print("=" * 46)
    print("  all passed")
    print("=" * 46)
