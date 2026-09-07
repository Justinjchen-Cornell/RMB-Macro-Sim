# -*- coding: utf-8 -*-
"""
ppi_pass_through.py - H4: 中国 PPI/CPI 对油价与汇率的实测传导
=============================================================
OLS: ppi_yoy_t = a + sum_{k=0..L}( b_oil_k * d12ln(Brent)_{t-k} )
                   + sum(c_fx_k * d12ln(USDCNY)_{t-k} ) + e
long-run: 油价 +10% -> PPI ?pp ; 人民币贬值(USDCNY)+10% -> PPI ?pp
同口径跑 CPI(如可取), 与引擎假设(oil weight 0.10, EPT 0.35)对照。
Run: python tools/ppi_pass_through.py
"""
import os, sys, json
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from data_loader import _fred_key
import fredapi


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    r = y - X1 @ b
    dof = len(y) - X1.shape[1]
    se = np.sqrt(np.diag((r @ r / dof) * np.linalg.inv(X1.T @ X1)))
    r2 = 1 - (r @ r) / ((y - y.mean()) ** 2).sum()
    return b, se, r2


def run():
    import akshare as ak
    f = fredapi.Fred(_fred_key())
    oil = f.get_series("DCOILBRENTEU").dropna()
    oil_m = oil.resample("ME").last()
    fx = f.get_series("DEXCHUS").dropna()
    fx_m = fx.resample("ME").last()

    def yoy_pct(s):
        return s.pct_change(12) * 100.0

    dl_oil = np.log(oil_m).diff(12) * 100.0
    dl_fx = np.log(fx_m).diff(12) * 100.0

    def fetch_cn(name):
        try:
            df = getattr(ak, name)()
            s = pd.to_numeric(df["今值"], errors="coerce")
            s.index = pd.to_datetime(df["日期"], errors="coerce")
            return s.groupby(s.index.to_period("M")).last().dropna()
        except Exception as e:
            print("  skip", name, type(e).__name__)
            return pd.Series(dtype=float)

    ppi = fetch_cn("macro_china_ppi_yearly")
    cpi = fetch_cn("macro_china_cpi_yearly")

    out = {"note": "OLS, 12m 差分; 解释为油价/汇率长期(水平)弹性于同比PPI(pp)", "runs": {}}
    for name, yy in [("ppi", ppi), ("cpi", cpi)]:
        if yy.empty:
            continue
        base = pd.concat([yy.rename("y"), dl_oil.to_period('M').rename("oil"),
                          dl_fx.to_period('M').rename("fx")], axis=1).dropna()
        base = base.loc["2000":]
        # build lags
        cols = []
        for lag in range(6):
            cols.append(base["oil"].shift(lag).rename("oil_l%d" % lag))
        for lag in range(3):
            cols.append(base["fx"].shift(lag).rename("fx_l%d" % lag))
        d = pd.concat([base["y"]] + cols, axis=1).dropna()
        X = d[[c for c in d.columns if c != "y"]].values
        y = d["y"].values
        b, se, r2 = ols(X, y)
        lr_oil = float(np.sum(b[:6]))
        lr_fx = float(np.sum(b[6:9]))
        t_oil = lr_oil / float(np.sqrt(np.sum(se[:6] ** 2)))
        t_fx = lr_fx / float(np.sqrt(np.sum(se[6:9] ** 2)))
        res = {"n": int(len(d)), "r2": round(float(r2), 3),
               "oil_10pct_pp": round(lr_oil / 10.0 * 10.0, 3),  # per +10% oil
               "fx_10pct_pp": round(lr_fx, 3),                  # USDCNY+10%
               "t_oil": round(float(t_oil), 2),
               "t_fx": round(float(t_fx), 2),
               "sample": [str(d.index[0]), str(d.index[-1])]}
        out["runs"][name] = res
        print("%s: n=%d R2=%.2f | 油价+10%% -> %.2f pp(t=%.1f) | USDCNY+10%% -> %.2f pp(t=%.1f)"
              % (name, res["n"], res["r2"], res["oil_10pct_pp"], res["t_oil"],
                 res["fx_10pct_pp"], res["t_fx"]))
    json.dump(out, open(os.path.join(ROOT, "params", "ppi_pass_through.json"),
                        "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved params/ppi_pass_through.json")


if __name__ == "__main__":
    run()
