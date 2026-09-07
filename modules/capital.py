"""modules/capital - 资本账户: S型流入/走资/外储/报复/管制冲突。"""
import numpy as np
from .core import UnifiedParams

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
        flight_share = flight_pct_gdp(appr_rate, p) / 100.0
        net_gdp = (attract - flight_share) * (1 - us_tariff_shock
                                        * p.us_retaliation_sensitivity)
        net_t = float(net_gdp * p.gdp_usd_t)
        flows.append(net_t)
        reserves += net_t
        path.append(reserves)
    return {"flows_t": [round(x, 3) for x in flows],
            "reserves_path_t": [round(x, 3) for x in path],
            "reserves_end_t": round(reserves, 3),
            "floor_hit": bool(reserves < p.reserves_floor_t)}




def flight_pct_gdp(s, p: UnifiedParams):
    """走资占 GDP% (v2 归一化标定): open=.40 -> 6%=9.6%, 10%=33%; 红线 35。"""
    raw = 0.30 * s + 4.0 * max(0.0, s - 0.06) ** 1.5
    return p.openness * 13.3 * raw * 100.0




def capital_components(appr_rate, p: UnifiedParams, us_tariff_shock=0.0):
    """资本账户分项(T$/yr, v2 语义): FDI/Portfolio/NEE/Hot(走资)。"""
    gdp = p.gdp_usd_t
    fdi = 0.05 * (1 + 0.3 * appr_rate - 0.2 * us_tariff_shock)
    port = 0.04 * appr_rate * (p.openness / 0.40) - 0.02 * us_tariff_shock
    nee = 0.015 * appr_rate * p.openness
    hot = -flight_pct_gdp(appr_rate, p) / 100.0 * gdp
    return {"fdi": round(fdi, 3), "portfolio": round(port, 3),
            "nee": round(nee, 3), "hot": round(hot, 3),
            "net_t": round(fdi + port + nee + hot, 3)}




def us_retaliation(appr_rate, p: UnifiedParams, rmb_intl_level=None):
    """美国报复(博弈): 速度>7% 或国际化加深 -> tariff 冲击 + 制裁概率。"""
    level = p.rmb_intl if rmb_intl_level is None else rmb_intl_level
    speed_pressure = max(0.0, appr_rate - 0.07)
    tariff_shock = p.us_retaliation_sensitivity * (
        speed_pressure + 0.3 * level)
    sanction_prob = min(1.0, 0.3 * speed_pressure + 0.4 * level)
    return {"tariff_shock": round(tariff_shock, 3),
            "sanction_prob": round(sanction_prob, 3)}




def intl_control_conflict(p: UnifiedParams):
    """管制(1-open)与国际化(rmb_intl)的目标冲突指数 [0,1]。"""
    return round(min(1.0, p.rmb_intl * (1.0 - p.openness) * 2.0), 2)


# ============================================================
# 3. 双口径去工业化
# ============================================================
