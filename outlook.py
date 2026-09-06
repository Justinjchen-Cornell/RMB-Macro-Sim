# -*- coding: utf-8 -*-
"""
outlook.py - Yearly USD/CNY outlook: three envelopes (model x news)
==================================================================
Blends calibrated inertia drift (FRED) with a maintainable news/event table
(news_watch.yaml). For honesty, outputs THREE envelopes per year:
  low   : inertia + only depreciation-side events (weakest appreciation)
  base  : inertia + all events          (most likely)
  high  : inertia + only appreciation-side events (strongest appreciation)
Also carries event-exposure bands. Pure computation, no network.

  drift(t) = clamp(inertia + sum(active event impacts at t), 0, 0.12)
  median L_t = spot0 * exp(-cum(drift))
  band 25-75 ~ L_t * exp(+- 0.67*vol*sqrt(t))
  amount   : CNY value change per USD 10,000 vs prior year end
"""
import os
import numpy as np
import yaml

BASE = os.path.dirname(os.path.abspath(__file__))
INERTIA = 0.027          # realized 3y drift (appreciation)
POLICY = 0.06            # policy anchor (unused in math, kept for reference)
VOL = 0.0284
YEARS = 5
CLAMP = 0.12


def load_news(path=None):
    if path is None:
        path = os.path.join(BASE, "news_watch.yaml")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    return d.get("events", [])


def event_drift(year_idx, ev):
    s = int(ev.get("start_year", 1))
    e = int(ev.get("end_year", YEARS))
    imp = float(ev.get("impact", 0.0))
    if year_idx < s:
        return 0.0
    if year_idx <= e:
        return imp
    return imp * max(0.0, 1.0 - (year_idx - e))


def drift_years(events, inertia=INERTIA):
    dr = []
    for t in range(1, YEARS + 1):
        base = inertia + sum(event_drift(t, ev) for ev in events)
        dr.append(max(0.0, min(CLAMP, base)))
    return dr


def _path(drifts, spot0):
    levels = [spot0]
    for t in range(1, YEARS + 1):
        levels.append(spot0 * np.exp(-sum(drifts[:t])))
    return [float(v) for v in levels]


def compute(spot0=6.7108, vol=VOL, events=None, inertia=INERTIA):
    if events is None:
        events = load_news()
    pos = [ev for ev in events if float(ev.get("impact", 0)) > 0]
    neg = [ev for ev in events if float(ev.get("impact", 0)) < 0]

    dr_low = drift_years(neg, inertia)     # 仅贬值类事件 -> 最弱升值
    dr_base = drift_years(events, inertia)  # 全部事件 -> 最可能
    dr_high = drift_years(pos, inertia)     # 仅升值类事件 -> 最强升值

    L_low = _path(dr_low, spot0)
    L_base = _path(dr_base, spot0)
    L_high = _path(dr_high, spot0)

    rows = []
    cal = 2026
    for t in range(1, YEARS + 1):
        b_now, b_prev = L_base[t], L_base[t - 1]
        chg_pct = (b_prev - b_now) / b_prev * 100.0
        usd10k = 10000.0 * (b_prev - b_now)
        band = b_now * np.exp(0.67 * vol * np.sqrt(t))
        band_lo = 2 * b_now - band
        env_lo = min(L_low[t], L_base[t], L_high[t])
        env_hi = max(L_low[t], L_base[t], L_high[t])
        pace = ("升值加速" if dr_base[t - 1] >= 0.05 else
                ("升值平稳" if dr_base[t - 1] >= 0.02 else
                 ("升值趋缓" if dr_base[t - 1] >= 0.005 else "双向波动/贬值风险")))
        rows.append({
            "year": cal + t - 1,
            "drift": round(dr_base[t - 1] * 100, 2),
            "level": round(b_now, 4),            # 最可能
            "level_low": round(L_low[t], 4),     # 包络下沿(最弱升值)
            "level_high": round(L_high[t], 4),   # 包络上沿(最强升值)
            "env_lo": round(env_lo, 4),
            "env_hi": round(env_hi, 4),
            "chg_pct": round(chg_pct, 2),
            "usd10k_cny": round(usd10k, 0),
            "band_lo": round(min(band_lo, b_now), 4),
            "band_hi": round(max(band, b_now), 4),
            "pace": pace})

    n_pos = sum(float(ev.get("impact", 0)) for ev in pos)
    n_neg = sum(float(ev.get("impact", 0)) for ev in neg)
    return {"rows": rows, "events": events,
            "envelopes": {"low": "inertia + 贬值类事件(最弱升值)",
                          "base": "inertia + 全部事件(最可能)",
                          "high": "inertia + 升值类事件(最强升值)"},
            "event_impact_total": {"pos_pp": round(n_pos * 100, 2),
                                   "neg_pp": round(n_neg * 100, 2)},
            "note": "包络上/下沿用于展示新闻事件的主观不确定性; "
                    "区间列为近似 25-75%。事件表: news_watch.yaml 可自行增删。"}
