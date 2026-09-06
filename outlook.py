# -*- coding: utf-8 -*-
"""
outlook.py - Yearly USD/CNY outlook: model x news-event weighting
=================================================================
Predicts, for each of the next 5 calendar years, the most-likely RMB
appreciation/depreciation magnitude and level, blending:
  (a) model anchor drifts - policy scenario (config 6%) and realized
      inertia (FRED drift, default 2.7%)
  (b) structured news/events from news_watch.yaml, each with direction,
      impact, and an active window with linear decay.

Pure computation, no network. Called by export_dashboard.py to add the
"Annual outlook" panel payload.

Method notes (documented, approximate):
  drift_y(t) = clamp(inertia + sum(event_impacts active at t), 0, 0.12)
  w_year    = clamp((drift_y(t)-inertia)/(policy-inertia),0,1)  (weight vs policy)
  median L_t = spot0 * exp(-sum(drift_y(1..t)))
  band 25-75 ~ L_t * exp(+- 0.67 * vol * sqrt(t))
  amount: per USD 10k, CNY value change vs prior year end.
"""
import os
import numpy as np
import yaml

BASE = os.path.dirname(os.path.abspath(__file__))
INERTIA = 0.027          # realized 3y drift (appreciation, + = CNY strong)
POLICY = 0.06            # policy scenario drift
VOL = 0.0284             # realized vol (3y)
YEARS = 5


def load_news(path=None):
    if path is None:
        path = os.path.join(BASE, "news_watch.yaml")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    return d.get("events", [])


def event_drift(year_idx, ev):
    """Active years window with linear fade-out after 'end_year'."""
    s = int(ev.get("start_year", 1))
    e = int(ev.get("end_year", YEARS))
    imp = float(ev.get("impact", 0.0))     # + = pro-appreciation drift
    if year_idx < s:
        return 0.0
    if year_idx <= e:
        return imp
    # linear decay over 1 extra year
    return imp * max(0.0, 1.0 - (year_idx - e))


def drift_years(events, inertia=INERTIA, policy=POLICY):
    dr = []
    for t in range(1, YEARS + 1):
        base = inertia + sum(event_drift(t, ev) for ev in events)
        dr.append(max(0.0, min(0.12, base)))
    return dr


def compute(spot0=6.7108, vol=VOL, events=None, inertia=INERTIA):
    if events is None:
        events = load_news()
    dr = drift_years(events, inertia=inertia)
    levels = [spot0]
    for t in range(1, YEARS + 1):
        levels.append(spot0 * np.exp(-sum(dr[:t])))
    rows = []
    cal = 2026
    for t in range(1, YEARS + 1):
        l_now = float(levels[t])
        l_prev = float(levels[t - 1])
        chg_pct = (l_prev - l_now) / l_prev * 100.0        # + = RMB appreciation
        usd10k = 10000.0 * (l_prev - l_now)                # CNY value change
        band = l_now * np.exp(0.67 * vol * np.sqrt(t))
        band_low = 2 * l_now - band                        # symmetric approx
        pace = "升值加速" if dr[t - 1] >= 0.05 else (
            "升值平稳" if dr[t - 1] >= 0.02 else (
            "升值趋缓" if dr[t - 1] >= 0.005 else "双向波动/贬值风险"))
        rows.append({
            "year": cal + t - 1, "drift": round(dr[t - 1] * 100, 2),
            "level": round(l_now, 4), "chg_pct": round(chg_pct, 2),
            "usd10k_cny": round(usd10k, 0),
            "band_lo": round(min(band_low, l_now), 4),
            "band_hi": round(max(band, l_now), 4),
            "pace": pace})
    active = [ev for ev in events if ev.get("impact", 0) != 0]
    return {"rows": rows, "events": active,
            "note": "最可能幅度 = 现实惯性 + 新闻事件评分(线性衰减); 区间为近似 25-75%。"
                    "新闻表见 news_watch.yaml, 可自行增删。"}
