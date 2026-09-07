"""modules/evaluate - 统一评估编排。"""
from .core import UnifiedParams, ImportTools, load_policy_params
from .inflation import inflation_net
from .trade import trade_surplus_t, import_policy_delta
from .capital import capital_path, flight_pct_gdp
from .industry import deind_dual

def evaluate(appr_rate, p: UnifiedParams = None,
             tools: ImportTools = None, profit_shock_pct=None,
             oil_pct=0.30, us_tariff_shock=0.0, horizon=5):
    p = p or load_policy_params()
    tools = tools or ImportTools()
    inf = inflation_net(appr_rate, p, horizon, oil_pct)
    surp = trade_surplus_t(appr_rate, p, horizon)
    pol = import_policy_delta(tools, p)
    surp_pol = surp - pol["delta_t"] * horizon
    cap = capital_path(appr_rate, p, horizon, us_tariff_shock)
    dd = deind_dual(appr_rate, p, profit_shock_pct)
    flight_gdp = flight_pct_gdp(appr_rate, p)
    # 判定(双口径各自红线)
    ok_trade = surp_pol <= 0.3 + 5e-3
    ok_flight = flight_gdp <= p.flight_redline
    ok_deind = (dd["gdp_erode_pt"] <= p.deind_gdp_redline and
                dd["profit_shock_pct"] <= p.deind_profit_redline)
    ok_reserve = not cap["floor_hit"]
    ok_fiscal = pol["fiscal_gdp_pct"] <= p.fiscal_budget_gdp
    ok_inf = inf["absorbed_pct"] >= 25.0
    ok = {"inflation": ok_inf, "trade": ok_trade, "flight": ok_flight,
          "deind": ok_deind, "reserve": ok_reserve, "fiscal": ok_fiscal}
    npass = sum(ok.values())
    if npass == 6:
        verdict = "政策带内"
    elif ok_flight and ok_deind and ok_trade and ok_reserve:
        verdict = "边缘(微调工具或速度)"
    elif not ok_flight:
        verdict = "走资超限 - 加严封堵或降速"
    elif not ok_deind:
        verdict = "去工业化超限(双口径) - 需政策分摊"
    elif not ok_trade:
        verdict = "顺差收敛不足 - 提高速度或进口政策"
    else:
        verdict = "其它约束未满足(外储/财政/通胀)"
    return {"rate": round(appr_rate * 100, 2),
            "inflation": inf, "surplus_t": round(surp_pol, 3),
            "surplus_no_policy_t": round(surp, 3),
            "policy": pol, "capital": cap,
            "deind": dd, "flight_gdp_pct": round(flight_gdp, 1),
            "ok": ok, "verdict": verdict,
            "surplus_rebalancing_pct": round(
                max(0, 1 - surp_pol / 1.2) * 100, 1)}


# ============================================================
# 6. 平衡年 + 联合求解
# ============================================================
