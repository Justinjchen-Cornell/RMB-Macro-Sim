"""modules/trade - 货物+服务顺差路径与进口政策工具。"""
from .core import UnifiedParams, ImportTools

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
