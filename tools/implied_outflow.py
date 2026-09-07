# -*- coding: utf-8 -*-
"""
implied_outflow.py - M4 主锚: 官方月度拼"走资残差" (2015..)
============================================================
resid = -d(外储) + 货物顺差 + FDI + 估值效应(美债/黄金/美元折算, 用 H1 分配)
来源: akshare 外储/黄金储备(月) · 贸易顺差(月) · FDI(月, 2023-07 后缺失补记)
      FRED DGS10/汇率 + COMEX GC(2016+) 做估值腿
输出: params/implied_outflow.csv + 年度汇总 + 危机锚(2015-16)统计
"""
import os
import sys
import json
import datetime as dt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.makedirs(os.path.join(ROOT, "params"), exist_ok=True)


def month_end(df, col):
    s = pd.to_numeric(df[col], errors="coerce")
    s.index = pd.to_datetime(df["日期"] if "日期" in df.columns else df["统计时间"],
                             format="mixed", errors="coerce")
    s = s.groupby(s.index.to_period("M")).last().sort_index()
    return s / 100.0 if col == "国家外汇储备" else s   # 亿美元 -> 百亿=0.1T? no: /100 -> 百亿美元? handle below


def main():
    import akshare as ak
    from data_loader import _fred_key
    import fredapi

    # 1) reserves monthly (亿美元 -> T$)
    res = ak.macro_china_foreign_exchange_gold()
    r = pd.to_numeric(res["国家外汇储备"], errors="coerce")
    r.index = pd.to_datetime(res["统计时间"], format="%Y.%m")
    r = r.groupby(r.index.to_period("M")).last().sort_index()
    r_t = r / 10000.0                      # 亿美元 -> T$

    # 2) trade balance monthly (亿美元 -> T$)
    tb_df = ak.macro_china_trade_balance()
    tb = pd.to_numeric(tb_df["今值"], errors="coerce")
    tb.index = pd.to_datetime(tb_df["日期"], errors="coerce")
    tb = tb.groupby(tb.index.to_period("M")).last().sort_index() / 10000.0

    # 3) FDI monthly (万元 -> T$)
    try:
        fdi_df = ak.macro_china_fdi()
        fdi = pd.to_numeric(fdi_df["当月"], errors="coerce")
        fdi.index = pd.to_datetime(fdi_df["月份"], errors="coerce")
        fdi = fdi.groupby(fdi.index.to_period("M")).last().sort_index()
        fdi_t = fdi * 1e4 / 7.1e12         # 万元 -> 元 -> T$ (CNY7.1)
    except Exception:
        fdi_t = pd.Series(dtype=float)

    # 4) valuation monthly (T$): bond+gold+fx legs on prev-month reserves
    f = fredapi.Fred(_fred_key())
    dgs = f.get_series("DGS10").dropna()
    dgs_m = dgs.resample("ME").last()
    dy = dgs_m.diff()
    fx = f.get_series("DEXCHUS").dropna()
    fx_m = fx.resample("ME").last()
    dfx = fx_m.pct_change()
    gold = None
    try:
        gc = ak.futures_foreign_hist(symbol="GC")
        gc["date"] = pd.to_datetime(gc["date"])
        gold = gc.set_index("date")["close"].astype(float).resample("ME").last()
        dgold = gold.pct_change()
    except Exception:
        dgold = pd.Series(dtype=float)

    idx = r_t.index
    dur = 6.0
    vals = []
    prev_r = r_t.iloc[0]
    for m in idx[1:]:
        dyv = float(dy.reindex(m.asfreq('D').tz_localize(None)
                                if False else m.to_timestamp()).iloc[0]) if False else None
        # month anchor by period -> timestamp end
        ts = m.to_timestamp(how="end")
        dym = dy.asof(ts)
        dfxm = dfx.asof(ts)
        dgm = dgold.asof(ts) if len(dgold) else np.nan
        val = 0.0
        if dym == dym:
            val += -dur * dym * 0.35 * prev_r
        if dgm == dgm:
            val += dgm * 0.15 * prev_r
        if dfxm == dfxm:
            val += -dfxm * 0.25 * prev_r
        vals.append(val)
        prev_r = prev_r + vals[-1]
    val_s = pd.Series(vals, index=idx[1:])

    # assemble residual
    dR = r_t.diff()
    parts = pd.DataFrame({
        "dR_t": dR,
        "tb_t": tb.reindex(idx),
        "fdi_t": fdi_t.reindex(idx),
        "val_t": val_s.reindex(idx),
    })
    parts["resid_t"] = -parts["dR_t"] + parts["tb_t"] + parts["fdi_t"].fillna(0.0) \
        + parts["val_t"].fillna(0.0)
    parts = parts.loc["2015":]
    parts = parts.dropna(subset=["dR_t"])
    parts.to_csv(os.path.join(ROOT, "params", "implied_outflow.csv"),
                 encoding="utf-8-sig")

    yearly = parts["resid_t"].resample("Y").sum()
    cy = yearly.loc["2015":"2016"]
    crisis_annual = float(cy.mean()) if len(cy) else np.nan
    gdp = 19.0
    crisis_pct_gdp = crisis_annual / gdp * 100.0 if crisis_annual == crisis_annual else np.nan
    monthly_p90 = float(np.abs(parts["resid_t"].loc["2015":"2016"]).quantile(0.90))
    monthly_all_p90 = float(np.abs(parts["resid_t"]).quantile(0.90))

    print("implied outflow (T$/年, 正=流出? 负=流入):")
    print(yearly.round(3).to_string())
    print()
    print("危机锚(2015-16): 年均残差=%.3f T$ -> %.2f%%GDP | 月|resid| p90=%.3f T$"
          % (crisis_annual, crisis_pct_gdp, monthly_p90))
    print("全样本月|resid| p90=%.3f T$" % monthly_all_p90)
    meta = {"crisis_annual_t": round(crisis_annual, 3),
            "crisis_pct_gdp": round(crisis_pct_gdp, 2),
            "anchor_note": "残差 = -d外储+货物顺差+FDI+估值; 数据覆盖至各源最新",
            "sources": ["akshare 外储/黄金储备(月)", "akshare 贸易顺差(月)",
                        "akshare FDI(月, 2023-07 后缺失)", "FRED DGS10/DEXCHUS",
                        "akshare GC(2016+)"]}
    json.dump(meta, open(os.path.join(ROOT, "params", "implied_outflow_meta.json"),
                         "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
