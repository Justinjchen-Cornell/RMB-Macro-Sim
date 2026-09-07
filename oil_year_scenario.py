# -*- coding: utf-8 -*-
"""
oil_year_scenario.py - 5-year oil window, year-by-year China drill-down
=======================================================================
Three Brent paths (year-end central), 2026-2030:
  A 温和去风险 : corridor holds, supply normalizes     96 90 88 86 85
  B 供给冲击   : Hormuz-scale disruption 2026          120 110 96 91 89
  C 速冻-修复  : 2026 dollar-freeze demand crash, V    70 76 83 86 88

Per path x year, for China (transparent anchors, USD/T$):
  energy bill   = 4.1 Gbbl/yr imports x price
  import CPI    = 0.10 x oil yoy (net of RMB offset, policy stance)
  surplus path  = rebalancing surplus (RMB stance) - energy bill delta
                 (- export demand hit in global shock years)
  RMB stance    = per year: 维稳/有序升值/加速升值 (%) - policy dial
  favor score   = 0-100 weighted: inflation 25 / trade gradualism 25 /
                  energy burden 20 / FX stability 20 / policy window 10

Prints tables + saves oil_year_scenario.json. Investment notes in doc.
Run: python oil_year_scenario.py
"""
import os
import json
import numpy as np

BIMPORTS = 4.1e9          # bbl/yr net crude imports
YEARS = [2026, 2027, 2028, 2029, 2030]
PATHS = {
    "A 温和去风险": {"brent": [96, 90, 88, 86, 85],
                  "rmb": [3.0, 4.0, 5.0, 5.0, 5.0],
                  "shock_years": []},
    "B 供给冲击":   {"brent": [120, 110, 96, 91, 89],
                  "rmb": [0.0, 3.0, 4.0, 5.0, 5.0],
                  "shock_years": [2026, 2027]},
    "C 速冻-修复":   {"brent": [70, 76, 83, 86, 88],
                  "rmb": [2.0, 2.0, 4.0, 5.0, 5.0],
                  "shock_years": [2026]},
}
BASE_BRENT = 90.0
W0 = {"inf": 25.0, "trade": 25.0, "bill": 20.0, "fx": 20.0, "pol": 10.0}


def _score_variants(parts, w0=None, step=10.0):
    """各权重 +/-step(其余按比例归一到100) -> 分数 min/max。"""
    w0 = w0 or dict(W0)
    scores = []
    for k in w0:
        for d in (step, -step):
            w = dict(w0)
            delta = d if w0[k] + d > 0 else 0.0
            w[k] = w0[k] + delta
            others = sum(v for kk, v in w.items() if kk != k)
            scale = (100.0 - w[k]) / others if others else 1.0
            for kk in w:
                if kk != k:
                    w[kk] *= scale
            val = (parts["inf"] * (w["inf"] / w0["inf"])
                   + parts["trade"] * (w["trade"] / w0["trade"])
                   + parts["bill"] * (w["bill"] / w0["bill"])
                   + parts["fx"] * (w["fx"] / w0["fx"])
                   + parts["pol"] * (w["pol"] / w0["pol"]))
            scores.append(val)
    return min(scores), max(scores)





def rebal_surplus_t(rate, t):
    """货物贸易顺差(不含能源价差): 与 policy_algo 同源近似。"""
    exp = 3.5 * (1.03 ** t) * (1 - 0.35 * rate / 100.0 * t)
    imp = 2.3 * (1.02 ** t) * (1 + 0.55 * rate / 100.0 * t)
    return exp - imp


def run():
    out = {}
    print("=" * 100)
    print("  5 年油价分年推演 - 中国视角 (原油净进口 4.1 Gbbl/年, 油价+30% 情景锚)")
    print("=" * 100)
    for pname, p in PATHS.items():
        rows = []
        prev_p = BASE_BRENT
        for i, yr in enumerate(YEARS):
            px = p["brent"][i]
            rate = p["rmb"][i]
            t = i + 1
            bill = px * BIMPORTS / 1e12
            bill0 = BASE_BRENT * BIMPORTS / 1e12
            oil_yoy = px / prev_p - 1.0
            infl_raw = 0.10 * oil_yoy * 100.0                       # CPI pp 输入
            infl_net = max(0.0, infl_raw - rate * 0.9)              # 升值对冲
            surp = rebal_surplus_t(rate, t) - (bill - bill0)
            if yr in p["shock_years"]:
                surp -= 0.10                                        # 全球需求衰减(近似)
            # favor score
            s_inf = max(0.0, 25.0 - 8.0 * infl_net)
            s_trade = 25.0 if 0.0 < surp < 1.0 else (
                12.0 if surp <= 0.0 else max(0.0, 25.0 - 10.0 * (surp - 1.0)))
            s_bill = max(0.0, 20.0 - 22.0 * (bill - bill0))
            s_fx = 20.0 if (rate >= 0 and yr not in p["shock_years"]) else (
                14.0 if rate >= 0 else 8.0)
            s_pol = 10.0 if px <= 78 else (6.0 if px >= 115 else 8.0)
            parts = {"inf": s_inf, "trade": s_trade, "bill": s_bill,
                     "fx": s_fx, "pol": s_pol}
            lo, hi = _score_variants(parts)
            score = round(s_inf + s_trade + s_bill + s_fx + s_pol, 1)
            rows.append({"year": yr, "brent": px, "rmb_rate": rate,
                         "bill_T": round(bill, 3),
                         "infl_raw_pt": round(infl_raw, 2),
                         "infl_net_pt": round(infl_net, 2),
                         "surplus_T": round(surp, 3),
                         "score": score,
                         "score_lo": round(lo, 1), "score_hi": round(hi, 1)})
            prev_p = px
        avg = round(float(np.mean([r["score"] for r in rows])), 1)
        win2 = round(float(np.mean([r["score"] for r in rows[:2]])), 1)
        best = max(rows, key=lambda r: r["score"])
        out[pname] = {"rows": rows, "avg_score": avg,
                      "first2y_score": win2, "best_year": best["year"],
                      "best_score": best["score"]}
        print("\n[%s]  avg=%.1f | 前2年均分=%.1f | 最优年=%d (%.1f)"
              % (pname, avg, win2, best["year"], best["score"]))
        print("  年 | Brent | 人民币立场% | 能源账单T$ | 输入通胀净pp | 顺差T$ | 有利度(±10pp带)")
        for r in rows:
            print("  %d | %5d | %4.1f%% | %5.2f | %5.2f | %5.2f | %5.1f(%4.1f-%4.1f)"
                  % (r["year"], r["brent"], r["rmb_rate"], r["bill_T"],
                     r["infl_net_pt"], r["surplus_T"], r["score"],
                     r["score_lo"], r["score_hi"]))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "oil_year_scenario.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("\n[saved] oil_year_scenario.json")


if __name__ == "__main__":
    run()
