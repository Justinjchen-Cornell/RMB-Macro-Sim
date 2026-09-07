"""modules/industry - 去工业化双口径。"""
from .core import UnifiedParams

def deind_dual(appr_rate, p: UnifiedParams, profit_shock_pct=None):
    """桥注: 利润冲击%约等于GDP侵蚀%x10(低端制造利润占增加值约8-12%,
    传导近线性); 两口径各对各自35红线, 勿跨比。"""
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
