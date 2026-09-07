# -*- coding: utf-8 -*-
"""
policy_engine.py - Unified Lu-three-principles policy system (V2 x V3 x V4)
===========================================================================
单一口径:本文件是唯一 canonical 引擎。历史资产:
  - V2a 仓库 policy_algo.py     (利润口径红线的政策带 + dashboard)
  - V2b 外部 policy_algo_v2.py  (GDP口径: EPT 0.35 滞后传导, 资本账户分层)
  - V3  外部 import_demand_policy.py (四类进口政策工具 + 联合优化)
  - V4  63KB 文档路线图(外储-顺差辩证, S型资本流动, 三元目标)
本引擎:
  1) 双口径去工业化: gdp_erode_pt(GDP增加值侵蚀%, V2b口径)
                   + profit_shock_pct(行业利润冲击%, V2a口径, 可注入 repo 引擎实测)
  2) 分层通胀:      油价→CPI 5期滞后(ept 0.35) - 升值对冲
  3) 资本账户:      S型期望收益流 + 走资 + 报复冲击 -> 外储路径(3.2T 底线)
  4) 四政策工具:    关税/战略采购(年增量封顶)/准入/内需, 财政与幼稚产业红线
  5) 联合优化:      目标 = 贸易平衡 x 外储安全 x 走资/去工业(双口径) x 财政成本
  6) 输出契约统一为 dict, 供 CLI / dashboard / 文档共用。
Run: python policy_engine.py
"""
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import math


# ============================================================
# 1. 统一参数 (单一口径; 全部可调且注明依据)
# ============================================================
@dataclass
class UnifiedParams:
    # 贸易
    lam_e: float = 0.35
    lam_m: float = 0.45
    lam_svc: float = 0.25
    # 汇率传递: 5期滞后累计 ~0.14 (油价) ; 升值对冲 EPT
    oil_lags: List[float] = field(default_factory=lambda: [0.02, 0.03, 0.04, 0.03, 0.02])
    ept: float = 0.35
    # 资本账户分层
    openness: float = 0.40
    fdi_share: float = 0.30
    portfolio_share: float = 0.35
    nee_share: float = 0.20
    hot_share: float = 0.15
    rmb_intl: float = 0.15
    us_retaliation_sensitivity: float = 0.5
    # 红线 (双口径并立)
    flight_redline: float = 35.0       # 走资红线 (% GDP, V2b口径)
    deind_gdp_redline: float = 35.0    # 去工业化红线 GDP 侵蚀 (% GDP)
    deind_profit_redline: float = 35.0 # 去工业化红线 利润冲击 (%, V2a口径)
    cca_redline: float = 55.0
    # 宏观基线
    gdp_usd_t: float = 19.0
    exports_t: float = 3.5
    imports_t: float = 2.3
    svc_export_t: float = 0.4
    svc_import_t: float = 0.6
    reserves_t: float = 3.2
    reserves_floor_t: float = 2.5
    fiscal_budget_gdp: float = 3.0     # 财政赤字容忍 (% GDP)
    # 油价
    oil_base: float = 90.0
    oil_shock: float = 1.30            # +30% 情景


def oil_cpi_raw(oil_price_series, p: UnifiedParams):
    """油价→CPI 滞后分布输入压力(每期). 输入为价格水平列表。"""
    out = []
    prev = p.oil_base
    acc = 0.0
    for i, px in enumerate(oil_price_series):
        yoy = px / prev - 1.0
        for lag, w in enumerate(p.oil_lags):
            t = i + lag
            while len(out) <= t:
                out.append(0.0)
            out[t] += w * yoy
        prev = px
    return [x * 100.0 for x in out[:len(oil_price_series)]]  # CPI pp


def inflation_net(appr_rate, p: UnifiedParams, horizon=5, oil_pct=0.30):
    """分层: 油价输入压力(5期累计 ~0.14*oil) vs 升值对冲(ept*appr累积)。"""
    raw = sum(p.oil_lags) * oil_pct * 100.0
    offset = min(raw, p.ept * appr_rate * 100.0 * horizon)
    return {"raw_pp": round(raw, 2), "offset_pp": round(offset, 2),
            "net_pp": round(max(0.0, raw - offset), 2),
            "absorbed_pct": round(min(100.0, offset / raw * 100.0), 1)}


def trade_surplus_t(appr_rate, p: UnifiedParams, t: int,
                    policy_delta=0.0, demand_hit=0.0):
    """货物+服务合并顺差(T$). appr_rate 为小数(0.06=6%). demand_hit: 需求冲击。"""
    cum = appr_rate * t
    g_exp = p.exports_t * (1.03 ** t) * (1 - p.lam_e * cum)
    g_imp = p.imports_t * (1.02 ** t) * (1 + p.lam_m * cum)
    s_exp = p.svc_export_t * (1.03 ** t) * (1 - p.lam_svc * cum)
    s_imp = p.svc_import_t * (1.02 ** t) * (1 + p.lam_svc * cum)
    base = (g_exp - g_imp) + (s_exp - s_imp)
    return base - policy_delta * t + demand_hit * t


# ============================================================
# 2. 资本账户: S型流入 + 走资 + 报复 -> 外储路径
# ============================================================
def _sigmoid(x, k=1.0, x0=0.0):
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))


def capital_path(appr_rate, p: UnifiedParams, horizon=5,
                 us_tariff_shock=0.0):
    """S型净资本流入(GDP%): 升值预期吸引流入但边际递减;
    走资随管制(1-open)衰减; 报复冲击减流入。"""
    flows = []
    reserves = float(p.reserves_t)
    path = []
    for t in range(1, horizon + 1):
        attract = 0.12 * _sigmoid(appr_rate * 100.0, k=0.9, x0=3.0)   # 期望收益
        flight = 0.35 * appr_rate * (p.openness / 0.5)                  # 高位走资
        net_gdp = (attract - flight) * (1 - us_tariff_shock
                                        * p.us_retaliation_sensitivity)
        net_t = float(net_gdp * p.gdp_usd_t)
        flows.append(net_t)
        reserves += net_t
        path.append(reserves)
    return {"flows_t": [round(x, 3) for x in flows],
            "reserves_path_t": [round(x, 3) for x in path],
            "reserves_end_t": round(reserves, 3),
            "floor_hit": bool(reserves < p.reserves_floor_t)}


# ============================================================
# 3. 双口径去工业化
# ============================================================
def deind_dual(appr_rate, p: UnifiedParams, profit_shock_pct=None):
    """GDP侵蚀口径(V2b)恒内置; 利润口径(V2a)支持注入 repo 引擎实测。"""
    gdp_erode = p.lam_e * appr_rate * 0.28 * 5 * 100.0       # % GDP 5y
    if profit_shock_pct is None:
        profit = gdp_erode * 10.0                              # 近似(仅无引擎时)
        approx = True
    else:
        profit = abs(profit_shock_pct)
        approx = False
    return {"gdp_erode_pt": round(gdp_erode, 1),
            "profit_shock_pct": round(profit, 1),
            "profit_approx": approx}


# ============================================================
# 4. 四政策工具 (V3 移植, 年增量封顶)
# ============================================================
@dataclass
class ImportTools:
    tariff: float = 0.20
    procurement: float = 0.30
    access: float = 0.20
    demand: float = 0.15


def import_policy_delta(tools: ImportTools, p: UnifiedParams) -> dict:
    """年进口增量(T$/yr)与成本。"""
    tariff_pp = tools.tariff * 15.0
    d_tariff = 0.8 * 0.60 * (tariff_pp / 10.0)
    raw_proc = 0.08 * tools.procurement
    d_proc = raw_proc * (1.0 + 0.25 * tools.procurement)
    d_access = 0.6 * 0.45 * tools.access
    d_demand = 2.3 * 0.50 * (0.05 * tools.demand)
    total = d_tariff + d_proc + d_access + d_demand
    fiscal_gdp = (0.30 * d_tariff + 0.10 * d_proc + 0.05 * d_access
                  + 0.60 * d_demand) / p.gdp_usd_t * 100.0
    return {"delta_t": round(total, 3),
            "parts": {"tariff": round(d_tariff, 3),
                      "procurement": round(d_proc, 3),
                      "access": round(d_access, 3),
                      "demand": round(d_demand, 3)},
            "fiscal_gdp_pct": round(fiscal_gdp, 2)}


# ============================================================
# 5. 统一评估
# ============================================================
def evaluate(appr_rate, p: UnifiedParams = None,
             tools: ImportTools = None, profit_shock_pct=None,
             oil_pct=0.30, us_tariff_shock=0.0, horizon=5):
    p = p or UnifiedParams()
    tools = tools or ImportTools()
    inf = inflation_net(appr_rate, p, horizon, oil_pct)
    surp = trade_surplus_t(appr_rate, p, horizon)
    pol = import_policy_delta(tools, p)
    surp_pol = surp - pol["delta_t"] * horizon
    cap = capital_path(appr_rate, p, horizon, us_tariff_shock)
    dd = deind_dual(appr_rate, p, profit_shock_pct)
    flight_gdp = 0.35 * appr_rate * (p.openness / 0.5) * 100.0
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
def balanced_year(appr_rate, p=None, tools=None, target=0.3, max_years=12):
    p = p or UnifiedParams()
    tools = tools or ImportTools()
    pol = import_policy_delta(tools, p)
    for t in range(1, max_years + 1):
        if trade_surplus_t(appr_rate, p, t) - pol["delta_t"] * t <= target:
            return t
    return None


TOOL_SETS = {
    "无政策": ImportTools(0, 0, 0, 0),
    "温和": ImportTools(0.20, 0.30, 0.20, 0.15),
    "积极": ImportTools(0.35, 0.50, 0.30, 0.25),
    "激进": ImportTools(0.60, 0.80, 0.50, 0.40),
}


def optimize_unified(p=None, profit_cb=None, open_set=(0.40, 0.25)):
    """两级扫描: 速度 0-12% x 四工具集 -> 找各开放度下满足全部约束的
    最低速度(卢氏极限思维: 用最低必要升值)与政策集。"""
    p = p or UnifiedParams()
    out = {}
    for op in open_set:
        pp = UnifiedParams(**{**p.__dict__, "openness": op})
        best = None
        for sname, tools in TOOL_SETS.items():
            for r in np.arange(0.0, 0.1201, 0.0025):
                low_profit = profit_cb(float(r)) if profit_cb else None
                ev = evaluate(float(r), pp, tools, low_profit)
                if all(ev["ok"].values()):
                    if best is None or r < best["rate_pct"] / 100.0:
                        best = {"rate_pct": round(r * 100, 2),
                                "tools": sname, "ev": ev}
                    break                       # 该工具集最低可行速度
        out[op] = best
    return out


def sweep_table(p=None, profit_cb=None, tools_name="积极",
                rates=None):
    p = p or UnifiedParams()
    tools = TOOL_SETS[tools_name]
    rows = []
    for r in (rates if rates is not None else np.arange(0.0, 0.1251, 0.0125)):
        low = profit_cb(float(r)) if profit_cb else None
        ev = evaluate(float(r), p, tools, low)
        rows.append(ev)
    return rows


def _engine_profit_cb(n_sim=300, seed=7):
    """repo 引擎利润口径回调(低端制造 5y 冲击)。"""
    from model import MacroParams, ScenarioEngine, load_project_config
    from dataclasses import replace
    mp, cc = load_project_config()

    def cb(rate):
        p = replace(mp, cny_annual_apprec=float(rate),
                    n_simulations=n_sim, seed=seed)
        r = ScenarioEngine(p, capital_cfg=cc).run()
        return float(r["industry_profit"]["export_lowend"].iloc[-1]) * 100
    return cb


def policy_needed_at(speed, p=None, profit_cb=None, target=0.3,
                 openness=0.40, full=ImportTools(0.60, 0.80, 0.50, 0.40)):
    """固定升值速度 -> 求满足顺差目标的最小政策力度 k (0-1 缩放 full 工具)。
    分工 = 速度承担一部分 + 政策补足其余; 返回 k 与贡献拆分。"""
    p = p or UnifiedParams()
    pp = UnifiedParams(**{**p.__dict__, "openness": openness})
    sur_no_pol = trade_surplus_t(speed, pp, 5)
    pol_full = import_policy_delta(full, pp)["delta_t"]
    need = max(0.0, sur_no_pol - target)
    k = min(1.0, math.ceil(need / (pol_full * 5.0) * 100) / 100.0) if pol_full > 0 else 0.0
    base_no = trade_surplus_t(0.0, pp, 5)                  # 不升值基准
    tools = ImportTools(*(x * k for x in (full.tariff, full.procurement,
                                          full.access, full.demand)))
    low = profit_cb(speed) if profit_cb else None
    ev = evaluate(speed, pp, tools, low)
    pol_cut = pol_full * 5.0 * k
    appr_cut = sur_no_pol - ev["surplus_t"] - pol_cut
    return {"speed": round(speed * 100, 2), "k": round(k, 2),
            "tools": tools, "surplus_t": ev["surplus_t"],
            "sur_no_pol": round(sur_no_pol, 3),
            "deind": ev["deind"], "flight_gdp_pct": ev["flight_gdp_pct"],
            "reserves_end": ev["capital"]["reserves_end_t"],
            "fiscal_gdp_pct": ev["policy"]["fiscal_gdp_pct"],
            "base_no": round(base_no, 3),
            "share_speed_pct": round(max(0.0, (base_no - sur_no_pol)
                                         / max(1e-9, base_no - target) * 100), 1),
            "share_policy_pct": round(max(0.0, (sur_no_pol - target)
                                          / max(1e-9, base_no - target) * 100), 1),
            "ok": ev["ok"], "verdict": ev["verdict"]}


def main():
    cb = None
    try:
        cb = _engine_profit_cb()
    except Exception as e:
        print("  [note] repo engine cb unavailable:", type(e).__name__)
    print("=" * 102)
    print("  policy_engine - 统一系统 (V2a 利润 x V2b GDP x V3 工具 x V4 外储/报复)")
    print("  原则: 以升值为主动力, 进口政策只补足差额 (非替代升值)")
    print("=" * 102)
    print()
    print("[1] 固定速度带求最小政策度 (开放度 0.40 / 0.25):")
    print("  %-5s %-6s %-9s %-10s %-10s %-8s %-9s %-6s" %
          ("速%", "政策k", "顺差T", "政策承担%", "速度承担%", "利润%", "外储T", "判定"))
    res = {}
    for op in (0.40, 0.25):
        for sp in (0.05, 0.06, 0.07, 0.08):
            r = policy_needed_at(sp, profit_cb=cb, openness=op)
            res[(op, round(sp * 100))] = r
            print("  %-5.0f %-6.2f %-9.2f %-10.0f %-10.0f %-8.1f %-9.2f %-6s"
                  % (r["speed"], r["k"], r["surplus_t"],
                     r["share_policy_pct"], r["share_speed_pct"],
                     r["deind"]["profit_shock_pct"], r["reserves_end"],
                     r["verdict"][:5]))
        print("  " + "-" * 96)
    rec = res[(0.40, 6)]
    print()
    print("[2] 推荐读数 @ 6%%/年 (open 0.40): 政策力度 k=%.2f -> 政策承担 %.0f%%, "
          "速度承担 %.0f%% | 顺差 %.2fT | 去工业 GDP侵蚀 %.1f%% / 利润 %.1f%% | "
          "财政 %.2f%%GDP" % (rec["k"], rec["share_policy_pct"],
                              rec["share_speed_pct"], rec["surplus_t"],
                              rec["deind"]["gdp_erode_pt"],
                              rec["deind"]["profit_shock_pct"],
                              rec["fiscal_gdp_pct"]))
    print()
    print("[3] 口径对照(6%%/年): 利润口径(引擎) %.1f%% vs GDP口径(解析) %.1f%%; "
          "红线均为 35" % (rec["deind"]["profit_shock_pct"],
                            rec["deind"]["gdp_erode_pt"]))
    print()
    print("  注: 不设速度偏好时联合优化会滑向 ~0.75%/年(政策替代升值) -")
    print("      违背以升值为主动力的原则, 已弃用自由解; 固定速度带求解为规范用法。")




if __name__ == "__main__":
    main()
