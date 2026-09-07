"""modules/optimizer - 平衡年/最小政策度/扫描。"""
import math
import numpy as np
from .core import UnifiedParams, ImportTools
from .trade import trade_surplus_t, import_policy_delta
from .evaluate import evaluate

TOOL_SETS = {
    "无政策": ImportTools(0, 0, 0, 0),
    "温和": ImportTools(0.20, 0.30, 0.20, 0.15),
    "积极": ImportTools(0.35, 0.50, 0.30, 0.25),
    "激进": ImportTools(0.60, 0.80, 0.50, 0.40),
}

def balanced_year(appr_rate, p=None, tools=None, target=0.3, max_years=12):
    p = p or UnifiedParams()
    tools = tools or ImportTools()
    pol = import_policy_delta(tools, p)
    for t in range(1, max_years + 1):
        if trade_surplus_t(appr_rate, p, t) - pol["delta_t"] * t <= target:
            return t
    return None





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




