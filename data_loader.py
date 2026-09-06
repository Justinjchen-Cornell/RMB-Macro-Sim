# -*- coding: utf-8 -*-
"""
data_loader.py - Real data access layer for macro_sim (2026-09)
===============================================================
Sources:
  1. FRED      : DEXCHUS (USD/CNY daily, 1981+), China exports (monthly)
  2. Tencent   : qt.gtimg.cn realtime spot / web.ifzq.gtimg.cn daily kline
                 (whUSDCNY FX + sh/sz ETF proxies for industry calibration)
  3. akshare   : northbound (Beixiang) capital history (Eastmoney push2his)

Usage:
    python data_loader.py            # fetch-if-missing
    python data_loader.py --refresh  # force re-fetch

All series cached under data/raw/*.csv; freshness tracked in data/meta.json.
ASCII-only source. No external deps beyond requests/pandas/akshare.
"""

import os
import re
import sys
import json
import datetime as dt
import requests
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "data", "raw")
META = os.path.join(BASE, "data", "meta.json")
ENV_PATH = os.path.join(BASE, "..", "..", "..", "..", ".env")  # repo root .env
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

os.makedirs(RAW, exist_ok=True)


def _fred_key():
    # 1) 环境变量优先 (GitHub Actions / 独立克隆场景)
    env = os.environ.get("FRED_API_KEY")
    if env:
        return env.strip()
    # 2) 向上搜索 .env (仓库根 / 上级目录), 最多 6 层
    cur = os.path.dirname(os.path.abspath(BASE))
    for _ in range(6):
        cand = os.path.join(cur, ".env")
        if os.path.exists(cand):
            for line in open(cand, encoding="utf-8", errors="ignore"):
                s = line.strip()
                if s.upper().startswith("FRED"):
                    v = s.split("=", 1)[1].strip()
                    if v:
                        return v
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    raise RuntimeError(
        "FRED_API_KEY missing. Set environment variable FRED_API_KEY or place "
        "FRED_API_KEY=... in a .env file under the repo root.")


# ── FRED ─────────────────────────────────────────────────
def fetch_fred(series_id: str) -> pd.Series:
    import fredapi
    fred = fredapi.Fred(_fred_key())
    return fred.get_series(series_id)


# ── Tencent realtime spot ────────────────────────────────
def fetch_tencent_spot(codes) -> dict:
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    r = requests.get(url, headers=UA, timeout=10)
    r.encoding = "gbk"
    out = {}
    for line in r.text.strip().split("\n"):
        m = re.match(r'v_([\w]+)="([^"]*)"', line.strip())
        if not m:
            continue
        code, payload = m.group(1), m.group(2)
        v = payload.split("~")
        if len(v) > 3 and v[1]:
            try:
                out[code] = {"name": v[1], "price": float(v[3])}
            except ValueError:
                pass
    return out


# ── Tencent daily kline (paginated) ──────────────────────
def fetch_tencent_kline(symbol: str, start: str = "2015-01-01",
                        end: str = None, page: int = 600) -> pd.DataFrame:
    if end is None:
        end = dt.date.today().isoformat()
    rows = []
    cur_end = end
    guard = 0
    while guard < 80:                     # safety: max 80 pages
        guard += 1
        url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
               "?param=%s,day,%s,%s,%d,qfq" % (symbol, start, cur_end, page))
        j = requests.get(url, headers=UA, timeout=15).json()
        node = j["data"].get(symbol, {})
        k = node.get("qfqday") or node.get("day") or []
        if not k:
            break
        rows.extend(k)
        first = k[0][0]
        if first <= start:
            break
        cur_end = (dt.date.fromisoformat(first) - dt.timedelta(days=1)).isoformat()
    if not rows:
        raise RuntimeError("no kline rows for %s" % symbol)
    # rows may carry 6 or 7 fields (dividend marker); take first 6 robustly
    rows6 = [r[:6] for r in rows]
    df = pd.DataFrame(rows6, columns=["date", "open", "close", "high", "low", "vol"])
    df = df[["date", "open", "high", "low", "close", "vol"]].copy()
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates("date")
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ── akshare northbound ───────────────────────────────────
def fetch_northbound() -> pd.DataFrame:
    import akshare as ak
    df = ak.stock_hsgt_hist_em(symbol="北向资金")
    df.columns = [str(c).strip() for c in df.columns]
    df["date"] = pd.to_datetime(df["日期"])
    return df.sort_values("date").reset_index(drop=True)


# ── cache helpers ────────────────────────────────────────
def _save(df: pd.DataFrame, name: str):
    df.to_csv(os.path.join(RAW, name + ".csv"), index=False, encoding="utf-8-sig")


def _load(name: str) -> pd.DataFrame:
    p = os.path.join(RAW, name + ".csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p)


def _meta():
    if os.path.exists(META):
        with open(META, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _touch(name: str):
    m = _meta()
    m[name] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(META, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)


# ── master fetcher ───────────────────────────────────────
def ensure_data(refresh: bool = False) -> dict:
    out = {}

    # 1) FRED USD/CNY daily
    if refresh or _load("fred_dexchus") is None:
        s = fetch_fred("DEXCHUS")
        df = pd.DataFrame({"date": s.index, "usdcny": s.values}).dropna()
        _save(df, "fred_dexchus"); _touch("fred_dexchus")
    out["fx_fred"] = _load("fred_dexchus")

    # 2) FRED China exports (monthly, USD)
    if refresh or _load("fred_exports_cn") is None:
        s = fetch_fred("XTEXVA01CNM667S")
        df = pd.DataFrame({"month": s.index, "exports_usd": s.values}).dropna()
        _save(df, "fred_exports_cn"); _touch("fred_exports_cn")
    out["exports_cn"] = _load("fred_exports_cn")

    # 3) Tencent USD/CNY daily kline
    if refresh or _load("tx_usdcny") is None:
        df = fetch_tencent_kline("whUSDCNY", start="2018-01-01")
        df.rename(columns={"close": "usdcny"}, inplace=True)
        _save(df[["date", "usdcny"]], "tx_usdcny"); _touch("tx_usdcny")
    out["fx_tencent"] = _load("tx_usdcny")

    # 4) Tencent realtime spot (always fresh)
    spot = fetch_tencent_spot(["whUSDCNY", "sh510300"])
    out["spot"] = spot

    # 5) Northbound capital
    if refresh or _load("northbound") is None:
        df = fetch_northbound()
        _save(df, "northbound"); _touch("northbound")
    out["northbound"] = _load("northbound")

    return out


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    res = ensure_data(refresh=refresh)
    print("series ready:", list(res.keys()))
    for k, v in res.items():
        if hasattr(v, "shape"):
            print("  %-14s rows=%d  (cached)" % (k, len(v)))
        else:
            print("  %-14s %s" % (k, v))
