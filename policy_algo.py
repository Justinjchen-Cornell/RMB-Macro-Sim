# -*- coding: utf-8 -*-
"""
policy_algo.py - Policy algorithm layer (卢氏三原则量化)
========================================================
RMB appreciation policy objectives, made computable:

  P1  消化输入性通胀    : 与油价逆向同步 —— 升值应对冲掉一部分进口油价
                         带来的输入性通胀 (CNY 进口成本 = 油价 x 汇率)
  P2  贸易项下基本平衡  : 1.2 万亿美元顺差"没有必要" -> 收敛到接近平衡
                         (目标: 5 年内压到 <=0.3 T$, 逐步而非急刹车)
  P3  封堵升值后走资    : 严厉管控资本外逃, 避免广场协议式去工业化

Four dials per appreciation rate (0..15%/yr, 5y horizon):
  inflation_absorbed_pt  : 输入性 CPI 中被升值对冲掉的百分点(油价情景)
  surplus_end_t          : 5 年末货物贸易顺差 (T$, 目标 <=0.3)
  rebalancing_pct        : 顺差收敛比例 (1 - S_end/1.2)
  flight_risk            : 0-100 走资风险指数 (升值幅度 x 资本开放度)
  deind_pressure_pct     : 低端制造 5y 累计利润冲击 (去工业化压力表)

Outputs per rate + bisection-solved "政策建议带" and a one-line verdict.
Run:  python policy_algo.py          (standalone deep-dive table)
"""
import numpy as np

# ---- structural anchors (T$/yr, 现实量级近似, 文档注明) ----
EXPORTS0 = 3.5        # 年出口额 (USD)
IMPORTS0 = 2.3        # 年进口额 (USD) -> 顺差 1.2T
SURPLUS0 = EXPORTS0 - IMPORTS0
G_EXP = 0.03          # 出口外需增长
G_IMP = 0.02          # 进口内需增长
LAM_E = 0.35          # 出口 USD 值对累计升值的弹性 (部分人民币定价粘性)
LAM_M = 0.55          # 进口 USD 值对累计升值的弹性 (本币购买力)
SURPLUS_TARGET = 0.30 # 5 年目标上限 (T$)
OIL_CPI_W = 0.10      # 油价对 CPI 的传导权重 (油价+30% -> ~+3pp 输入压力上限)
OIL_SCEN = 30.0       # 情景: 油价 +30%
APP_OFFSET = 0.90     # 升值对进口油价成本的对冲传导率 (0.9 = 升值 90% 传导)
OPENNESS = 0.40       # 资本账户开放度 0-1 (假设值, 可下调表示加强封堵)
FLIGHT_K = 7.0        # 走资压力系数 (标定: 10%/年 x 开放0.4 -> ~56/100 高风险)


def inflation_absorption(rate_pct, oil_scen_pct=OIL_SCEN):
    """升值对冲输入性通胀: 油价输入压力 vs 升值抵消的百分比。"""
    oil_cpi_pressure = OIL_CPI_W * (oil_scen_pct / 100.0)      # 未对冲输入压力 (CPI pp)
    offset = min(rate_pct / 100.0 * APP_OFFSET, oil_cpi_pressure)
    net = oil_cpi_pressure - offset
    absorbed = offset / oil_cpi_pressure * 100.0 if oil_cpi_pressure > 0 else 0.0
    return {"oil_cpi_pressure_pt": round(oil_cpi_pressure, 3),
            "offset_pt": round(offset, 3),
            "net_pt": round(net, 3),
            "absorbed_pct": round(absorbed, 1)}


def rebalance(rate_pct, years=5):
    """货物贸易顺差路径: 升值+需求 vs 目标。"""
    e = EXPORTS0
    m = IMPORTS0
    path = []
    for t in range(1, years + 1):
        cum = rate_pct / 100.0 * t
        e = EXPORTS0 * (1 + G_EXP) ** t * (1 - LAM_E * cum)
        m = IMPORTS0 * (1 + G_IMP) ** t * (1 + LAM_M * cum)
        path.append(e - m)
    end = path[-1]
    bal_year = None
    for t, s in enumerate(path, start=1):
        if s <= SURPLUS_TARGET:
            bal_year = t
            break
    return {"path_t": [round(x, 3) for x in path],
            "end_t": round(end, 3),
            "rebalancing_pct": round(max(0, 1 - end / SURPLUS0) * 100, 1),
            "balanced_year": bal_year,
            "years_to_target": bal_year if bal_year else None}


def flight_risk(rate_pct, openness=OPENNESS):
    """走资风险指数 0-100。升值越陡 + 越开放 -> 越高; 封堵 = 调低 openness。"""
    if rate_pct <= 0:
        return 0.0
    base = FLIGHT_K * rate_pct * (openness / 0.5)
    return round(min(100.0, base), 0)


def evaluate(rate_pct, lowend_shock_pct, oil_scen_pct=OIL_SCEN, openness=OPENNESS):
    inf = inflation_absorption(rate_pct, oil_scen_pct)
    reb = rebalance(rate_pct)
    fr = flight_risk(rate_pct, openness)
    deind = abs(lowend_shock_pct) if lowend_shock_pct < 0 else 0.0
    # 政策带判断 (三原则合成)
    ok_inf = inf["absorbed_pct"] >= 25.0          # 至少对冲 1/4 输入压力
    ok_trade = reb["end_t"] <= SURPLUS_TARGET
    ok_flight = fr <= 55
    ok_deind = deind <= 35.0                       # 低端制造冲击上限(避免去工业化红线)
    dials = {"inflation_absorbed_pct": inf["absorbed_pct"],
             "surplus_end_t": reb["end_t"],
             "rebalancing_pct": reb["rebalancing_pct"],
             "balanced_year": reb["balanced_year"],
             "flight_risk": fr,
             "deind_pressure_pct": round(deind, 1)}
    passes = sum([ok_inf, ok_trade, ok_flight, ok_deind])
    if passes == 4:
        verdict = "政策带内"
    elif passes >= 3 and ok_trade and ok_flight:
        verdict = "边缘(微调开放度或节奏)"
    elif not ok_flight:
        verdict = "走资风险超限 - 需加严封堵(降开放度)或降速"
    elif not ok_trade:
        verdict = "顺差收敛不足 - 需更高升值或需求端配合"
    elif not ok_deind:
        verdict = "去工业化压力超限 - 需产业政策缓冲"
    else:
        verdict = "通胀对冲不足 - 升值速度偏低"
    return {"rate_pct": rate_pct, "dials": dials,
            "ok": {"inflation": ok_inf, "trade": ok_trade,
                   "flight": ok_flight, "deind": ok_deind},
            "verdict": verdict}


def policy_band(lowend_fn, step=0.5):
    """低端冲击随升值速度 -> 逐档评估, 返回政策带与档位明细。"""
    rows = []
    for r in np.arange(0.0, 15.001, step):
        low = lowend_fn(float(r))
        ev = evaluate(float(r), low)
        rows.append(ev)
    good = [r["rate_pct"] for r in rows if r["ok"]["trade"] and r["ok"]["flight"]]
    inf_ok = [r["rate_pct"] for r in rows if r["ok"]["inflation"]]
    deind_ok = [r["rate_pct"] for r in rows if r["ok"]["deind"]]
    full = [r["rate_pct"] for r in rows if all(r["ok"].values())]
    return {"rows": rows,
            "trade_ok": (min(good), max(good)) if good else None,
            "inflation_ok": (min(inf_ok), max(inf_ok)) if inf_ok else None,
            "deind_ok": (min(deind_ok), max(deind_ok)) if deind_ok else None,
            "full_band": (min(full), max(full)) if full else None}


def solve_trade_rate(target=SURPLUS_TARGET, years=5, lo=0.0, hi=15.0):
    """求 5 年把顺差压到 target 所需的最小年化升值速度 (bisection)。"""
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if rebalance(mid, years)["end_t"] > target:
            lo = mid
        else:
            hi = mid
    return round(hi, 2)


def main():
    from model import MacroParams, ScenarioEngine, load_project_config
    from dataclasses import replace
    mp, cc = load_project_config()

    def lowend(rate):
        p = replace(mp, cny_annual_apprec=rate / 100.0,
                    n_simulations=300, seed=7)
        r = ScenarioEngine(p, capital_cfg=cc).run()
        return float(r["industry_profit"]["export_lowend"].iloc[-1]) * 100

    print("=" * 92)
    print("  政策算法深潜: 卢氏三原则 -> 四个仪表 (5 年窗口, 油价+30% 情景)")
    print("=" * 92)
    print("  %-5s %-10s %-9s %-8s %-7s %-8s %-22s"
          % ("速%", "通胀对冲%", "顺差末T$", "收敛%", "平衡年", "走资", "去工业% | 判定"))
    for rate in np.arange(0.0, 12.01, 1.0):
        ev = evaluate(float(rate), lowend(float(rate)))
        d = ev["dials"]
        print("  %-5.0f %-10.1f %-9.2f %-8.1f %-7s %-8.0f %-22s | %s"
              % (rate, d["inflation_absorbed_pct"], d["surplus_end_t"],
                 d["rebalancing_pct"], d["balanced_year"] or "-",
                 d["flight_risk"], "%.1f" % d["deind_pressure_pct"],
                 ev["verdict"]))
    r6 = solve_trade_rate()
    print("\n  基准速 6%%/年: 5 年顺差 %.2f T$ -> 完全平衡(<=0.3T)需 %.1f%%/年, 或接受 8-10 年渐近"
          % (rebalance(6.0)["end_t"], r6))
    print("  封堵演示: 开放度 0.40 -> 0.25 时, 10%%/年 档走资风险 %d -> %d"
          % (flight_risk(10, 0.40), flight_risk(10, 0.25)))
    print("  注: 走资风险仅指示性; 贸易弹性/开放度为假设, 详见算法修订文档。")

if __name__ == "__main__":
    main()
